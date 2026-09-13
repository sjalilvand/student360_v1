# app/core/event_middleware.py
# Auto event tracking for API traffic. Never breaks requests.
# v2: reads Bearer token AND X-Student-Number/X-User headers; throttles noisy GETs.
from __future__ import annotations

import time
from threading import Lock

from starlette.middleware.base import BaseHTTPMiddleware

from app.core.database import SessionLocal
from app.services import event_tracking_service as ets

SKIP_PREFIXES = ("/api/events", "/health", "/openapi.json", "/docs", "/redoc")
GET_THROTTLE_SECONDS = 30.0

_seen: dict = {}
_lock = Lock()


def _student_ref(request):
    auth = request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        try:
            from app.services.student360_auth import parse_session_token

            data = parse_session_token(auth.split(" ", 1)[1].strip())
            for attr in ("student_number", "student_ref", "sub", "username"):
                val = data.get(attr) if isinstance(data, dict) else getattr(data, attr, None)
                if val:
                    return str(val)
        except Exception:
            pass
    for h in ("x-student-number", "x-user"):
        v = request.headers.get(h)
        if v:
            return str(v)
    return None


def _throttled(method: str, path: str) -> bool:
    if method != "GET":
        return False
    now = time.time()
    with _lock:
        if len(_seen) > 1000:
            cutoff = now - GET_THROTTLE_SECONDS
            for k in [k for k, t in _seen.items() if t < cutoff]:
                _seen.pop(k, None)
        last = _seen.get(path, 0)
        if now - last < GET_THROTTLE_SECONDS:
            return True
        _seen[path] = now
    return False


class EventTrackingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path
        method = request.method
        tracked = method in ("GET", "POST", "PUT", "DELETE", "PATCH")
        skipped = any(path.startswith(p) for p in SKIP_PREFIXES)
        if tracked and not skipped:
            t0 = time.time()
            response = await call_next(request)
            if not _throttled(method, path):
                try:
                    db = SessionLocal()
                    try:
                        ets.track_event(
                            db,
                            event_type="http_request",
                            event_name=f"{method} {path}",
                            student_ref=_student_ref(request),
                            source="api",
                            payload={"status": response.status_code, "ms": int((time.time() - t0) * 1000)},
                        )
                    finally:
                        db.close()
                except Exception:
                    pass
            return response
        return await call_next(request)
