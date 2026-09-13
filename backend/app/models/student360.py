# Student 360 — domain entities (requirement section 10-1).
# These models are additive: they do not touch the existing scheduler tables.
from sqlalchemy import (Column, Integer, String, Float, Boolean, DateTime, Date,
                        Text, JSON, ForeignKey, UniqueConstraint, Index)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


# ============================================================
# Program / Curriculum
# ============================================================
class Program(Base):
    """رشته، گرایش، مقطع و نسخه برنامه درسی"""
    __tablename__ = "stu_programs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)          # نام رشته
    level = Column(String(50), nullable=False)           # مقطع (کارشناسی و ...)
    orientation = Column(String(200))                    # گرایش
    department = Column(String(200))                     # گروه/دانشکده
    curriculum_version = Column(String(50), default="v1")  # نسخه برنامه درسی
    total_units = Column(Integer, default=140)           # کل واحدهای لازم
    min_gpa_graduation = Column(Float, default=12.0)     # حداقل معدل فارغ‌التحصیلی
    max_allowed_terms = Column(Integer, default=8)       # حداکثر نیمسال مجاز (سنوات)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    curriculum = relationship("Curriculum", back_populates="program")


class Curriculum(Base):
    """سرفصل و ساختار دروس مصوب"""
    __tablename__ = "stu_curriculum"

    id = Column(Integer, primary_key=True, index=True)
    program_id = Column(Integer, ForeignKey("stu_programs.id"), nullable=False)
    course_code = Column(String(50), nullable=False, index=True)
    course_title = Column(String(200), nullable=False)
    credits = Column(Integer, default=3)
    course_nature = Column(String(50), default="obligatory")
    # main-obligatory | optional-obligatory | general | elective | prerequisite-bridging
    suggested_term = Column(Integer)                      # ترم پیشنهادی در چارت
    is_chain_course = Column(Boolean, default=False)      # درس زنجیره‌ای (ضروری برای ادامه)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    program = relationship("Program", back_populates="curriculum")

    __table_args__ = (
        UniqueConstraint("program_id", "course_code", name="uq_curriculum_program_course"),
    )


# ============================================================
# Student / AcademicStatus
# ============================================================
class Student(Base):
    """شناسه دانشجو، اطلاعات هویتی، رشته، مقطع، ورودی"""
    __tablename__ = "stu_students"

    id = Column(Integer, primary_key=True, index=True)
    student_number = Column(String(50), unique=True, index=True, nullable=False)
    national_id = Column(String(20), index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    program_id = Column(Integer, ForeignKey("stu_programs.id"), nullable=False)
    entry_term = Column(String(20), nullable=False)       # ورودی (مثلاً 1402-1)
    entry_year = Column(String(10))
    status = Column(String(30), default="active")         # active | graduated | dismissed
    email = Column(String(200))
    phone = Column(String(20))
    is_pilot = Column(Boolean, default=False)             # عضو پایلوت
    sso_username = Column(String(100), index=True)        # نام کاربری SSO دانشگاه
    password_hash = Column(String(255))                   # هش رمز (برای OTP/local fallback)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_data_sync_at = Column(DateTime(timezone=True))   # STU-PRO-07

    program = relationship("Program")
    academic_statuses = relationship("AcademicStatus", back_populates="student")

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class AcademicStatus(Base):
    """وضعیت عادی، مشروط، مرخصی و سایر وضعیت‌ها"""
    __tablename__ = "stu_academic_statuses"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("stu_students.id"), nullable=False, index=True)
    term = Column(String(20), nullable=False)
    status = Column(String(50), nullable=False)
    # normal | probation | leave-of-absence | dismissal-threat | active-military | other
    detail = Column(String(500))
    probation_count = Column(Integer, default=0)          # تعداد مشروطی‌های قبلی
    effective_from = Column(Date)                         # تاریخ شروع اعتبار
    effective_to = Column(Date)                           # تاریخ پایان اعتبار
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    student = relationship("Student", back_populates="academic_statuses")


# ============================================================
# Term / Enrollment / Grade
# ============================================================
class Term(Base):
    """نیمسال، تاریخ شروع و پایان"""
    __tablename__ = "stu_terms"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False)   # مثل 1403-1
    title = Column(String(50), nullable=False)               # نیمسال اول ۱۴۰۳-۱۴۰۴
    start_date = Column(Date)
    end_date = Column(Date)
    is_current = Column(Boolean, default=False)
    is_open_for_registration = Column(Boolean, default=False)  # باز بودن انتخاب واحد
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Enrollment(Base):
    """ثبت‌نام دانشجو در درس"""
    __tablename__ = "stu_enrollments"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("stu_students.id"), nullable=False, index=True)
    term = Column(String(20), nullable=False, index=True)
    course_code = Column(String(50), nullable=False, index=True)
    course_title = Column(String(200))
    credits = Column(Integer, default=3)
    # day/start_time/end_time برای برنامه هفتگی (STU-PRO-05)
    class_day = Column(Integer)              # 0=شنبه ... 5=جمعه
    start_time = Column(String(10))
    end_time = Column(String(10))
    instructor_name = Column(String(100))
    status = Column(String(30), default="current")   # current | passed | failed | withdrawn
    registered_via = Column(String(30), default="official-system")  # منبع ثبت

    __table_args__ = (
        UniqueConstraint("student_id", "term", "course_code", name="uq_enrollment_student_term_course"),
    )


class Grade(Base):
    """نمره، وضعیت قبولی و تاریخ ثبت"""
    __tablename__ = "stu_grades"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("stu_students.id"), nullable=False, index=True)
    term = Column(String(20), nullable=False, index=True)
    course_code = Column(String(50), nullable=False, index=True)
    course_title = Column(String(200))
    credits = Column(Integer, default=3)
    grade = Column(Float)                                    # نمره 0..20
    status = Column(String(20), default="registered")        # passed | failed | in-progress | withdrawn
    graded_at = Column(DateTime(timezone=True))              # تاریخ ثبت نمره
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("student_id", "term", "course_code", name="uq_grade_student_term_course"),
    )


# ============================================================
# CourseRule — قواعد پیش‌نیاز/هم‌نیاز قابل مدیریت توسط کارشناس آموزش
# ============================================================
class CourseRule(Base):
    """پیش‌نیاز، هم‌نیاز، محدودیت و استثنا — با تاریخ اعتبار"""
    __tablename__ = "stu_course_rules"

    id = Column(Integer, primary_key=True, index=True)
    course_code = Column(String(50), nullable=False, index=True)     # درسِ مقصد
    rule_type = Column(String(30), nullable=False)
    # prerequisite | corequisite | probation-restriction | max-units | exception
    related_course_code = Column(String(50))                          # درسِ پیش‌نیاز/هم‌نیاز
    min_grade = Column(Float)                                         # حداقل نمره پیش‌نیاز
    restriction_detail = Column(String(500))                          # جزئیات محدودیت مشروطی و ...
    exception_note = Column(String(500))                              # توضیح مجوز/استثنا
    is_exception = Column(Boolean, default=False)                     # استثنای ثبت‌شده
    effective_from = Column(Date, nullable=False)                     # تاریخ شروع اعتبار (قاعده ۹-۷)
    effective_to = Column(Date)                                       # تاریخ پایان اعتبار
    created_by = Column(String(100))                                  # کارشناس آموزش
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============================================================
# Regulation — آیین‌نامه‌ها (دستیار آیین‌نامه‌ای)
# ============================================================
class Regulation(Base):
    """آیین‌نامه، ماده، تبصره، تاریخ اعتبار"""
    __tablename__ = "stu_regulations"

    id = Column(Integer, primary_key=True, index=True)
    doc_type = Column(String(50), nullable=False, index=True)
    # academic-regulations | course-selection | add-drop | probation | leave-of-absence
    # transfer-guest | graduation | academic-calendar | circular
    title = Column(String(300), nullable=False)
    article = Column(String(50))                # شماره ماده
    clause = Column(String(50))                 # شماره تبصره
    content = Column(Text, nullable=False)      # متن ماده/تبصره
    keywords = Column(String(500))              # کلمات کلیدی برای بازیابی
    source_name = Column(String(200), nullable=False)   # نام منبع تأییدشده
    valid_from = Column(Date, nullable=False)   # تاریخ اعتبار از
    valid_to = Column(Date)                     # تاریخ اعتبار تا (منقضی = پاسخ‌گو نیست)
    is_active = Column(Boolean, default=True)
    approved_by = Column(String(200))           # مرجع تصویب
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============================================================
# ProcessGuide — راهنمای فرایندهای اداری
# ============================================================
class ProcessGuide(Base):
    """راهنمای فرایند اداری آموزشی"""
    __tablename__ = "stu_process_guides"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    title = Column(String(300), nullable=False)
    category = Column(String(100), index=True)
    conditions = Column(Text)           # شرایط استفاده
    required_documents = Column(Text)   # مدارک موردنیاز (JSON لیست)
    steps = Column(Text)                # مراحل انجام (JSON لیست)
    responsible_unit = Column(String(200))    # واحد مسئول
    deadline = Column(String(200))            # مهلت ثبت درخواست
    system_url = Column(String(300))          # نشانی سامانه یا فرم
    processing_time = Column(String(100))     # زمان تقریبی رسیدگی
    related_rules = Column(Text)              # قوانین مرتبط
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============================================================
# CalendarEvent — تقویم و یادآوری
# ============================================================
class CalendarEvent(Base):
    """رویدادها و مهلت‌های آموزشی"""
    __tablename__ = "stu_calendar_events"

    id = Column(Integer, primary_key=True, index=True)
    term = Column(String(20), index=True)
    event_type = Column(String(50), nullable=False, index=True)
    # course-selection-start/end | add-drop | emergency-drop | exams | tuition-payment
    # guest-request | grade-appeal | supervisor-selection | thesis-defense
    title = Column(String(300), nullable=False)
    event_date = Column(Date, nullable=False, index=True)
    reminder_offset_days = Column(Integer, default=3)   # چند روز قبل یادآوری
    description = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class NotificationChannel(Base):
    """تنظیم کانال اطلاع‌رسانی دانشجو (بند ۸-۸)"""
    __tablename__ = "stu_notification_channels"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("stu_students.id"), nullable=False, unique=True)
    in_app = Column(Boolean, default=True)
    sms = Column(Boolean, default=True)
    email = Column(Boolean, default=True)
    mobile_push = Column(Boolean, default=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ============================================================
# Alert — هشدار زودهنگام پایه (بند ۸-۹)
# ============================================================
class Alert(Base):
    """نوع هشدار، شدت، دلیل و وضعیت رسیدگی"""
    __tablename__ = "stu_alerts"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("stu_students.id"), nullable=False, index=True)
    rule_code = Column(String(50), nullable=False)      # کد قاعده مولد هشدار (قابل ممیزی)
    alert_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False, default="info")   # info | warning | critical
    reason = Column(Text, nullable=False)               # دلیل هشدار (الزامات بند ۸-۹)
    recommended_action = Column(String(500))            # اقدام پیشنهادی
    status = Column(String(20), default="open")         # open | counseling-requested | resolved | dismissed
    visible_to_student = Column(Boolean, default=True)  # هشدارهای حساس فقط برای افراد مجاز
    term = Column(String(20))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True))


class CounselingRequest(Base):
    """درخواست مشاوره بعد از مشاهده هشدار"""
    __tablename__ = "stu_counseling_requests"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("stu_students.id"), nullable=False, index=True)
    alert_id = Column(Integer, ForeignKey("stu_alerts.id"))
    message = Column(Text)
    status = Column(String(20), default="pending")      # pending | in-progress | done
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============================================================
# Quiz — کوییز هوشمند (بند ۸-۱۰)
# ============================================================
class Quiz(Base):
    __tablename__ = "stu_quizzes"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("stu_students.id"), nullable=False, index=True)
    course_code = Column(String(50), nullable=False, index=True)
    title = Column(String(300))
    difficulty = Column(String(20), default="medium")   # easy | medium | hard
    status = Column(String(20), default="draft")        # draft | approved | active | closed
    approved_by = Column(String(100))                   # تأیید استاد
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    questions = relationship("QuizQuestion", back_populates="quiz", cascade="all, delete-orphan")


class QuizQuestion(Base):
    __tablename__ = "stu_quiz_questions"

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("stu_quizzes.id"), nullable=False, index=True)
    question_type = Column(String(20), default="multiple-choice")  # multiple-choice | short-answer
    question_text = Column(Text, nullable=False)
    options = Column(Text)              # JSON لیست گزینه‌ها برای چندگزینه‌ای
    correct_answer = Column(Text, nullable=False)
    explanation = Column(Text)          # پاسخ تشریحی
    source_ref = Column(String(300))    # ارجاع به منبع تأییدشده
    difficulty = Column(String(20), default="medium")
    topic = Column(String(100))         # مبحث (برای تحلیل نقاط ضعف)

    quiz = relationship("Quiz", back_populates="questions")


class QuizAttempt(Base):
    """ذخیره نتیجه آزمون"""
    __tablename__ = "stu_quiz_attempts"

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("stu_quizzes.id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("stu_students.id"), nullable=False, index=True)
    answers = Column(Text)              # JSON پاسخ‌های دانشجو
    score = Column(Float)
    max_score = Column(Float)
    weak_topics = Column(Text)          # JSON نقاط ضعف شناسایی‌شده
    study_recommendations = Column(Text)  # JSON پیشنهاد مطالعه مجدد
    taken_at = Column(DateTime(timezone=True), server_default=func.now())


# ============================================================
# LearningContent — منابع مورد تأیید درس (استاد هوشمند)
# ============================================================
class LearningContent(Base):
    __tablename__ = "stu_learning_contents"

    id = Column(Integer, primary_key=True, index=True)
    course_code = Column(String(50), nullable=False, index=True)
    title = Column(String(300), nullable=False)
    content_type = Column(String(50), default="text")   # text | file | slide | link
    content = Column(Text)                              # متن یا مسیر فایل
    section_ref = Column(String(200))                   # فصل/بخش برای ارجاع پاسخ
    is_verified = Column(Boolean, default=True)         # فقط منابع تأییدشده
    uploaded_by = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============================================================
# Conversation — سابقه تعامل با دستیارهای هوشمند
# ============================================================
class Conversation(Base):
    __tablename__ = "stu_conversations"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("stu_students.id"), nullable=False, index=True)
    assistant_type = Column(String(50), nullable=False, index=True)
    # regulations | smart-professor
    course_code = Column(String(50))                    # برای استاد هوشمند
    question = Column(Text, nullable=False)             # STU-REG-07
    answer = Column(Text)
    source_refs = Column(Text)                          # JSON: نام منبع، ماده، تبصره، تاریخ اعتبار
    confidence = Column(Float, default=1.0)             # STU-REG-04
    is_low_confidence = Column(Boolean, default=False)
    feedback = Column(String(20))                       # helpful | not-helpful (STU-REG-06)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============================================================
# AuditLog — بند STU-AUTH-04 و قاعده ۹-۱۰
# ============================================================
class AuditLog(Base):
    __tablename__ = "stu_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    student_number = Column(String(50), index=True)     # کاربر (یا system)
    role = Column(String(30))
    action = Column(String(100), nullable=False, index=True)   # login | view | change | ...
    entity = Column(String(100))                        # موجودیتِ موردِ عمل
    entity_id = Column(String(50))
    detail = Column(Text)                               # توضیح و دلیل (قابل توضیح و ممیزی)
    ip_address = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


# ============================================================
# DataDiscrepancyReport — اعلام مغایرت (STU-PRO-08)
# ============================================================
class DataDiscrepancyReport(Base):
    __tablename__ = "stu_discrepancy_reports"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("stu_students.id"), nullable=False, index=True)
    field = Column(String(100), nullable=False)         # فیلدِ دارای مغایرت
    current_value = Column(String(500))                 # مقدار موجود در سامانه
    claimed_value = Column(String(500))                 # مقدار اعلامی دانشجو
    description = Column(Text)
    status = Column(String(20), default="pending")      # pending | reviewing | resolved | rejected
    resolution_note = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True))


# ============================================================
# CourseScenario — سناریوهای انتخاب واحد (STU-CRS-10)
# ============================================================
class CourseScenario(Base):
    __tablename__ = "stu_course_scenarios"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("stu_students.id"), nullable=False, index=True)
    term = Column(String(20), nullable=False)
    name = Column(String(200), nullable=False)
    selected_course_codes = Column(Text)   # JSON لیست کد دروس انتخاب‌شده
    total_units = Column(Integer, default=0)
    validations = Column(Text)             # JSON نتیجه کنترل‌های STU-CRS-02..07
    is_final = Column(Boolean, default=False)
    # ثبت نهایی فقط پس از تأیید دانشجو در سامانه رسمی آموزش (STU-CRS-11)
    confirmed_officially = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============================================================
# Advisor / Expert — کنترل دسترسی نقش‌محور (STU-AUTH-05)
# ============================================================
class StaffUser(Base):
    """مشاور/کارشناس آموزش با نقش و محدوده سازمانی"""
    __tablename__ = "stu_staff_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    full_name = Column(String(200), nullable=False)
    role = Column(String(30), nullable=False)    # education-expert | advisor | admin
    org_scope = Column(String(200))              # محدوده سازمانی (گروه/دانشکده)
    can_view_sensitive_alerts = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============================================================
# UnifiedUser — برای ورود یکپارچه (دانشجو/کارمند)
# ============================================================
class UnifiedUser(Base):
    __tablename__ = "stu_unified_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(200))
    role = Column(String(30), nullable=False, default="student")  # student | education-expert | advisor | admin
    ref_id = Column(Integer)             # شناسه در جدول Student یا StaffUser
    password_hash = Column(String(255))
    sso_subject = Column(String(150), index=True)   # شناسه SSO در صورت وجود
    created_at = Column(DateTime(timezone=True), server_default=func.now())
