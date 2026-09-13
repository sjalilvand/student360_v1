import sys, traceback
sys.stdout.reconfigure(encoding="utf-8")

print("[1] patch marker in student360_profile.py:", end=" ")
_p = r"app\services\student360_profile.py"
src = open(_p, encoding="utf-8").read()
print("YES (v_student_gpa found)" if "v_student_gpa" in src else "NO - PATCH MISSING!")

print("[2] importing app.main (server import order)...")
try:
    import app.main  # noqa - replicates uvicorn import order, avoids circular trap
    print("[2] OK")
except Exception:
    traceback.print_exc(); sys.exit(1)

from sqlalchemy import text
from app.core.database import SessionLocal
from app.models.student360 import Student
from app.services.student360_profile import get_profile

db = SessionLocal()
try:
    views = [r[0] for r in db.execute(text("SELECT name FROM sqlite_master WHERE type='view'"))]
    print("[3] views in DB:", views)
    row = db.execute(text("SELECT weighted_gpa, total_credits FROM v_student_gpa WHERE student_number='402101001'")).mappings().first()
    print("[4] raw view row:", dict(row) if row else None)
    s = db.query(Student).filter(Student.student_number == "402101001").first()
    p = get_profile(db, s)
    print("[5] gpa keys from service:", list(p["gpa"].keys()))
    print("[6] gpa.mart value:", p["gpa"].get("mart"))
except Exception:
    traceback.print_exc()
finally:
    db.close()

from app.utils.jalali import jalali_to_gregorian, gregorian_to_jalali
g = jalali_to_gregorian(1405, 6, 20)
print("[7] jalali round-trip: 1405/06/20 ->", g, "-> back:", gregorian_to_jalali(*g))
