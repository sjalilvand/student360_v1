import sys
sys.stdout.reconfigure(encoding="utf-8")
import app.main  # noqa
from app.core.database import SessionLocal
from app.services import risk_ml_service as rm

db = SessionLocal()
try:
    r = rm.train(db, min_students=2)
    print("retrain:", r)
finally:
    db.close()
