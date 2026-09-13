# Student 360 — REST API (auth, profile, regulations, guides, selection,
# prerequisites, graduation, calendar, alerts, quiz, smart professor).
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.student360 import Student, UnifiedUser
from app.services import (
    student360_auth as auth_svc,
    student360_profile as profile_svc,
    student360_regulations as reg_svc,
    student360_academic as acad_svc,
    student360_calendar_alerts as cal_svc,
    student360_quiz_professor as qp_svc,
)

router = APIRouter(prefix="/api/student360", tags=["Student360"])


# =====================================================================
# Helpers — نشست پایلوت: هدر X-Student-Number (در استقرار: JWT)
# =====================================================================

def _get_client_ip(request: Request) -> str:
    return request.client.host if request.client else None


def get_current_student(request: Request, db: Session = Depends(get_db)) -> Student:
    student_number = request.headers.get("X-Student-Number")
    if not student_number:
        raise HTTPException(status_code=401, detail="ورود انجام نشده است.")
    student = db.query(Student).filter(
        Student.student_number == student_number).first()
    if not student:
        raise HTTPException(status_code=401, detail="دانشجو یافت نشد.")
    return student


def get_current_user(request: Request, db: Session = Depends(get_db)) -> UnifiedUser:
    """کاربر فعلی (دانشجو یا کارمند) — STU-AUTH-03/05."""
    username = request.headers.get("X-User")
    if not username:
        raise HTTPException(status_code=401, detail="ورود انجام نشده است.")
    user = auth_svc.get_unified_user(db, username)
    if not user:
        raise HTTPException(status_code=401, detail="کاربر یافت نشد.")
    return user


# =====================================================================
# Auth
# =====================================================================

class SSORequest(BaseModel):
    sso_token: str


class OTPRequestModel(BaseModel):
    student_number: str


class OTPVerifyModel(BaseModel):
    student_number: str
    code: str


class PasswordLoginModel(BaseModel):
    username: str
    password: str


@router.post("/auth/sso")
def auth_sso(body: SSORequest, request: Request, db: Session = Depends(get_db)):
    result = auth_svc.sso_login(db, body.sso_token)
    if not result["ok"]:
        raise HTTPException(status_code=401, detail=result["reason"])
    user = result["user"]
    auth_svc.write_audit_log(db, student_number=user.username, action="login",
                             role=user.role, detail="ورود با SSO",
                             ip_address=_get_client_ip(request))
    token = auth_svc.issue_session_token(user.username)
    return {"ok": True, "token": token, "role": user.role,
            "display_name": user.display_name, "username": user.username}


@router.post("/auth/otp/request")
def auth_otp_request(body: OTPRequestModel, db: Session = Depends(get_db)):
    result = auth_svc.otp_request(db, body.student_number)
    if not result["ok"]:
        raise HTTPException(status_code=404, detail=result["reason"])
    return result  # dev_code فقط در پایلوت


@router.post("/auth/otp/verify")
def auth_otp_verify(body: OTPVerifyModel, request: Request, db: Session = Depends(get_db)):
    result = auth_svc.otp_login(db, body.student_number, body.code,
                                ip=_get_client_ip(request))
    if not result["ok"]:
        raise HTTPException(status_code=401, detail=result["reason"])
    user = result["user"]
    token = auth_svc.issue_session_token(user.username)
    return {"ok": True, "token": token, "role": user.role,
            "display_name": user.display_name, "username": user.username}


@router.post("/auth/login")
def auth_password(body: PasswordLoginModel, request: Request, db: Session = Depends(get_db)):
    result = auth_svc.password_login(db, body.username, body.password,
                                     ip=_get_client_ip(request))
    if not result["ok"]:
        raise HTTPException(status_code=401, detail=result["reason"])
    user = result["user"]
    token = auth_svc.issue_session_token(user.username)
    return {"ok": True, "token": token, "role": user.role,
            "display_name": user.display_name, "username": user.username}


@router.get("/audit-logs")
def audit_logs(limit: int = 100, db: Session = Depends(get_db)):
    rows = auth_svc.read_audit_logs(db, limit=min(limit, 500))
    return [
        {
            "id": r.id, "student_number": r.student_number, "role": r.role,
            "action": r.action, "entity": r.entity, "entity_id": r.entity_id,
            "detail": r.detail, "ip_address": r.ip_address,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        } for r in rows
    ]


# =====================================================================
# Profile (STU-PRO)
# =====================================================================

@router.get("/profile")
def get_profile(student: Student = Depends(get_current_student),
                db: Session = Depends(get_db)):
    return profile_svc.get_profile(db, student)


@router.get("/profile/weekly-schedule")
def weekly_schedule(student: Student = Depends(get_current_student),
                    db: Session = Depends(get_db)):
    return profile_svc.get_weekly_schedule(db, student)


class DiscrepancyModel(BaseModel):
    field: str
    current_value: str = None
    claimed_value: str = None
    description: str = None


@router.post("/profile/discrepancy")
def report_discrepancy(body: DiscrepancyModel, request: Request,
                       student: Student = Depends(get_current_student),
                       db: Session = Depends(get_db)):
    report = profile_svc.report_discrepancy(db, student, body.model_dump(),
                                            ip=_get_client_ip(request))
    return {"ok": True, "report_id": report.id,
            "message": "اعلام مغایرت ثبت شد و توسط آموزش بررسی خواهد شد. "
                       "داده‌های رسمی مستقیماً تغییر نمی‌کند."}


@router.get("/profile/discrepancies")
def list_discrepancies(student: Student = Depends(get_current_student),
                       db: Session = Depends(get_db)):
    return profile_svc.list_discrepancies(db, student)


# =====================================================================
# Regulations assistant (STU-REG)
# =====================================================================

class AskModel(BaseModel):
    question: str


@router.post("/regulations/ask")
def regulations_ask(body: AskModel, request: Request,
                    student: Student = Depends(get_current_student),
                    db: Session = Depends(get_db)):
    if not body.question.strip():
        raise HTTPException(status_code=422, detail="سؤال خالی است.")
    return reg_svc.ask_regulations(db, student.id, student.student_number,
                                   body.question, ip=_get_client_ip(request))


class FeedbackModel(BaseModel):
    feedback: str  # helpful | not-helpful


@router.post("/regulations/{conversation_id}/feedback")
def regulations_feedback(conversation_id: int, body: FeedbackModel,
                         student: Student = Depends(get_current_student),
                         db: Session = Depends(get_db)):
    result = reg_svc.set_conversation_feedback(db, student.student_number,
                                               conversation_id, body.feedback)
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result["reason"])
    return result


@router.get("/regulations/history")
def regulations_history(student: Student = Depends(get_current_student),
                        db: Session = Depends(get_db)):
    return reg_svc.list_conversations(db, student.id, "regulations")


# =====================================================================
# Process guides (بند ۸-۴)
# =====================================================================

@router.get("/guides")
def guides(category: str = None, db: Session = Depends(get_db)):
    return reg_svc.list_process_guides(db, category)


@router.get("/guides/{slug}")
def guide_detail(slug: str, db: Session = Depends(get_db)):
    guide = reg_svc.get_process_guide(db, slug)
    if not guide:
        raise HTTPException(status_code=404, detail="راهنما یافت نشد.")
    return guide


# =====================================================================
# Course selection assistant (STU-CRS) + prerequisite analysis
# =====================================================================

@router.get("/selection/assistant")
def selection_assistant(term: str,
                        student: Student = Depends(get_current_student),
                        db: Session = Depends(get_db)):
    return acad_svc.build_selection_assistant(db, student, term)


@router.get("/selection/courses/{course_code}/analysis")
def course_analysis(course_code: str,
                    student: Student = Depends(get_current_student),
                    db: Session = Depends(get_db)):
    return acad_svc.analyze_course(db, student, course_code)


class ScenarioModel(BaseModel):
    term: str
    name: str
    course_codes: list[str]


@router.post("/selection/scenarios")
def save_scenario(body: ScenarioModel, request: Request,
                  student: Student = Depends(get_current_student),
                  db: Session = Depends(get_db)):
    return acad_svc.save_scenario(db, student, body.term, body.name,
                                  body.course_codes, ip=_get_client_ip(request))


@router.get("/selection/scenarios")
def list_scenarios(student: Student = Depends(get_current_student),
                   db: Session = Depends(get_db)):
    return acad_svc.list_scenarios(db, student)


# =====================================================================
# Graduation check (STU-GRD)
# =====================================================================

@router.get("/graduation/check")
def graduation_check(student: Student = Depends(get_current_student),
                     db: Session = Depends(get_db)):
    result = acad_svc.check_graduation(db, student)
    auth_svc.write_audit_log(db, student_number=student.student_number,
                             action="graduation-check",
                             detail=f"نتیجه: {result.get('result')}")
    return result


# =====================================================================
# Calendar & reminders + notification channels (بند ۸-۸)
# =====================================================================

@router.get("/calendar")
def calendar(term: str = None, db: Session = Depends(get_db)):
    return cal_svc.get_calendar(db, term)


@router.get("/calendar/reminders")
def reminders(student: Student = Depends(get_current_student),
              db: Session = Depends(get_db)):
    return cal_svc.get_upcoming_reminders(db, student)


@router.get("/notifications/channels")
def get_channels(student: Student = Depends(get_current_student),
                 db: Session = Depends(get_db)):
    return cal_svc.get_notification_channels(db, student)


class ChannelsModel(BaseModel):
    in_app: bool = None
    sms: bool = None
    email: bool = None
    mobile_push: bool = None


@router.put("/notifications/channels")
def update_channels(body: ChannelsModel,
                    student: Student = Depends(get_current_student),
                    db: Session = Depends(get_db)):
    return cal_svc.update_notification_channels(db, student, body.model_dump(exclude_none=True))


# =====================================================================
# Alerts & counseling (بند ۸-۹)
# =====================================================================

@router.get("/alerts")
def my_alerts(student: Student = Depends(get_current_student),
              db: Session = Depends(get_db)):
    return cal_svc.get_student_alerts(db, student)


class CounselingModel(BaseModel):
    alert_id: int
    message: str = None


@router.post("/alerts/counseling")
def counseling(body: CounselingModel, request: Request,
               student: Student = Depends(get_current_student),
               db: Session = Depends(get_db)):
    result = cal_svc.request_counseling(db, student, body.alert_id,
                                        body.message, ip=_get_client_ip(request))
    if not result["ok"]:
        raise HTTPException(status_code=404, detail=result["reason"])
    return result


# =====================================================================
# Quiz (بند ۸-۱۰)
# =====================================================================

class QuizGenerateModel(BaseModel):
    course_code: str
    difficulty: str = "medium"
    count: int = 3


@router.post("/quiz/generate")
def quiz_generate(body: QuizGenerateModel, request: Request,
                  student: Student = Depends(get_current_student),
                  db: Session = Depends(get_db)):
    result = qp_svc.generate_quiz(db, student, body.course_code,
                                  body.difficulty, body.count)
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result["reason"])
    return result


class QuizSubmitModel(BaseModel):
    answers: dict


@router.post("/quiz/{quiz_id}/submit")
def quiz_submit(quiz_id: int, body: QuizSubmitModel,
                student: Student = Depends(get_current_student),
                db: Session = Depends(get_db)):
    result = qp_svc.submit_quiz(db, student, quiz_id, body.answers)
    if not result["ok"]:
        raise HTTPException(status_code=404, detail=result["reason"])
    return result


@router.get("/quiz/history")
def quiz_history(student: Student = Depends(get_current_student),
                 db: Session = Depends(get_db)):
    return qp_svc.get_quiz_history(db, student)


# =====================================================================
# Smart professor (بند ۸-۱۱)
# =====================================================================

class ProfessorAskModel(BaseModel):
    course_code: str
    question: str
    mode: str = "simple"  # simple | advanced


@router.post("/professor/ask")
def professor_ask(body: ProfessorAskModel,
                  student: Student = Depends(get_current_student),
                  db: Session = Depends(get_db)):
    if not body.question.strip():
        raise HTTPException(status_code=422, detail="سؤال خالی است.")
    result = qp_svc.ask_smart_professor(db, student, body.course_code,
                                        body.question, body.mode)
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result["reason"])
    return result


class ExerciseModel(BaseModel):
    course_code: str
    topic: str = None


@router.post("/professor/exercise")
def professor_exercise(body: ExerciseModel,
                       student: Student = Depends(get_current_student),
                       db: Session = Depends(get_db)):
    result = qp_svc.design_exercise(db, student, body.course_code, body.topic)
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result["reason"])
    return result


@router.get("/professor/history")
def professor_history(student: Student = Depends(get_current_student),
                      db: Session = Depends(get_db)):
    return reg_svc.list_conversations(db, student.id, "smart-professor")
