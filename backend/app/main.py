# app/main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import traceback
from sqlalchemy import inspect, text
from app.core.database import engine  # فرض بر این است که engine در این مسیر تعریف شده است

from app.api.routes_schedule import router as schedule_router
from app.api.routes_courses import router as courses_router
from app.api.routes_charts import router as charts_router
from app.api.routes_professors_rooms import router as professors_rooms_router
from app.core.db_init import init_db
from app.api.routes_schedule_history import router as schedule_history_router
from app.api.routes_term_courses import router as term_courses_router
from app.api.routes_teaching_preferences import router as teaching_preferences_router
from app.api.routes_time_preferences import router as time_preferences_router
from app.api.routes_workflow import router as workflow_router
from app.api.routes_baskets import router as baskets_router
from app.api.routes_room_allocation import router as room_allocation_router
from app.api.routes_optimization import router as optimization_router
from app.services.schedule.slot_times import router as slot_times_router
from app.api import test_report
from app.api.routes_student360 import router as student360_router
from app.data.seed_student360 import seed_student360
from app.core.database import SessionLocal

# تنظیم لاگر
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ===== تابع برای اضافه کردن ستون‌های گم‌شده به دیتابیس =====
def ensure_missing_columns():
    """
    بررسی و اضافه کردن ستون‌های مورد نیاز به جداول موجود (برای SQLite)
    """
    required_columns = {
        "unique_courses": ["historical_demand", "avg_rating"],
        "offered_courses": ["preferred_instructors", "preferred_time_slots", "enrollment_count", "demand_prediction"],
    }

    with engine.connect() as conn:
        for table, columns in required_columns.items():
            # دریافت لیست ستون‌های موجود
            inspector = inspect(engine)
            existing_columns = [col['name'] for col in inspector.get_columns(table)]

            for col in columns:
                if col not in existing_columns:
                    # اضافه کردن ستون به جدول
                    try:
                        # نوع داده‌ها بر اساس نیاز: برای TEXT و FLOAT
                        if col in ["historical_demand", "avg_rating", "enrollment_count", "demand_prediction"]:
                            col_type = "FLOAT"
                        else:
                            col_type = "TEXT"

                        alter_sql = f"ALTER TABLE {table} ADD COLUMN {col} {col_type};"
                        conn.execute(text(alter_sql))
                        conn.commit()
                        logger.info(f"✅ ستون '{col}' به جدول '{table}' اضافه شد.")
                    except Exception as e:
                        logger.error(f"❌ خطا در اضافه کردن ستون '{col}' به جدول '{table}': {e}")
                else:
                    logger.info(f"ℹ️ ستون '{col}' در جدول '{table}' وجود دارد.")


# ===== استفاده از lifespan =====
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 راه‌اندازی سامانه هوشمند برنامه‌ریزی درسی...")
    try:
        # مقداردهی اولیه دیتابیس (ایجاد جداول در صورت عدم وجود)
        init_db()
        logger.info("✅ دیتابیس با موفقیت مقداردهی شد.")

        # اضافه کردن ستون‌های گم‌شده (برای رفع خطای no such column)
        ensure_missing_columns()
        logger.info("✅ ساختار دیتابیس به‌روزرسانی شد.")

        # ===== Student 360: داده اولیه پایلوت =====
        try:
            db = SessionLocal()
            seed_student360(db)
            db.close()
            logger.info("✅ داده‌های اولیه دانشجو ۳۶۰ آماده شد.")
        except Exception as e:
            logger.warning(f"⚠️ seed دانشجو ۳۶۰: {e}")

    except Exception as e:
        logger.error(f"❌ خطا در مقداردهی دیتابیس: {e}")
        logger.error(traceback.format_exc())
    yield
    logger.info("🛑 سامانه در حال خاموش‌شدن...")


app = FastAPI(
    title="Intelligent University Scheduler",
    version="2.0.0",
    description="سامانه هوشمند برنامه‌ریزی درسی دانشگاهی با قابلیت گام‌به‌گام و مدیریت فرایند",
    lifespan=lifespan
)

# ===== CORS - تنظیمات کامل =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# ===== ثبت روترها =====
app.include_router(courses_router, tags=["Courses"])
app.include_router(charts_router, tags=["Charts"])
app.include_router(professors_rooms_router, tags=["Professors & Rooms"])
app.include_router(term_courses_router, tags=["Term Courses"])
app.include_router(schedule_history_router, tags=["Schedule History"])
app.include_router(teaching_preferences_router, tags=["Teaching Preferences"])
app.include_router(time_preferences_router, tags=["Time Preferences"])
app.include_router(schedule_router, tags=["Schedule"])
app.include_router(workflow_router, tags=["Workflow"])
app.include_router(baskets_router, prefix="/api", tags=["Baskets"])
app.include_router(optimization_router, prefix="/api")
app.include_router(room_allocation_router)
app.include_router(test_report.router)
app.include_router(student360_router)
app.include_router(slot_times_router)


# ===== اندپوینت ریشه =====
@app.get("/")
def root():
    return {
        "service": "Intelligent University Scheduler",
        "version": app.version,
        "status": "running",
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
        }
    }


# ===== اندپوینت سلامت =====
@app.get("/health")
def health_check():
    return {"status": "healthy"}


# ===== مدیریت خطاهای عمومی =====
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"❌ خطای سرور: {exc}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={
            "detail": "خطای داخلی سرور رخ داده است.",
            "error": str(exc)
        }
    )
# ===== Event Tracking (Phase 1 / Data Fast Track) =====
try:
    from app.api.routes_events import router as events_router  # noqa: E402
    app.include_router(events_router, tags=["Event Tracking"])
except Exception as _evt_err:  # pragma: no cover
    print(f"WARNING: Event Tracking router load failed: {_evt_err}")

# ===== Step 2/3: Event middleware + AI layer (auto-added) =====
try:
    from app.core.event_middleware import EventTrackingMiddleware
    app.add_middleware(EventTrackingMiddleware)
except Exception as _evm_err:
    print(f"WARNING: EventTrackingMiddleware failed: {_evm_err}")

try:
    from app.api.routes_ai import router as ai_router
    app.include_router(ai_router, tags=["AI (RAG+LLM)"])
except Exception as _ai_err:
    print(f"WARNING: AI router failed: {_ai_err}")

# ===== Step 4: Audit endpoint + Data Marts (auto-added) =====
try:
    from app.api.routes_audit import router as audit_router
    app.include_router(audit_router, tags=["Audit"])
except Exception as _aud_err:
    print(f"WARNING: audit router failed: {_aud_err}")

try:
    from app.api.routes_marts import router as marts_router
    app.include_router(marts_router, tags=["Data Marts"])
except Exception as _mrt_err:
    print(f"WARNING: marts router failed: {_mrt_err}")

# ===== Step 5: Jalali calendar + GPA-mart bridge (auto-added) =====
try:
    from app.api.routes_jalali import router as jalali_router
    app.include_router(jalali_router, tags=["Jalali Calendar"])
except Exception as _jal_err:
    print(f"WARNING: jalali router failed: {_jal_err}")

try:
    from app.api.routes_profile_mart import router as profile_mart_router
    app.include_router(profile_mart_router, tags=["Profile (GPA Mart)"])
except Exception as _pgm_err:
    print(f"WARNING: profile mart router failed: {_pgm_err}")

# ===== Step 6: Demand prediction runner (auto-added) =====
try:
    from app.api.routes_demand import router as demand_router
    app.include_router(demand_router, tags=["Demand Prediction"])
except Exception as _dem_err:
    print(f"WARNING: demand router failed: {_dem_err}")

# ===== Step 7: Staff workspace (auto-added) =====
try:
    from app.api.routes_staff import router as staff_router
    app.include_router(staff_router, tags=["Staff Workspace"])
except Exception as _stf_err:
    print(f"WARNING: staff router failed: {_stf_err}")

# ===== Step 8: AI upgrade for legacy services (auto-added) =====
try:
    from app.core.ai_integration import install_ai_integration
    install_ai_integration()
except Exception as _aii_err:
    print(f"WARNING: AI integration failed: {_aii_err}")

# ===== Phase 2 Step 1: Behavioral Insights (auto-added) =====
try:
    from app.api.routes_behavior import router as behavior_router
    app.include_router(behavior_router, tags=["Behavioral Insights"])
except Exception as _beh_err:
    print(f"WARNING: behavior router failed: {_beh_err}")

# ===== Phase 2 Step 2: Academic Risk Prediction (auto-added) =====
try:
    from app.api.routes_risk import router as risk_router
    app.include_router(risk_router, tags=["Risk Prediction"])
except Exception as _rsk_err:
    print(f"WARNING: risk router failed: {_rsk_err}")

# ===== Phase 2 Step 3: Smart Interventions (auto-added) =====
try:
    from app.api.routes_intervention import router as intervention_router
    app.include_router(intervention_router, tags=["Interventions"])
except Exception as _itv_err:
    print(f"WARNING: intervention router failed: {_itv_err}")

# ===== Phase 2 Step 4: Personalized Study Path (auto-added) =====
try:
    from app.api.routes_studypath import router as studypath_router
    app.include_router(studypath_router, tags=["Study Path"])
except Exception as _spp_err:
    print(f"WARNING: studypath router failed: {_spp_err}")

# ===== Phase 2 Step 5: Adaptive Quiz (auto-added) =====
try:
    from app.api.routes_adaptive_quiz import router as adaptive_quiz_router
    app.include_router(adaptive_quiz_router, tags=["Adaptive Quiz"])
except Exception as _aq_err:
    print(f"WARNING: adaptive quiz router failed: {_aq_err}")

# ===== Phase 2 Step 6: Career & Skills (auto-added) =====
try:
    from app.api.routes_career import router as career_router
    app.include_router(career_router, tags=["Career & Skills"])
except Exception as _car_err:
    print(f"WARNING: career router failed: {_car_err}")

# ===== Phase 2 Step 7: Feedback NLP (auto-added) =====
try:
    from app.api.routes_feedback_nlp import router as feedback_nlp_router
    app.include_router(feedback_nlp_router, tags=["Feedback Quality"])
except Exception as _fbn_err:
    print(f"WARNING: feedback nlp router failed: {_fbn_err}")

# ===== Phase 3 Step 1: Digital Twin what-if (auto-added) =====
try:
    from app.api.routes_twin import router as twin_router
    app.include_router(twin_router, tags=["Digital Twin"])
except Exception as _tw_err:
    print(f"WARNING: twin router failed: {_tw_err}")
