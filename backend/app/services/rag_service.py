# app/services/rag_service.py
# Lightweight RAG core (Retrieval + sources) over regulation/guide/content tables.
# Schema-agnostic: reads any String/Text column, so it survives model changes.
# Uses sklearn TF-IDF (works well for Persian without extra deps).
from __future__ import annotations

from threading import RLock

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy.orm import Session

from app.models.student360 import (
    CourseRule,
    Curriculum,
    LearningContent,
    ProcessGuide,
    Regulation,
)

_LOCK = RLock()
_INDEX = {"docs": [], "matrix": None, "vectorizer": None}

_TITLE_CANDIDATES = ("title", "name", "question", "topic", "slug", "article_no", "code", "course_code")
_TEXT_EXCLUDE = ("password", "token", "hash", "otp")


def _row_doc(model, row):
    title = None
    parts = []
    for col in model.__table__.columns:
        lname = col.name.lower()
        if any(x in lname for x in _TEXT_EXCLUDE):
            continue
        val = getattr(row, col.name, None)
        if val is None:
            continue
        sval = str(val).strip()
        if not sval or sval.lower() in ("none", "null"):
            continue
        if lname in _TITLE_CANDIDATES and title is None:
            title = sval
        if isinstance(val, str) and len(sval) >= 8:
            parts.append(sval)
    return title, "\n".join(parts)


def rebuild_index(db: Session):
    docs = []
    sources = [
        (Regulation, "regulation"),
        (ProcessGuide, "guide"),
        (LearningContent, "content"),
        (CourseRule, "course_rule"),
        (Curriculum, "curriculum"),
    ]
    for model, kind in sources:
        try:
            rows = db.query(model).all()
        except Exception:
            continue
        for row in rows:
            title, text = _row_doc(model, row)
            if not text or len(text) < 15:
                continue
            rid = getattr(row, "id", "?")
            docs.append({
                "kind": kind,
                "model": model.__name__,
                "row_id": rid,
                "title": title or f"{kind} #{rid}",
                "text": text,
            })
    with _LOCK:
        if docs:
            vec = TfidfVectorizer(analyzer="word", ngram_range=(1, 2), min_df=1)
            mat = vec.fit_transform([d["text"] for d in docs])
            _INDEX.update(docs=docs, matrix=mat, vectorizer=vec)
        else:
            _INDEX.update(docs=[], matrix=None, vectorizer=None)
    by_kind = {}
    for d in docs:
        by_kind[d["kind"]] = by_kind.get(d["kind"], 0) + 1
    return {"documents": len(docs), "by_kind": by_kind}


def ensure_index(db: Session):
    with _LOCK:
        if _INDEX["matrix"] is None:
            return rebuild_index(db)
    return {"documents": len(_INDEX["docs"])}


def retrieve(db: Session, query: str, k: int = 4):
    ensure_index(db)
    with _LOCK:
        docs, mat, vec = _INDEX["docs"], _INDEX["matrix"], _INDEX["vectorizer"]
        if not docs or vec is None or not (query or "").strip():
            return []
        q = vec.transform([query])
        scores = cosine_similarity(q, mat)[0]
        order = scores.argsort()[::-1][: max(1, min(int(k), 10))]
        out = []
        for i in order:
            if scores[i] <= 0.01:
                continue
            d = dict(docs[i])
            d["score"] = round(float(scores[i]), 4)
            d["snippet"] = d["text"][:400]
            out.append(d)
        return out
