# app/services/risk_ml_service.py
# ML risk scorer (Phase 2/3): RandomForest distilled from the rule-based model.
# Same pattern as demand_service: train -> joblib -> predict. Graceful fallback
# to the rule-based scorer when the model is not trained.
from __future__ import annotations

import os
from pathlib import Path

import joblib
import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services import behavioral_service as bs
from app.services import risk_service as rs

MODEL_DIR = Path(__file__).resolve().parents[1] / "ml_models"
MODEL_PATH = MODEL_DIR / "risk_rf.joblib"
FEATURES = ("gpa", "trend_drop", "failed_credits", "probation", "engagement", "term_idx")


def _features_for(db: Session, sn: str) -> dict | None:
    st = rs.compute_risk(db, sn)  # gives gpa etc. (marts-independent now)
    gpa = st.get("gpa")
    tg = db.execute(text(
        "SELECT g.term, ROUND(SUM(g.grade * g.credits) * 1.0 / NULLIF(SUM(g.credits), 0), 2) AS tg "
        "FROM stu_grades g JOIN stu_students s2 ON s2.id = g.student_id "
        "WHERE s2.student_number = :sn AND g.grade IS NOT NULL "
        "GROUP BY g.term ORDER BY g.term"), {"sn": str(sn)}).all()
    term_gpas = [(t, float(x)) for t, x in tg if x is not None]
    drop = 0.0
    if len(term_gpas) >= 2:
        drop = max(0.0, term_gpas[-2][1] - term_gpas[-1][1])
    failed = int(st.get("failed_credits") or 0)
    prob = int(st.get("probation_count") or 0)
    eng = int(bs.engagement_index(db, sn, days=30).get("score", 0))
    return {
        "gpa": float(gpa) if gpa is not None else 12.0,  # neutral default
        "trend_drop": round(drop, 2),
        "failed_credits": failed,
        "probation": prob,
        "engagement": eng,
        "term_idx": len(term_gpas),
        "_rule_level": st.get("risk_level"),
        "_rule_score": st.get("risk_score"),
        "_reasons": st.get("reasons"),
        "_actions": st.get("suggested_actions"),
    }


def _vec(f: dict) -> list:
    return [f[k] for k in FEATURES]


def model_exists() -> bool:
    return MODEL_PATH.exists()


def train(db: Session, min_students: int = 3) -> dict:
    from sklearn.ensemble import RandomForestClassifier
    students = db.execute(text("SELECT student_number FROM stu_students")).all()
    X, y, used = [], [], []
    for (sn,) in students:
        try:
            f = _features_for(db, str(sn))
        except Exception:
            continue
        X.append(_vec(f))
        # label: distilled from rule model (>=35 => at-risk)
        y.append(1 if (f["_rule_score"] or 0) >= 35 else 0)
        used.append(str(sn))
    if len(used) < min_students:
        return {"ok": False, "reason": f"not enough students ({len(used)} < {min_students})",
                "students": used}
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    clf = RandomForestClassifier(n_estimators=120, max_depth=6, random_state=42)
    clf.fit(np.array(X), np.array(y))
    joblib.dump({"model": clf, "features": FEATURES}, MODEL_PATH)
    acc = round(clf.score(np.array(X), np.array(y)), 3)  # train-acc (pilot only!)
    return {"ok": True, "students": len(used), "train_accuracy": acc,
            "note": "pilot: labels distilled from rules; replace with real outcomes later"}


def predict(db: Session, sn: str) -> dict:
    """ML-scored risk; falls back to rule-based when model absent."""
    f = _features_for(db, sn)
    base = {
        "student_number": str(sn),
        "gpa": f["gpa"], "trend_drop": f["trend_drop"],
        "failed_credits": f["failed_credits"], "probation": f["probation"],
        "engagement": f["engagement"],
        "reasons": f["_reasons"], "suggested_actions": f["_actions"],
        "disclaimer": ("⚠️ پیش‌بینی اولیه و غیرقطعی است؛ مبنای هیچ تصمیم تنبیهی "
                       "خودکار نیست."),
    }
    if not model_exists():
        base.update({"engine": "rules", "risk_score": f["_rule_score"],
                     "risk_level": f["_rule_level"]})
        return base
    blob = joblib.load(MODEL_PATH)
    clf = blob["model"]
    X = np.array([_vec(f)])
    proba = clf.predict_proba(X)[0]
    p_risk = float(proba[list(clf.classes_).index(1)] if 1 in clf.classes_ else 0.0)
    score = round(p_risk * 100)
    level = "بالا" if score >= 60 else ("متوسط" if score >= 35 else "پایین")
    rule_score = f["_rule_score"] or 0
    blend = round(0.6 * score + 0.4 * rule_score)  # ensemble with rules
    blend_level = "بالا" if blend >= 60 else ("متوسط" if blend >= 35 else "پایین")
    base.update({"engine": "ml+rules", "ml_prob": round(p_risk, 3),
                 "ml_score": score, "risk_score": blend, "risk_level": blend_level})
    return base
