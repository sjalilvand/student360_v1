# app/services/prof_auth_utils.py
# Werkzeug-compatible password hashing (no Flask dependency) + HMAC tokens.
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time

SECRET = (os.getenv("PROF_JWT_SECRET") or "student360-prof-secret-fallback").encode()
TOKEN_TTL = 7 * 24 * 3600


# ---------- werkzeug-compatible password hashing ----------
def generate_password_hash(password: str) -> str:
    salt = secrets.token_hex(16)
    iters = 600000
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iters)
    return f"pbkdf2:sha256:{iters}${salt}${h.hex()}"


def check_password_hash(stored: str, password: str) -> bool:
    if not stored:
        return False
    try:
        method, salt, hexhash = stored.split("$", 2)
        parts = method.split(":")
        algo = parts[0]
        if algo == "pbkdf2":
            iters = int(parts[2]) if len(parts) > 2 else 260000
            h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iters)
            return hmac.compare_digest(h.hex(), hexhash)
        if algo == "scrypt":
            # scrypt:N:r:p$salt$hash
            n, r, pp = int(parts[1]), int(parts[2]), int(parts[3])
            salt2, hexhash = salt, hexhash
            h = hashlib.scrypt(password.encode(), salt=salt2.encode(), n=n, r=r, p=pp)
            return hmac.compare_digest(h.hex(), hexhash)
    except Exception:
        return False
    return False


# ---------- HMAC token (opaque string for FE) ----------
def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def create_token(prof_id: int, role: str = "professor", ttl: int = TOKEN_TTL) -> str:
    payload = {"prof_id": prof_id, "role": role, "exp": int(time.time()) + ttl}
    body = _b64(json.dumps(payload).encode())
    sig = _b64(hmac.new(SECRET, body.encode(), hashlib.sha256).digest())
    return f"{body}.{sig}"


def parse_token(token: str) -> dict | None:
    try:
        body, sig = token.split(".", 1)
        expected = hmac.new(SECRET, body.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(_unb64(sig), expected):
            return None
        payload = json.loads(_unb64(body))
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


def current_professor_id(request) -> int | None:
    auth = (request.headers.get("authorization") or "")
    if not auth.lower().startswith("bearer "):
        return None
    payload = parse_token(auth.split(" ", 1)[1].strip())
    if not payload or payload.get("role") != "professor":
        return None
    return payload.get("prof_id")
