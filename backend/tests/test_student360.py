# Tests for Student 360 business rules (requirements sections 8 & 9).
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./test_student360.db"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
import app.models  # noqa: F401
import app.models.student360  # noqa: F401
from app.data.seed_student360 import seed_student360
from app.main import app


@pytest.fixture(scope="module")
def client():
    engine = create_engine(
        "sqlite:///./test_student360.db",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db = TestingSession()
    seed_student360(db)

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    db.close()
    app.dependency_overrides.clear()
    try:
        os.remove("./test_student360.db")
    except OSError:
        pass


STUDENT = {"X-Student-Number": "402101001"}


# =====================================================================
# STU-AUTH
# =====================================================================

class TestAuth:
    def test_otp_flow(self, client):
        # STU-AUTH-02: ورود با شناسه دانشجویی و رمز یک‌بارمصرف
        req = client.post("/api/student360/auth/otp/request",
                          json={"student_number": "402101001"})
        assert req.status_code == 200
        code = req.json()["dev_code"]
        verify = client.post("/api/student360/auth/otp/verify",
                             json={"student_number": "402101001", "code": code})
        assert verify.status_code == 200
        assert verify.json()["role"] == "student"

    def test_otp_wrong_code(self, client):
        client.post("/api/student360/auth/otp/request",
                    json={"student_number": "402101001"})
        bad = client.post("/api/student360/auth/otp/verify",
                          json={"student_number": "402101001", "code": "000000"})
        assert bad.status_code == 401

    def test_sso_login(self, client):
        # STU-AUTH-01
        res = client.post("/api/student360/auth/sso",
                          json={"sso_token": "a.mohammadi"})
        assert res.status_code == 200
        assert res.json()["ok"] is True

    def test_audit_log_records_login(self, client):
        # STU-AUTH-04
        logs = client.get("/api/student360/audit-logs").json()
        actions = {l["action"] for l in logs}
        assert "otp-request" in actions or "login" in actions

    def test_unauthorized_profile(self, client):
        res = client.get("/api/student360/profile")
        assert res.status_code == 401


# =====================================================================
# STU-PRO
# =====================================================================

class TestProfile:
    def test_profile_complete(self, client):
        # STU-PRO-01..07
        res = client.get("/api/student360/profile", headers=STUDENT)
        assert res.status_code == 200
        p = res.json()
        assert p["identity"]["student_number"] == "402101001"
        assert p["academic"]["program"] == "مهندسی کامپیوتر"
        assert "overall" in p["gpa"] and p["gpa"]["overall"] > 0
        assert p["units"]["passed"] > 0
        assert len(p["current_courses"]) == 3
        assert p["last_data_update"] is not None
        # قاعده: پروفایل جایگزین سامانه رسمی نیست
        assert "جایگزین سامانه رسمی آموزش نیست" in p["disclaimer"]

    def test_student_isolation(self, client):
        # STU-AUTH-03: دانشجو فقط به اطلاعات خودش دسترسی دارد
        res = client.get("/api/student360/profile",
                         headers={"X-Student-Number": "402101002"})
        assert res.status_code == 200
        assert res.json()["identity"]["student_number"] == "402101002"

    def test_discrepancy_flow(self, client):
        # STU-PRO-08/09: اعلام مغایرت بدون تغییر داده رسمی
        res = client.post("/api/student360/profile/discrepancy",
                          headers=STUDENT,
                          json={"field": "national_id", "current_value": "0012",
                                "claimed_value": "9999",
                                "description": "کد ملی نادرست است"})
        assert res.status_code == 200
        rows = client.get("/api/student360/profile/discrepancies",
                          headers=STUDENT).json()
        assert any(r["status"] == "pending" for r in rows)


# =====================================================================
# STU-REG
# =====================================================================

class TestRegulations:
    def test_answer_with_source(self, client):
        # STU-REG-02/03: پاسخ فقط بر اساس منابع، با استناد کامل
        res = client.post("/api/student360/regulations/ask", headers=STUDENT,
                          json={"question": "حداکثر واحد مجاز انتخاب واحد چند است؟"})
        assert res.status_code == 200
        body = res.json()
        assert body["sources"], "پاسخ باید منبع داشته باشد"
        src = body["sources"][0]
        assert src["source_name"] and src["article"]
        assert src["valid_from"]

    def test_low_confidence_flagged(self, client):
        # STU-REG-04
        res = client.post("/api/student360/regulations/ask", headers=STUDENT,
                          json={"question": "قانون جابجایی خوابگاه چیست؟"})
        body = res.json()
        assert body["is_low_confidence"] is True
        assert body["requires_expert_referral"] is True  # STU-REG-05

    def test_feedback(self, client):
        # STU-REG-06
        ask = client.post("/api/student360/regulations/ask", headers=STUDENT,
                          json={"question": "مقررات مرخصی تحصیلی چیست؟"})
        conv_id = ask.json()["conversation_id"]
        fb = client.post(f"/api/student360/regulations/{conv_id}/feedback",
                         headers=STUDENT, json={"feedback": "helpful"})
        assert fb.status_code == 200
        history = client.get("/api/student360/regulations/history",
                             headers=STUDENT).json()
        assert any(h["id"] == conv_id and h["feedback"] == "helpful"
                   for h in history)  # STU-REG-07

    def test_expired_regulation_excluded(self, client, db_session=None):
        # قاعده ۹-۶: آیین‌نامه منقضی نباید استفاده شود
        from app.core.database import get_db
        db = next(app.dependency_overrides[get_db]())
        from app.models.student360 import Regulation
        import datetime
        db.add(Regulation(
            doc_type="circular", title="بخشنامه قدیمی آزمون", article="ماده ۹",
            content="قاعده منقضی درباره ورود به آزمون با کارت دانجوشی.",
            keywords="آزمون، ورود، کارت", source_name="بخشنامه منقضی",
            valid_from=datetime.date(2015, 1, 1),
            valid_to=datetime.date(2018, 1, 1), is_active=True))
        db.commit()
        res = client.post("/api/student360/regulations/ask", headers=STUDENT,
                          json={"question": "ورود به جلسه آزمون با کارت دانجوشی چگونه است؟"})
        body = res.json()
        for src in body.get("sources", []):
            assert src["source_name"] != "بخشنامه منقضی"

    def test_no_decision_disclaimer(self, client):
        # STU-REG-08
        res = client.post("/api/student360/regulations/ask", headers=STUDENT,
                          json={"question": "مقررات مشروطی چیست؟"}).json()
        assert "تصمیم قطعی" in res["disclaimer"]


# =====================================================================
# بند ۸-۴ Process guides
# =====================================================================

class TestGuides:
    def test_all_required_guides(self, client):
        res = client.get("/api/student360/guides").json()
        slugs = {g["slug"] for g in res}
        for needed in ("leave-of-absence", "emergency-drop", "add-drop",
                       "grade-appeal", "professor-intro", "guest-request",
                       "transfer-request", "unit-matching",
                       "study-certificate", "graduation-settlement"):
            assert needed in slugs

    def test_guide_structure(self, client):
        g = client.get("/api/student360/guides/leave-of-absence").json()
        assert g["conditions"] and g["required_documents"] and g["steps"]
        assert g["responsible_unit"] and g["deadline"]
        assert g["system_url"] and g["processing_time"] and g["related_rules"]


# =====================================================================
# STU-CRS
# =====================================================================

class TestSelectionAssistant:
    def test_assistant_output_statuses(self, client):
        res = client.get("/api/student360/selection/assistant?term=1404-2",
                         headers=STUDENT).json()
        valid_statuses = {"قابل اخذ", "قابل اخذ با اخطار", "نیازمند تأیید آموزش",
                          "غیرقابل اخذ", "پیشنهادشده",
                          "ضروری برای جلوگیری از تأخیر تحصیلی"}
        assert res["courses"]
        for c in res["courses"]:
            assert c["status"] in valid_statuses
            assert c["reasons"] is not None  # STU-CRS-09

    def test_passed_course_not_takable(self, client):
        # STU-CRS-05
        res = client.get("/api/student360/selection/assistant?term=1404-2",
                         headers=STUDENT).json()
        cs101 = next(c for c in res["courses"] if c["course_code"] == "CS101")
        assert cs101["status"] == "غیرقابل اخذ"

    def test_prerequisite_control(self, client):
        # STU-CRS-02: CS499 پیش‌نیاز CS401 دارد که گذرانده نشده
        res = client.get("/api/student360/selection/assistant?term=1404-2",
                         headers=STUDENT).json()
        cs499 = next(c for c in res["courses"] if c["course_code"] == "CS499")
        assert cs499["status"] == "غیرقابل اخذ"
        assert any("پیش‌نیاز" in r for r in cs499["reasons"])

    def test_scenario_validation(self, client):
        # STU-CRS-10: سناریو با پیش‌نیاز نقض‌شده باید خطا بگیرد
        res = client.post("/api/student360/selection/scenarios", headers=STUDENT,
                          json={"term": "1404-2", "name": "تست ۱",
                                "course_codes": ["CS499", "CS401"]})
        assert res.status_code == 200
        v = res.json()["validation"]
        assert v["valid"] is False
        assert any("پیش‌نیاز" in e for e in v["errors"])

    def test_scenario_units_cap(self, client):
        # STU-CRS-03
        many = ["CS101", "MATH101", "PHYS101", "CS102", "MATH102",
                "CS201", "CS202", "CS301"]
        res = client.post("/api/student360/selection/scenarios", headers=STUDENT,
                          json={"term": "1404-2", "name": "سنگین",
                                "course_codes": many}).json()
        errs = res["validation"]["errors"]
        assert any("سقف" in e for e in errs)

    def test_scenario_list(self, client):
        rows = client.get("/api/student360/selection/scenarios",
                          headers=STUDENT).json()
        assert len(rows) >= 2
        # STU-CRS-11: هیچ سناریویی به‌صورت رسمی تأیید نشده
        assert all(s["confirmed_officially"] is False for s in rows)

    def test_prerequisite_analysis_detail(self, client):
        # بند ۸-۶: وضعیت هر پیش‌نیاز، نمره و دلیل
        res = client.get("/api/student360/selection/courses/CS303/analysis",
                         headers=STUDENT).json()
        assert res["course_code"] == "CS303"
        assert res["prerequisites"], "CS303 پیش‌نیاز CS201 دارد"
        pre = res["prerequisites"][0]
        assert pre["course_code"] == "CS201"
        assert pre["status"] == "passed"
        assert pre["grade"] == 11.0
        assert res["allowed"] is True
        assert res["reasons"] == []


# =====================================================================
# STU-GRD
# =====================================================================

class TestGraduation:
    def test_graduation_report(self, client):
        res = client.get("/api/student360/graduation/check", headers=STUDENT).json()
        # STU-GRD-08
        assert "غیرقطعی" in res["warning"]
        assert res["result"] in {
            "واجد شرایط اولیه فارغ‌التحصیلی", "دارای کسری واحد",
            "دارای درس الزامی باقی‌مانده", "دارای مغایرت در سرفصل یا تطبیق",
            "نیازمند بررسی کارشناسی"}
        assert res["remaining_obligatory"]  # دانشجوی پایلوت هنوز درس دارد
        assert res["total_passed_units"] < res["total_required_units"]
        assert res["expert_referral"] is True  # STU-GRD-09


# =====================================================================
# بند ۸-۸ Calendar
# =====================================================================

class TestCalendar:
    def test_calendar_events(self, client):
        rows = client.get("/api/student360/calendar").json()
        types = {r["event_type"] for r in rows}
        for needed in ("course-selection-start", "add-drop", "exams",
                       "tuition-payment", "grade-appeal",
                       "supervisor-selection", "thesis-defense"):
            assert needed in types

    def test_channels_update(self, client):
        res = client.put("/api/student360/notifications/channels", headers=STUDENT,
                         json={"sms": False, "mobile_push": True})
        assert res.status_code == 200
        body = res.json()
        assert body["sms"] is False and body["mobile_push"] is True
        assert body["in_app"] is True  # بدون تغییر


# =====================================================================
# بند ۸-۹ Alerts
# =====================================================================

class TestAlerts:
    def test_alerts_have_reason_action_severity(self, client):
        rows = client.get("/api/student360/alerts", headers=STUDENT).json()
        assert rows, "دانشجوی پایلوت باید حداقل یک هشدار داشته باشد"
        for a in rows:
            assert a["reason"] and a["severity"] and a["recommended_action"]
            assert "تنبیهی خودکار" in a["note"]

    def test_counseling_request(self, client):
        rows = client.get("/api/student360/alerts", headers=STUDENT).json()
        res = client.post("/api/student360/alerts/counseling", headers=STUDENT,
                          json={"alert_id": rows[0]["id"], "message": "مشاوره می‌خواهم"})
        assert res.status_code == 200
        rows2 = client.get("/api/student360/alerts", headers=STUDENT).json()
        target = next(a for a in rows2 if a["id"] == rows[0]["id"])
        assert target["status"] == "counseling-requested"


# =====================================================================
# بند ۸-۱۰ Quiz
# =====================================================================

class TestQuiz:
    def test_generate_only_enabled_courses(self, client):
        ok = client.post("/api/student360/quiz/generate", headers=STUDENT,
                         json={"course_code": "CS201", "count": 2})
        assert ok.status_code == 200
        bad = client.post("/api/student360/quiz/generate", headers=STUDENT,
                          json={"course_code": "CS401"})
        assert bad.status_code == 400  # خارج از دروس منتخب فاز اول

    def test_submit_and_weak_topics(self, client):
        gen = client.post("/api/student360/quiz/generate", headers=STUDENT,
                          json={"course_code": "CS301", "count": 2}).json()
        answers = {str(q["id"]): "نادرست عمدی" for q in gen["questions"]}
        sub = client.post(f"/api/student360/quiz/{gen['quiz_id']}/submit",
                          headers=STUDENT, json={"answers": answers}).json()
        assert sub["score"] == 0
        assert sub["weak_topics"], "نقاط ضعف باید شناسایی شود"
        assert sub["study_recommendations"]
        assert all("explanation" in r for r in sub["results"])

    def test_history(self, client):
        # یک آزمون کامل دیگر ثبت کن، سپس سابقه را بررسی کن
        gen = client.post("/api/student360/quiz/generate", headers=STUDENT,
                          json={"course_code": "CS101", "count": 1}).json()
        client.post(f"/api/student360/quiz/{gen['quiz_id']}/submit",
                    headers=STUDENT, json={"answers": {}})
        rows = client.get("/api/student360/quiz/history", headers=STUDENT).json()
        assert len(rows) >= 2


# =====================================================================
# بند ۸-۱۱ Smart professor
# =====================================================================

class TestSmartProfessor:
    def test_answer_with_source(self, client):
        res = client.post("/api/student360/professor/ask", headers=STUDENT,
                          json={"course_code": "CS201",
                                "question": "درخت جست‌وجوی دودویی چیست؟"}).json()
        assert res["ok"] is True
        assert res["sources"], "پاسخ باید منبع داشته باشد"
        assert res["confidence"] > 0.5

    def test_disabled_course(self, client):
        res = client.post("/api/student360/professor/ask", headers=STUDENT,
                          json={"course_code": "CS401", "question": "تست؟"})
        assert res.status_code == 400

    def test_no_confidential_exam_leak(self, client):
        # سؤال درباره امتحان محرمانه نباید پاسخ قطعی بدهد
        res = client.post("/api/student360/professor/ask", headers=STUDENT,
                          json={"course_code": "CS201",
                                "question": "سؤالات امتحان پایان‌ترم چیست؟"}).json()
        assert res["is_low_confidence"] is True

    def test_exercise_design(self, client):
        res = client.post("/api/student360/professor/exercise", headers=STUDENT,
                          json={"course_code": "CS201", "topic": "پشته"}).json()
        assert res["ok"] is True
        assert len(res["exercise"]) == 3
        assert res["source_ref"]
