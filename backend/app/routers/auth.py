from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pymongo.errors import DuplicateKeyError, PyMongoError

from .. import config
from ..auth import check_password, create_session, current_user, hash_password, public_user
from ..db import get_db
from ..errors import ApiError
from ..schemas import Credentials, Login

router = APIRouter(tags=["account"])


@router.get("/meta")
def meta():
    return {"app_name": config.APP_NAME, "tagline": config.APP_TAGLINE}


@router.get("/health")
def health():
    try:
        get_db().command("ping")
        return {"status": "ok", "database": "up"}
    except PyMongoError:
        return JSONResponse(status_code=503, content={"status": "degraded", "database": "down"})


@router.post("/auth/register", status_code=201)
def register(body: Credentials):
    user = {"username": body.username.lower(), "display_name": body.display_name or body.username,
            "password": hash_password(body.password), "favourite_genres": [], "my_list": [],
            "onboarded": False, "created_at": datetime.now(timezone.utc)}
    try:
        user["_id"] = get_db().users.insert_one(user).inserted_id   # unique index on username
    except DuplicateKeyError:
        raise ApiError(409, "username_taken", f"The username '{body.username}' is already taken.")
    return {"token": create_session(user["_id"]), "user": public_user(user)}


@router.post("/auth/login")
def login(body: Login):
    user = get_db().users.find_one({"username": body.username.strip().lower()})
    if not user or not check_password(body.password, user["password"]):
        raise ApiError(401, "bad_login", "Wrong username or password.")
    return {"token": create_session(user["_id"]), "user": public_user(user)}


@router.post("/auth/logout")
def logout(user: dict = Depends(current_user)):
    get_db().sessions.delete_one({"_id": user["_token"]})
    return {"ok": True}


@router.get("/auth/me")
def me(user: dict = Depends(current_user)):
    return public_user(user)
