# app/utils/jalali.py  (v2)
# Forward conversion: standard verified algorithm (matches real-world dates).
# Inverse conversion: derived FROM the forward function (search + cache) so the
# two can never disagree. Fixes the calendar query window bug.
from datetime import date, datetime, timedelta

JALALI_MONTH_NAMES = (
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
)

_PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
_FARVARDIN_CACHE: dict = {}


def gregorian_to_jalali(gy: int, gm: int, gd: int):
    g_d_m = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)
    gy2, gm2, gd2 = gy - 1600, gm - 1, gd - 1
    g_day_no = 365 * gy2 + (gy2 + 3) // 4 - (gy2 + 99) // 100 + (gy2 + 399) // 400
    g_day_no += g_d_m[gm2]
    if gm2 > 1 and ((gy % 4 == 0 and gy % 100 != 0) or (gy % 400 == 0)):
        g_day_no += 1
    g_day_no += gd2
    j_day_no = g_day_no - 79
    j_np = j_day_no // 12053
    j_day_no %= 12053
    jy = 979 + 33 * j_np + 4 * (j_day_no // 1461)
    j_day_no %= 1461
    if j_day_no >= 366:
        jy += (j_day_no - 1) // 365
        j_day_no = (j_day_no - 1) % 365
    if j_day_no < 186:
        jm = 1 + j_day_no // 31
        jd = 1 + j_day_no % 31
    else:
        jm = 7 + (j_day_no - 186) // 30
        jd = 1 + (j_day_no - 186) % 30
    return jy, jm, jd


def _farvardin_first(jy: int) -> date:
    """Gregorian date of 1405/01/01-style Jalali new year (cached, search-based)."""
    if jy in _FARVARDIN_CACHE:
        return _FARVARDIN_CACHE[jy]
    start = date(jy + 621, 1, 1)
    for i in range(500):
        dt = start + timedelta(days=i)
        if gregorian_to_jalali(dt.year, dt.month, dt.day) == (jy, 1, 1):
            _FARVARDIN_CACHE[jy] = dt
            return dt
    raise ValueError(f"cannot locate Farvardin 1 for jalali year {jy}")


def jalali_to_gregorian(jy: int, jm: int, jd: int):
    offset = (31 * (jm - 1)) if jm <= 6 else (186 + 30 * (jm - 7))
    offset += (jd - 1)
    dt = _farvardin_first(jy) + timedelta(days=offset)
    return dt.year, dt.month, dt.day


def is_jalali_leap(jy: int) -> bool:
    return (jy % 33) in (1, 5, 9, 13, 17, 22, 26, 30)


def jalali_month_length(jy: int, jm: int) -> int:
    if jm <= 6:
        return 31
    if jm <= 11:
        return 30
    return 30 if is_jalali_leap(jy) else 29


def fa_str(jy: int, jm: int, jd: int) -> str:
    raw = f"{jy}/{jm:02d}/{jd:02d}"
    return raw.translate(_PERSIAN_DIGITS)


def today_jalali():
    n = datetime.utcnow()
    return gregorian_to_jalali(n.year, n.month, n.day)


def weekday_index_fa(dt: datetime) -> int:
    """0=شنبه ... 6=جمعه (Persian week order)."""
    return (dt.weekday() + 2) % 7
