# Student 360 — auth, roles, org-scope access and audit logging (STU-AUTH-01..05).
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.student360 import AuditLog, StaffUser, Student, UnifiedUser

# =====================================================================
# STU-AUTH-04 / قاعده ۹-۱۰ — لاگ ممیزی برای هر عمل حساس
# =====================================================================
SENSITIVE_ACTIONS = {
    "login", "login-failed", "logout", "otp-request", "otp-verify",
    "view-profile", "view-grades", "view-transcript",
    "view-sensitive-alert", "request-counseling", "save-scenario",
    "confirm-official-registration", "graduation-check", "report-discrepancy",
    "regulation-ask", "quiz-generate", "quiz-submit", "export-report",
    "view-student-as-staff", "rule-change",
}


def write_audit_log(
    db: Session,
    *,
    student_number: str,
    action: str,
    role: str = "student",
    entity: str = None,
    entity_id: str = None,
    detail: str = None,
    ip_address: str = None,
) -> AuditLog:
    """ثبت رخداد در لاگ ممیزی — هر ورود و عملیات حساس (STU-AUTH-04)."""
    entry = AuditLog(
        student_number=student_number,
        role=role,
        action=action,
        entity=entity,
        entity_id=str(entity_id) if entity_id is not None else None,
        detail=detail,
        ip_address=ip_address,
    )
    db.add(entry)
    db.commit()
    return entry


def read_audit_logs(db: Session, limit: int = 200):
    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()


# =====================================================================
# هش رمز (بدون وابستگی خارجی؛ SHA-256 salted)
# =====================================================================
def _hash_password(password: str, salt: str = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return f"sha256${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt, digest = stored.split("$")
    except ValueError:
        return False
    candidate = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return hmac.compare_digest(candidate, digest)


# =====================================================================
# OTP — STU-AUTH-02: ورود با شناسه دانشجویی و رمز یک‌بارمصرف
# =====================================================================
class OTPService:
    """رمزهای یک‌بارمصرف در حافظه؛ در نسخه نهایی باید در Redis/دیتابیس ذخیره شود."""

    TTL_SECONDS = 120
    MAX_ATTEMPTS = 3

    def __init__(self):
        self._store: dict[str, dict] = {}

    def issue(self, student_number: str) -> str:
        code = f"{secrets.randbelow(1000000):06d}"
        self._store[student_number] = {
            "code": code,
            "expires_at": datetime.now(timezone.utc) + timedelta(seconds=self.TTL_SECONDS),
            "attempts": 0,
        }
        # در نسخه نهایی: ارسال پیامک. در پایلوت، کد در پاسخ برگردانده می‌شود.
        return code

    def verify(self, student_number: str, code: str) -> tuple[bool, str]:
        record = self._store.get(student_number)
        if not record:
            return False, "درخواست رمز یک‌بارمصرف ثبت نشده است."
        if datetime.now(timezone.utc) > record["expires_at"]:
            del self._store[student_number]
            return False, "رمز یک‌بارمصرف منقضی شده است."
        record["attempts"] += 1
        if record["attempts"] > self.MAX_ATTEMPTS:
            del self._store[student_number]
            return False, "تعداد تلاش‌های ناموفق بیش از حد مجاز است."
        if not hmac.compare_digest(record["code"], str(code)):
            return False, "رمز یک‌بارمصرف نادرست است."
        del self._store[student_number]
        return True, "verified"


otp_service = OTPService()


# =====================================================================
# دسترسی نقش‌محور و محدوده سازمانی — STU-AUTH-03 و STU-AUTH-05
# =====================================================================
def get_unified_user(db: Session, username: str) -> Optional[UnifiedUser]:
    return db.query(UnifiedUser).filter(UnifiedUser.username == username).first()


def get_staff_user(db: Session, username: str) -> Optional[StaffUser]:
    return db.query(StaffUser).filter(StaffUser.username == username).first()


def can_access_student(staff: StaffUser, student: Student) -> bool:
    """کنترل دسترسی کارشناس/مشاور بر اساس نقش و محدوده سازمانی (STU-AUTH-05)."""
    if staff.role == "admin":
        return True
    if staff.role in ("education-expert", "advisor"):
        # محدوده سازمانی: گروه/دانشکده دانشجو باید با محدوده کاربر همخوان باشد
        if not staff.org_scope:
            return False
        student_scope = getattr(student, "org_scope", None) or ""
        return staff.org_scope in student_scope or student_scope == staff.org_scope
    return False


def can_view_sensitive_alerts(staff: StaffUser) -> bool:
    return bool(staff.can_view_sensitive_alerts) or staff.role == "admin"


def resolve_role(db: Session, username: str) -> tuple[Optional[UnifiedUser], str]:
    """تشخیص نقش کاربر: دانشجو یا کارشناس/مشاور."""
    user = get_unified_user(db, username)
    if user:
        return user, user.role
    return None, "unknown"


# =====================================================================
# ورود
# =====================================================================
def sso_login(db: Session, sso_token: str) -> dict:
    """STU-AUTH-01 — ورود از طریق SSO دانشگاه.

    در نسخه پایلوت، sso_token همان sso_subject کاربر است.
    در استقرار واقعی، این تابع باید توکن SSO را با سرور دانشگاه اعتبارسنجی کند.
    """
    user = db.query(UnifiedUser).filter(UnifiedUser.sso_subject == sso_token).first()
    if not user:
        return {"ok": False, "reason": "کاربر SSO شناسایی نشد."}
    return {
        "ok": True,
        "user": user,
        "role": user.role,
    }


def otp_request(db: Session, student_number: str) -> dict:
    """STU-AUTH-02 — گام ۱: درخواست رمز یک‌بارمصرف."""
    student = db.query(Student).filter(Student.student_number == student_number).first()
    if not student:
        return {"ok": False, "reason": "دانشجویی با این شماره دانشجویی یافت نشد."}
    code = otp_service.issue(student_number)
    write_audit_log(db, student_number=student_number, action="otp-request",
                    detail="درخواست رمز یک‌بارمصرف")
    # در پایلوت کد برگردانده می‌شود؛ در استقرار واقعی حذف شود و پیامک شود.
    return {"ok": True, "dev_code": code}


def otp_login(db: Session, student_number: str, code: str, ip: str = None) -> dict:
    """STU-AUTH-02 — گام ۲: تأیید رمز و ورود."""
    ok, message = otp_service.verify(student_number, code)
    if not ok:
        write_audit_log(db, student_number=student_number, action="login-failed",
                        detail=f"OTP نامعتبر: {message}")
        return {"ok": False, "reason": message}

    student = db.query(Student).filter(Student.student_number == student_number).first()
    if not student:
        return {"ok": False, "reason": "دانشجو یافت نشد."}

    user = get_unified_user(db, student_number)
    if not user:
        user = UnifiedUser(
            username=student_number,
            display_name=student.full_name,
            role="student",
            ref_id=student.id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    write_audit_log(db, student_number=student_number, action="login",
                    detail="ورود موفق با OTP", ip_address=ip)
    return {"ok": True, "user": user, "role": user.role}


def password_login(db: Session, username: str, password: str, ip: str = None) -> dict:
    """ورود با رمز (برای کارکنان و حالت جایگزین)."""
    user = get_unified_user(db, username)
    if not user or not user.password_hash or not verify_password(password, user.password_hash):
        write_audit_log(db, student_number=username, action="login-failed",
                        detail="نام کاربری یا رمز نادرست", ip_address=ip)
        return {"ok": False, "reason": "نام کاربری یا رمز نادرست است."}
    write_audit_log(db, student_number=username, action="login",
                    role=user.role, detail="ورود موفق با رمز", ip_address=ip)
    return {"ok": True, "user": user, "role": user.role}


def issue_session_token(username: str) -> str:
    """توکن نشست ساده (پایلوت). در استقرار واقعی JWT امضاشده جایگزین شود."""
    payload = f"{username}|{datetime.now(timezone.utc).isoformat()}"
    return secrets.token_urlsafe(32) + "$" + payload


def parse_session_token(token: str) -> Optional[str]:
    try:
        payload = token.split("$", 1)[1]
        username = payload.split("|", 1)[0]
        return username
    except Exception:
        return None


def ensure_notification_channel(db: Session, student_id: int):
    from app.models.student360 import NotificationChannel
    channel = db.query(NotificationChannel).filter(
        NotificationChannel.student_id == student_id).first()
    if not channel:
        channel = NotificationChannel(student_id=student_id)
        db.add(channel)
        db.commit()
        db.refresh(channel)
    return channel
