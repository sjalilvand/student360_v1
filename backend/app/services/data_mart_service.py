# app/services/data_mart_service.py
# Lightweight Data Mart (Phase 1 / Data Fast Track). v2: exact schema-based SQL.
from sqlalchemy import inspect as sa_inspect, text
from sqlalchemy.engine import Engine

ALLOWED_VIEWS = ("v_event_daily", "v_event_totals", "v_student_gpa", "v_course_demand", "v_term_enrollment")


def _columns(engine: Engine, table: str):
    try:
        return [c["name"] for c in sa_inspect(engine).get_columns(table)]
    except Exception:
        return []


def _has_all(cols: list, needed: tuple) -> bool:
    return all(c in cols for c in needed)


def refresh_marts(engine: Engine):
    created, skipped = [], []
    with engine.begin() as conn:
        # 1) events per day/type
        conn.execute(text("DROP VIEW IF EXISTS v_event_daily"))
        conn.execute(text(
            "CREATE VIEW v_event_daily AS "
            "SELECT date(occurred_at) AS day, event_type, COUNT(*) AS events "
            "FROM stu_event_logs GROUP BY day, event_type"
        ))
        created.append("v_event_daily")

        # 2) event totals per type
        conn.execute(text("DROP VIEW IF EXISTS v_event_totals"))
        conn.execute(text(
            "CREATE VIEW v_event_totals AS "
            "SELECT event_type, COUNT(*) AS events, COUNT(DISTINCT student_ref) AS students "
            "FROM stu_event_logs GROUP BY event_type"
        ))
        created.append("v_event_totals")

        # 3) student GPA (weighted by credits) - exact columns: stu_grades(grade,credits,student_id), stu_students(student_number,first_name,last_name)
        gcols = _columns(engine, "stu_grades")
        scols = _columns(engine, "stu_students")
        if _has_all(gcols, ("student_id", "grade", "credits")) and _has_all(scols, ("student_number", "first_name", "last_name")):
            conn.execute(text("DROP VIEW IF EXISTS v_student_gpa"))
            conn.execute(text(
                "CREATE VIEW v_student_gpa AS "
                "SELECT s.id AS student_id, s.student_number AS student_number, "
                "TRIM(s.first_name || ' ' || s.last_name) AS full_name, "
                "COUNT(*) AS graded_courses, SUM(g.credits) AS total_credits, "
                "ROUND(AVG(g.grade), 2) AS avg_score, "
                "ROUND(SUM(g.grade * g.credits) * 1.0 / NULLIF(SUM(g.credits), 0), 2) AS weighted_gpa "
                "FROM stu_grades g JOIN stu_students s ON s.id = g.student_id "
                "WHERE g.grade IS NOT NULL GROUP BY s.id"
            ))
            created.append("v_student_gpa")
        else:
            skipped.append("v_student_gpa (schema mismatch)")

        # 4) course demand: offered_courses(unique_code,enrollment_count,demand_prediction) JOIN unique_courses(code,historical_demand,estimated_capacity,avg_rating)
        ocols = _columns(engine, "offered_courses")
        ucols = _columns(engine, "unique_courses")
        if _has_all(ocols, ("unique_code", "enrollment_count", "demand_prediction")) and _has_all(ucols, ("code", "historical_demand", "estimated_capacity")):
            conn.execute(text("DROP VIEW IF EXISTS v_course_demand"))
            conn.execute(text(
                "CREATE VIEW v_course_demand AS "
                "SELECT o.unique_code AS course_code, o.unique_title AS title, "
                "o.enrollment_count AS enrollment_count, o.demand_prediction AS demand_prediction, "
                "u.historical_demand AS historical_demand, "
                "u.estimated_capacity AS estimated_capacity, u.avg_rating AS avg_rating "
                "FROM offered_courses o LEFT JOIN unique_courses u ON u.code = o.unique_code"
            ))
            created.append("v_course_demand")
        else:
            skipped.append("v_course_demand (schema mismatch)")

        # 5) term enrollment trend
        ecols = _columns(engine, "stu_enrollments")
        if _has_all(ecols, ("term", "student_id")):
            conn.execute(text("DROP VIEW IF EXISTS v_term_enrollment"))
            conn.execute(text(
                "CREATE VIEW v_term_enrollment AS "
                "SELECT term, COUNT(*) AS enrollments, COUNT(DISTINCT student_id) AS students "
                "FROM stu_enrollments GROUP BY term"
            ))
            created.append("v_term_enrollment")
        else:
            skipped.append("v_term_enrollment (schema mismatch)")

    return {"created": created, "skipped": skipped}


def status(engine: Engine):
    views = [v for v in sa_inspect(engine).get_view_names() if v.startswith("v_")]
    out = []
    with engine.connect() as conn:
        for v in views:
            try:
                n = conn.execute(text(f"SELECT COUNT(*) FROM {v}")).scalar()
                out.append({"view": v, "rows": int(n)})
            except Exception:
                out.append({"view": v, "rows": None})
    return out


def sample(engine: Engine, view: str, limit: int = 20):
    if view not in ALLOWED_VIEWS:
        raise ValueError("unknown view")
    with engine.connect() as conn:
        rows = conn.execute(text(f"SELECT * FROM {view} LIMIT :l"), {"l": max(1, min(int(limit), 200))}).mappings().all()
        return [dict(r) for r in rows]
