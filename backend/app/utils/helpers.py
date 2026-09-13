# app/utils/helpers.py  (v2 - circular-import safe)
from typing import Dict

from .constants import DAY_NAMES
from .normalization import normalize_code, normalize_instructor_code
from .time_utils import time_to_minutes, slot_overlap, calculate_time_match_score


def get_day_name(day_num: int) -> str:
    """نام فارسی روز بر اساس شماره (۰ تا ۵ برای شنبه تا پنجشنبه)."""
    return DAY_NAMES[day_num] if 0 <= day_num < 6 else str(day_num)


def is_internship_or_project(course: Dict) -> bool:
    """تشخیص درس کارآموزی/پروژه."""
    course_type = course.get("course_type") or ""
    if course_type.lower() in ["internship", "project", "کارآموزی", "پروژه"]:
        return True
    name = course.get("course_name") or ""
    if "کارآموزی" in name or "پروژه" in name:
        return True
    return False


# ===== re-export از slot_times =====
# v2: این import عمداً در انتهای فایل است. زنجیره گردش:
#   slot_times -> services/__init__ -> time_scheduler -> (time_to_minutes,
#   slot_overlap, get_day_name) از همین ماژول. با قرارگیری در انتها، این
#   نام‌ها قبل از بازگشت حلقه تعریف شده‌اند و import مستقل دیگر crash نمی‌کند.
try:
    from app.services.schedule.slot_times import normalize_day, DAY_MAP  # noqa: E402,F401
except Exception as _slot_imp_err:  # pragma: no cover
    print(f"WARNING: lazy slot_times re-export failed: {_slot_imp_err}")
