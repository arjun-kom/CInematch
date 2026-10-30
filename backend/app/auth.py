"""Simple login: hashed passwords + random session tokens stored in MongoDB.

Sessions live in the `sessions` collection. A TTL index on `expires_at` makes MongoDB
delete expired sessions by itself, so nobody has to write a clean-up job.
"""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Header

from . import config
from .db import get_db
from .errors import ApiError

ITERATIONS = 120_000


def hash_password(password: str, salt: str | None = None) -> dict:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), ITERATIONS).hex()
    return {"salt": salt, "hash": digest}


def check_password(password: str, stored: dict) -> bool:
    return hmac.compare_digest(hash_password(password, stored["salt"])["hash"], stored["hash"])


def create_session(user_id) -> str:
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    get_db().sessions.insert_one({"_id": token, "user_id": user_id, "created_at": now,
                                  "expires_at": now + timedelta(days=config.SESSION_DAYS)})
    return token


def current_user(authorization: str | None = Header(default=None)) -> dict:
    """FastAPI dependency: returns the logged-in user or raises 401."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise ApiError(401, "not_logged_in", "Please log in.")
    token = authorization.split(" ", 1)[1].strip()
    db = get_db()
    session = db.sessions.find_one({"_id": token, "expires_at": {"$gt": datetime.now(timezone.utc)}})
    if not session:
        raise ApiError(401, "session_expired", "Your session has expired. Please log in again.")
    user = db.users.find_one({"_id": session["user_id"]}, {"password": 0})
    if not user:
        raise ApiError(401, "not_logged_in", "Please log in.")
    user["_token"] = token
    return user


def public_user(user: dict) -> dict:
    return {
        "id": str(user["_id"]),
        "username": user["username"],
        "display_name": user.get("display_name") or user["username"],
        "favourite_genres": user.get("favourite_genres", []),
        "onboarded": user.get("onboarded", False),
        "list_count": len(user.get("my_list", [])),
    }
