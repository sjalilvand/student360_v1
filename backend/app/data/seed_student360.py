# Student 360 — seed data for pilot phase.
# Creates a pilot program, students, transcript, terms, rules, regulations,
# process guides, calendar events, learning contents and demo users.
from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.student360 import (
    Program, Curriculum, Student, AcademicStatus, Term, Enrollment, Grade,
    CourseRule, Regulation, ProcessGuide, CalendarEvent, Alert,
    LearningContent, StaffUser, UnifiedUser, NotificationChannel,
)
from app.services.student360_auth import _hash_password


def _ensure(db: Session, model, filters: dict, defaults: dict):
    obj = db.query(model).filter_by(**filters).first()
    if not obj:
        obj = model(**{**filters, **defaults})
        db.add(obj)
        db.flush()
    return obj


def seed_student360(db: Session) -> dict:
    """Idempotent seeding — safe to run at every startup."""
    created = {"students": 0, "regulations": 0, "guides": 0, "events": 0}

    # ================= Program / Curriculum =================
    program = _ensure(db, Program, {"title": "مهندسی کامپیوتر", "level": "کارشناسی"}, {
        "orientation": "نرم‌افزار",
        "department": "دانشکده مهندسی کامپیوتر",
        "curriculum_version": "1403",
        "total_units": 140,
        "min_gpa_graduation": 12.0,
        "max_allowed_terms": 8,
    })

    curriculum_rows = [
        # (code, title, credits, nature, term, chain)
        ("CS101", "مبانی کامپیوتر و برنامه‌سازی", 3, "main-obligatory", 1, True),
        ("MATH101", "ریاضی عمومی ۱", 3, "general", 1, False),
        ("PHYS101", "فیزیک عمومی ۱", 3, "general", 1, False),
        ("CS102", "برنامه‌سازی پیشرفته", 3, "main-obligatory", 2, True),
        ("MATH102", "ریاضی عمومی ۲", 3, "general", 2, False),
        ("CS201", "ساختمان داده", 3, "main-obligatory", 3, True),
        ("CS202", "مدار منطقی", 3, "main-obligatory", 3, False),
        ("CS301", "سیستم‌عامل", 3, "main-obligatory", 5, True),
        ("CS302L", "آزمایشگاه سیستم‌عامل", 1, "main-obligatory", 5, False),
        ("CS303", "طراحی الگوریتم", 3, "main-obligatory", 5, False),
        ("CS401", "مهندسی نرم‌افزار", 3, "main-obligatory", 7, False),
        ("CS499", "پروژه", 3, "main-obligatory", 8, False),
        ("ELEC01", "درس اختیاری ۱", 2, "elective", 7, False),
        ("ELEC02", "درس اختیاری ۲", 2, "elective", 8, False),
        ("GEN01", "تربیت بدنی", 1, "general", 1, False),
    ]
    for code, title, credits, nature, term, chain in curriculum_rows:
        _ensure(db, Curriculum, {"program_id": program.id, "course_code": code}, {
            "course_title": title, "credits": credits,
            "course_nature": nature, "suggested_term": term,
            "is_chain_course": chain,
        })

    # ================= Terms =================
    today = date.today()
    t1 = _ensure(db, Term, {"code": "1403-1"}, {
        "title": "نیمسال اول ۱۴۰۳-۱۴۰۴", "start_date": date(2024, 9, 21),
        "end_date": date(2025, 1, 19), "is_current": False,
    })
    t2 = _ensure(db, Term, {"code": "1403-2"}, {
        "title": "نیمسال دوم ۱۴۰۳-۱۴۰۴", "start_date": date(2025, 2, 9),
        "end_date": date(2025, 6, 8), "is_current": False,
    })
    t3 = _ensure(db, Term, {"code": "1404-1"}, {
        "title": "نیمسال اول ۱۴۰۴-۱۴۰۵", "start_date": today - timedelta(days=60),
        "end_date": today + timedelta(days=60),
        "is_current": True,
        "is_open_for_registration": True,
    })
    tnext = _ensure(db, Term, {"code": "1404-2"}, {
        "title": "نیمسال دوم ۱۴۰۴-۱۴۰۵", "start_date": today + timedelta(days=90),
        "end_date": today + timedelta(days=180),
        "is_current": False,
        "is_open_for_registration": True,   # نیمسال آینده برای انتخاب واحد
    })

    # ================= Students =================
    s1 = _ensure(db, Student, {"student_number": "402101001"}, {
        "first_name": "علی", "last_name": "محمدی",
        "program_id": program.id, "entry_term": "1402-1", "entry_year": "1402",
        "status": "active", "email": "ali.mohammadi@uni.ac.ir",
        "phone": "09120000001", "is_pilot": True,
        "sso_username": "a.mohammadi",
        "last_data_sync_at": datetime.now() - timedelta(hours=6),
    })
    s2 = _ensure(db, Student, {"student_number": "402101002"}, {
        "first_name": "سارا", "last_name": "کریمی",
        "program_id": program.id, "entry_term": "1402-1", "entry_year": "1402",
        "status": "active", "email": "sara.karimi@uni.ac.ir",
        "phone": "09120000002", "is_pilot": True,
        "sso_username": "s.karimi",
    })

    # وضعیت تحصیلی
    _ensure(db, AcademicStatus, {"student_id": s1.id, "term": "1403-2"}, {
        "status": "normal", "probation_count": 1,
        "effective_from": date(2025, 2, 9), "effective_to": date(2025, 6, 8),
    })

    # ================= Transcript (Grades) =================
    transcript = [
        # term, code, title, credits, grade, status
        ("1402-1", "CS101", "مبانی کامپیوتر و برنامه‌سازی", 3, 17.0, "passed"),
        ("1402-1", "MATH101", "ریاضی عمومی ۱", 3, 15.5, "passed"),
        ("1402-1", "GEN01", "تربیت بدنی", 1, 19.0, "passed"),
        ("1402-2", "CS102", "برنامه‌سازی پیشرفته", 3, 14.0, "passed"),
        ("1402-2", "MATH102", "ریاضی عمومی ۲", 3, 9.5, "failed"),
        ("1402-2", "PHYS101", "فیزیک عمومی ۱", 3, 12.0, "passed"),
        ("1403-1", "CS201", "ساختمان داده", 3, 11.0, "passed"),
        ("1403-1", "CS202", "مدار منطقی", 3, 16.5, "passed"),
        ("1403-1", "MATH102", "ریاضی عمومی ۲", 3, 14.5, "passed"),
        ("1403-2", "CS301", "سیستم‌عامل", 3, None, "in-progress"),
    ]
    for term, code, title, credits, grade, status in transcript:
        _ensure(db, Grade, {"student_id": s1.id, "term": term, "course_code": code}, {
            "course_title": title, "credits": credits, "grade": grade, "status": status,
            "graded_at": datetime.now() if grade is not None else None,
        })

    # دروس جاری نیمسال (برنامه هفتگی)
    current_enrollments = [
        ("CS301", "سیستم‌عامل", 3, 0, "08:00", "10:00", "دکتر احمدی"),
        ("CS302L", "آزمایشگاه سیستم‌عامل", 1, 2, "13:00", "15:00", "مهندس کریمی"),
        ("CS303", "طراحی الگوریتم", 3, 1, "10:00", "12:00", "دکتر رضایی"),
    ]
    for code, title, credits, day, st, et, instr in current_enrollments:
        _ensure(db, Enrollment, {"student_id": s1.id, "term": "1404-1", "course_code": code}, {
            "course_title": title, "credits": credits,
            "class_day": day, "start_time": st, "end_time": et,
            "instructor_name": instr, "status": "current",
        })

    # ================= CourseRules (با تاریخ اعتبار) =================
    rules = [
        ("CS102", "prerequisite", "CS101", 10.0, None),
        ("CS201", "prerequisite", "CS102", 10.0, None),
        ("CS301", "prerequisite", "CS201", 10.0, None),
        ("CS302L", "corequisite", "CS301", None, None),
        ("CS303", "prerequisite", "CS201", 10.0, None),
        ("CS401", "prerequisite", "CS301", 10.0, None),
        ("CS499", "prerequisite", "CS401", 10.0, None),
        ("CS201", "probation-restriction", None, None, "در وضعیت مشروطی حداکثر ۱۴ واحد مجاز است."),
    ]
    for course, rtype, related, ming, detail in rules:
        _ensure(db, CourseRule,
                {"course_code": course, "rule_type": rtype, "related_course_code": related}, {
                    "min_grade": ming, "restriction_detail": detail,
                    "effective_from": date(2024, 9, 1),  # تاریخ شروع اعتبار
                })

    # ================= Regulations (دستیار آیین‌نامه‌ای) =================
    regulations = [
        ("academic-regulations", "آیین‌نامه آموزشی دوره کارشناسی", "ماده ۲۳", None,
         "حداقل معدل قبولی در هر نیمسال ۱۲ است. دانشجویی که معدل نیمسال او کمتر از ۱۲ باشد، در آن نیمسال مشروط محسوب می‌شود.",
         "معدل، مشروطی، قبولی", "آیین‌نامه آموزشی دانشگاه", date(2023, 9, 1), date(2028, 8, 31)),
        ("academic-regulations", "آیین‌نامه آموزشی دوره کارشناسی", "ماده ۲۶", None,
         "حداکثر مدت مجاز تحصیل در دوره کارشناسی پیوسته ۸ نیمسال است.",
         "سنوات، مدت مجاز", "آیین‌نامه آموزشی دانشگاه", date(2023, 9, 1), date(2028, 8, 31)),
        ("academic-regulations", "آیین‌نامه آموزشی دوره کارشناسی", "ماده ۲۷", None,
         "دانشجو می‌تواند حداکثر دو بار در طول دوره تحصیل از وضعیت مشروطی به وضعیت عادی بازگردد.",
         "مشروطی، اخراج", "آیین‌نامه آموزشی دانشگاه", date(2023, 9, 1), date(2028, 8, 31)),
        ("course-selection", "شیوه‌نامه انتخاب واحد", "ماده ۵", None,
         "حداکثر واحدهای قابل اخذ دانشجو در هر نیمسال ۲۰ واحد و برای دانشجوی مشروط ۱۴ واحد است. دانشجوی ممتاز (معدل بالای ۱۷) می‌تواند تا ۲۴ واحد اخذ کند.",
         "انتخاب واحد، سقف واحد", "شیوه‌نامه انتخاب واحد دانشگاه", date(2024, 8, 1), date(2027, 7, 31)),
        ("add-drop", "مقررات حذف و اضافه", "ماده ۱", "تبصره ۲",
         "حذف و اضافه در هفته اول و دوم نیمسال از طریق سامانه آموزش امکان‌پذیر است.",
         "حذف اضافه", "بخشنامه آموزش", date(2024, 8, 1), None),
        ("leave-of-absence", "مقررات مرخصی تحصیلی", "ماده ۱", None,
         "دانشجو می‌تواند حداکثر دو نیمسال (پيوسته) یا چهار نیمسال (ناپیوسته) مرخصی تحصیلی اخذ کند.",
         "مرخصی تحصیلی", "آیین‌نامه آموزشی دانشگاه", date(2023, 9, 1), date(2028, 8, 31)),
        ("transfer-guest", "مقررات مهمانی و انتقال", "ماده ۱۲", None,
         "درخواست انتقال فقط یک‌بار در طول دوره تحصیل و پیش از گذراندن نیمی از واحدهای دوره امکان‌پذیر است.",
         "انتقال، مهمانی", "آیین‌نامه آموزشی دانشگاه", date(2023, 9, 1), date(2028, 8, 31)),
        ("graduation", "شرایط فارغ‌التحصیلی", "ماده ۳۴", None,
         "فارغ‌التحصیلی مستلزم گذراندن تمام دروس برنامه مصوب، کسب معدل کل حداقل ۱۲ و عدم منع آموزشی است.",
         "فارغ‌التحصیلی، سرفصل", "آیین‌نامه آموزشی دانشگاه", date(2023, 9, 1), date(2028, 8, 31)),
        ("circular", "بخشنامه حذف اضطراری", "ماده ۱", None,
         "حذف اضطراری فقط با تأیید استاد و آموزش و حداکثر تا نیم‌سال تحصیلی مجاز است.",
         "حذف اضطراری", "بخشنامه معاونت آموزشی", date(2025, 8, 1), None),
    ]
    for dtype, title, article, clause, content, kw, src, vfrom, vto in regulations:
        existing = db.query(Regulation).filter_by(title=title, article=article).first()
        if not existing:
            db.add(Regulation(
                doc_type=dtype, title=title, article=article, clause=clause,
                content=content, keywords=kw, source_name=src,
                valid_from=vfrom, valid_to=vto,
            ))
            created["regulations"] += 1

    # ================= Process Guides =================
    guides = [
        {
            "slug": "leave-of-absence", "title": "درخواست مرخصی تحصیلی",
            "category": "وضعیت تحصیلی",
            "conditions": "گذراندن حداقل یک نیمسال، عدم وجود منع آموزشی، حداکثر دو نیمسال مرخصی در مقطع کارشناسی پیوسته.",
            "required_documents": ["فرم درخواست مرخصی", "کارت دانشجویی"],
            "steps": ["ثبت درخواست در سامانه آموزش", "تأیید گروه آموزشی", "تأیید معاونت آموزشی", "اعلام نتیجه به دانشجو"],
            "responsible_unit": "معاونت آموزشی",
            "deadline": "تا پایان هفته سوم نیمسال قبل",
            "system_url": "https://edu.uni.ac.ir/leave",
            "processing_time": "حدود ۵ روز کاری",
            "related_rules": "آیین‌نامه آموزشی، ماده ۳۵",
        },
        {
            "slug": "emergency-drop", "title": "حذف اضطراری",
            "category": "انتخاب واحد",
            "conditions": "فقط یک بار در طول دوره تحصیل و برای حداکثر یک درس؛ با دلیل موجه.",
            "required_documents": ["فرم حذف اضطراری", "مدارک مستند دلیل"],
            "steps": ["ثبت درخواست", "تأیید استاد درس", "تأیید معاونت آموزشی"],
            "responsible_unit": "معاونت آموزشی",
            "deadline": "تا پایان هفته دهم نیمسال",
            "system_url": "https://edu.uni.ac.ir/emergency-drop",
            "processing_time": "حدود ۷ روز کاری",
            "related_rules": "بخشنامه حذف اضطراری، ماده ۱",
        },
        {
            "slug": "add-drop", "title": "حذف و اضافه",
            "category": "انتخاب واحد",
            "conditions": "پیش از پایان هفته دوم نیمسال؛ حفظ حداقل و حداکثر واحد مجاز.",
            "required_documents": ["دسترسی به سامانه آموزش"],
            "steps": ["ورود به سامانه آموزش", "بخش حذف و اضافه", "تغییر واحدها", "تأیید نهایی"],
            "responsible_unit": "مرکز آموزش",
            "deadline": "هفته اول و دوم نیمسال",
            "system_url": "https://edu.uni.ac.ir/adddrop",
            "processing_time": "فوری (برخط)",
            "related_rules": "مقررات حذف و اضافه، ماده ۱ تبصره ۲",
        },
        {
            "slug": "grade-appeal", "title": "اعتراض به نمره",
            "category": "آموزشی",
            "conditions": "حداکثر تا ۷ روز پس از اعلام نمره.",
            "required_documents": ["فرم اعتراض", "توضیح مکتوب"],
            "steps": ["ثبت اعتراض در سامانه", "بررسی توسط استاد", "اعلام نتیجه به گروه آموزشی"],
            "responsible_unit": "گروه آموزشی",
            "deadline": "۷ روز پس از اعلام نمره",
            "system_url": "https://edu.uni.ac.ir/appeal",
            "processing_time": "حدود ۱۰ روز کاری",
            "related_rules": "آیین‌نامه آموزشی، ماده ۵۱",
        },
        {
            "slug": "professor-intro", "title": "معرفی به استاد",
            "category": "پایان‌نامه",
            "conditions": "گذراندن حداقل ۷۰ واحد و داشتن معدل مناسب.",
            "required_documents": ["فرم معرفی به استاد", "رزومه آموزشی"],
            "steps": ["انتخاب استاد پیشنهادی", "ثبت درخواست", "تأیید گروه آموزشی"],
            "responsible_unit": "گروه آموزشی",
            "deadline": "طبق تقویم آموزشی",
            "system_url": "https://edu.uni.ac.ir/professor-intro",
            "processing_time": "حدود ۱۴ روز کاری",
            "related_rules": "دستورالعمل پایان‌نامه",
        },
        {
            "slug": "guest-request", "title": "درخواست مهمانی",
            "category": "انتقال و مهمانی",
            "conditions": "گذراندن حداقل یک نیمسال، اخذ درس‌های غیرقابل ارائه در دانشگاه اصلی.",
            "required_documents": ["فرم درخواست مهمانی", "درخواست دانشگاه مقصد"],
            "steps": ["ثبت درخواست در سامانه", "تأیید دانشگاه مبدأ", "تأیید دانشگاه مقصد"],
            "responsible_unit": "معاونت آموزشی",
            "deadline": "قبل از شروع انتخاب واحد نیمسال مقصد",
            "system_url": "https://edu.uni.ac.ir/guest",
            "processing_time": "حدود ۲۰ روز کاری",
            "related_rules": "آیین‌نامه مهمانی و انتقال، ماده ۱۲",
        },
        {
            "slug": "transfer-request", "title": "درخواست انتقال",
            "category": "انتقال و مهمانی",
            "conditions": "داشتن دلیل موجه (نظری، جسمی، خانوادگی)؛ فقط یک‌بار در دوره تحصیل.",
            "required_documents": ["فرم انتقال", "مدارک مستند"],
            "steps": ["ثبت درخواست", "بررسی کمیسیون انتقال", "اعلام نتیجه"],
            "responsible_unit": "سازمان مرکزی دانشگاه",
            "deadline": "طبق بخشنامه سالانه",
            "system_url": "https://edu.uni.ac.ir/transfer",
            "processing_time": "حدود ۳۰ روز کاری",
            "related_rules": "آیین‌نامه مهمانی و انتقال، ماده ۱۲",
        },
        {
            "slug": "unit-matching", "title": "درخواست تطبیق واحد",
            "category": "انتقال و مهمانی",
            "conditions": "برای دانشجویان منتقل یا مهمان.",
            "required_documents": ["ریزنمرات دانشگاه قبلی", "سرفصل دروس"],
            "steps": ["ثبت درخواست", "بررسی گروه آموزشی", "تأیید معاونت آموزشی"],
            "responsible_unit": "گروه آموزشی",
            "deadline": "تا پایان هفته دوم نیمسال",
            "system_url": "https://edu.uni.ac.ir/matching",
            "processing_time": "حدود ۱۵ روز کاری",
            "related_rules": "آیین‌نامه آموزشی، ماده ۵۶",
        },
        {
            "slug": "study-certificate", "title": "گواهی اشتغال به تحصیل",
            "category": "اداری",
            "conditions": "عدم وجود منع آموزشی یا مالی.",
            "required_documents": ["درخواست برخط"],
            "steps": ["ثبت درخواست برخط", "صدور خودکار گواهی"],
            "responsible_unit": "مرکز آموزش",
            "deadline": "بدون مهلت",
            "system_url": "https://edu.uni.ac.ir/certificate",
            "processing_time": "فوری (برخط)",
            "related_rules": "دستورالعمل صدور گواهی‌ها",
        },
        {
            "slug": "graduation-settlement", "title": "تسویه‌حساب و فارغ‌التحصیلی",
            "category": "فارغ‌التحصیلی",
            "conditions": "گذراندن کامل واحدهای دوره و تأیید آموزش.",
            "required_documents": ["تسویه‌حساب کتابخانه", "تسویه‌حساب خوابگاه", "تسویه‌حساب مالی"],
            "steps": ["بررسی کسری واحدها", "تسویه‌حساب با واحدها", "دریافت مدرک"],
            "responsible_unit": "معاونت آموزشی",
            "deadline": "طبق تقویم آموزشی",
            "system_url": "https://edu.uni.ac.ir/graduation",
            "processing_time": "حدود ۳۰ روز کاری",
            "related_rules": "آیین‌نامه آموزشی، ماده ۳۴",
        },
    ]
    for g in guides:
        existing = db.query(ProcessGuide).filter_by(slug=g["slug"]).first()
        if not existing:
            import json as _json
            db.add(ProcessGuide(
                slug=g["slug"], title=g["title"], category=g["category"],
                conditions=g["conditions"],
                required_documents=_json.dumps(g["required_documents"], ensure_ascii=False),
                steps=_json.dumps(g["steps"], ensure_ascii=False),
                responsible_unit=g["responsible_unit"], deadline=g["deadline"],
                system_url=g["system_url"], processing_time=g["processing_time"],
                related_rules=g["related_rules"],
            ))
            created["guides"] += 1

    # ================= Calendar Events =================
    events = [
        ("1404-2", "course-selection-start", "شروع انتخاب واحد نیمسال دوم", today + timedelta(days=3), 2),
        ("1404-2", "course-selection-end", "پایان انتخاب واحد نیمسال دوم", today + timedelta(days=10), 2),
        ("1404-2", "add-drop", "حذف و اضافه نیمسال دوم", today + timedelta(days=11), 2),
        ("1404-2", "emergency-drop", "حذف اضطراری نیمسال دوم", today + timedelta(days=45), 5),
        ("1404-1", "exams", "امتحانات پایان نیمسال اول", today + timedelta(days=25), 7),
        ("1404-1", "tuition-payment", "مهلت پرداخت شهریه", today + timedelta(days=5), 3),
        ("1404-1", "grade-appeal", "مهلت اعتراض به نمره", today + timedelta(days=40), 3),
        ("1404-1", "supervisor-selection", "مهلت انتخاب استاد راهنما", today + timedelta(days=50), 7),
        ("1404-1", "thesis-defense", "مهلت دفاع/ثبت پایان‌نامه", today + timedelta(days=120), 14),
    ]
    for term, etype, title, edate, offset in events:
        existing = db.query(CalendarEvent).filter_by(term=term, event_type=etype).first()
        if not existing:
            db.add(CalendarEvent(term=term, event_type=etype, title=title,
                                 event_date=edate, reminder_offset_days=offset))
            created["events"] += 1

    # ================= Learning contents (برای دروس منتخب استاد هوشمند) =================
    contents = [
        ("CS201", "ساختمان داده — پشته و صف", "text",
         "پشته ساختاری LIFO است: آخرین داده‌ای که وارد می‌شود، اول خارج می‌شود. صف ساختاری FIFO است: اولین داده واردشده، اولین داده خارج‌شده. عملیات اصلی پشته push و pop و عملیات اصلی صف enqueue و dequeue است.",
         "فصل ۳"),
        ("CS201", "ساختمان داده — درخت جست‌وجوی دودویی", "text",
         "درخت جست‌وجوی دودویی درختی است که برای هر گره، مقادیر زیردرخت چپ کوچکتر و مقادیر زیردرخت راست بزرگتر از مقدار گره هستند. میانگین هزینه جست‌وجو O(log n) و در بدترین حالت O(n) است.",
         "فصل ۷"),
        ("CS301", "سیستم‌عامل — زمان‌بندی پردازنده", "text",
         "الگوریتم‌های زمان‌بندی پردازنده شامل FCFS، SJF، زمان‌بندی اولویتی و Round Robin هستند. Round Robin برای سیستم‌های تعاملی مناسب است و سهم زمانی (quantum) نقش کلیدی در پاسخ‌گویی دارد.",
         "فصل ۵"),
        ("CS101", "مبانی کامپیوتر و برنامه‌سازی — حلقه‌ها", "text",
         "حلقه while تا زمانی که شرط برقرار است تکرار می‌شود و حلقه for برای پیمایش دنباله‌ها به کار می‌رود. حلقه تو در تو برای پیمایش ماتریس‌ها استفاده می‌شود.",
         "فصل ۴"),
    ]
    for course, title, ctype, content, section in contents:
        _ensure(db, LearningContent, {"course_code": course, "title": title}, {
            "content_type": ctype, "content": content, "section_ref": section,
            "is_verified": True, "uploaded_by": "staff-admin",
        })

    # ================= Staff / users =================
    admin = _ensure(db, StaffUser, {"username": "staff-admin"}, {
        "full_name": "کارشناس آموزش مرکزی", "role": "education-expert",
        "org_scope": "دانشکده مهندسی کامپیوتر", "can_view_sensitive_alerts": True,
    })
    advisor = _ensure(db, StaffUser, {"username": "advisor-1"}, {
        "full_name": "مشاور دانشکده", "role": "advisor",
        "org_scope": "دانشکده مهندسی کامپیوتر", "can_view_sensitive_alerts": False,
    })

    _ensure(db, UnifiedUser, {"username": "402101001"}, {
        "display_name": "علی محمدی", "role": "student", "ref_id": s1.id,
        "sso_subject": "a.mohammadi",
    })
    _ensure(db, UnifiedUser, {"username": "402101002"}, {
        "display_name": "سارا کریمی", "role": "student", "ref_id": s2.id,
        "sso_subject": "s.karimi",
    })
    _ensure(db, UnifiedUser, {"username": "staff-admin"}, {
        "display_name": "کارشناس آموزش مرکزی", "role": "education-expert",
        "ref_id": admin.id, "password_hash": _hash_password("admin123"),
    })
    _ensure(db, UnifiedUser, {"username": "advisor-1"}, {
        "display_name": "مشاور دانشکده", "role": "advisor",
        "ref_id": advisor.id, "password_hash": _hash_password("advisor123"),
    })

    ensure_channel = NotificationChannel(student_id=s1.id) if not db.query(
        NotificationChannel).filter_by(student_id=s1.id).first() else None
    if ensure_channel:
        db.add(ensure_channel)

    db.commit()
    created["students"] = 2
    return created
