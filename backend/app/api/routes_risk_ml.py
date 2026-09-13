# app/api/routes_risk_ml.py
from typing import Optional

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services import risk_ml_service as rm

router = APIRouter()


@router.post("/api/risk-ml/train")
def risk_ml_train(db: Session = Depends(get_db)):
    return rm.train(db)


@router.get("/api/risk-ml/predict")
def risk_ml_predict(x_student_number: Optional[str] = Header(default=None),
                    db: Session = Depends(get_db)):
    if not x_student_number:
        return {"error": "missing X-Student-Number"}
    return rm.predict(db, x_student_number)


@router.get("/api/risk-ml/status")
def risk_ml_status():
    return {"model_exists": rm.model_exists()}
