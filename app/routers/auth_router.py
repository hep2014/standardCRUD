import os
from fastapi import APIRouter, Depends, HTTPException, Body, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.cache.redis_cache import cache_delete, cache_get, cache_set
from fastapi_sso.sso.github import GithubSSO
from app.db.db import redis_client
import json
import time
from app.db.db import get_db
from app.models.user import User
from contextlib import contextmanager
from app.auth.passwords import hash_password, verify_password
from app.auth.jwt import jwt_encode, make_access_payload
from app.auth.deps import get_current_user

from argon2 import PasswordHasher
ph = PasswordHasher()

router = APIRouter(prefix="/api/auth", tags=["Auth"])

ph = PasswordHasher()

def _issue_tokens(u: User, user_agent: str | None, db: Session) -> dict:
    payload = make_access_payload(u.id, u.is_admin, u.is_verified_author)
    access_token = jwt_encode(payload, os.getenv("JWT_SECRET", "dev"))

    raw_refresh = os.urandom(32).hex()
    refresh_key = f"session:{u.id}:{raw_refresh}"

    expires_in_days = 30
    expires_at = int(time.time()) + expires_in_days * 86400

    data = {
        "user_id": u.id,
        "user_agent": user_agent or "",
        "created_at": int(time.time()),
        "expires_at": expires_at,
    }
    redis_client.set(refresh_key, json.dumps(data), ex=expires_in_days * 86400)
    return {
        "access_token": access_token,
        "refresh_token": raw_refresh,
        "token_type": "bearer",
        "expires_in": int(os.getenv("JWT_EXPIRES_MIN", "15")) * 60,
    }

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
GITHUB_REDIRECT_URL = os.getenv("GITHUB_REDIRECT_URL")

@contextmanager
def db_context():
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()
github_sso = GithubSSO(
    client_id=GITHUB_CLIENT_ID,
    client_secret=GITHUB_CLIENT_SECRET,
    redirect_uri=GITHUB_REDIRECT_URL,
    allow_insecure_http=True,
    scope=["user:email"],
)

@router.post("/register")
def register(
    request: Request,
    name: str = Body(...),
    email: str = Body(...),
    password: str = Body(..., min_length=6),
    db: Session = Depends(get_db),
):
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(400, "Email already exists")
    u = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        is_verified_author=False,
        is_admin=False,
    )
    db.add(u); db.commit(); db.refresh(u)
    ua = request.headers.get("User-Agent") if "request" in locals() else None
    return _issue_tokens(u, ua, db)

@router.post("/login")
def login(
    request: Request,
    email: str = Body(...),
    password: str = Body(...),
    db: Session = Depends(get_db),
):
    u = db.query(User).filter(User.email == email).first()
    if not u or not u.password_hash or not verify_password(password, u.password_hash):
        raise HTTPException(401, "Invalid credentials")
    ua = request.headers.get("User-Agent") if "request" in locals() else None
    return _issue_tokens(u, ua, db)

@router.post("/refresh")
def refresh_token(refresh_token: str = Body(...)):
    keys = redis_client.keys(f"session:*:{refresh_token}")
    if not keys:
        raise HTTPException(401, "Invalid refresh token")

    key = keys[0]
    data = json.loads(redis_client.get(key))
    if int(time.time()) > data["expires_at"]:
        redis_client.delete(key)
        raise HTTPException(401, "Session expired")

    user_id = data["user_id"]
    # получаем пользователя (из кэша или БД)
    u_data = cache_get(f"user:{user_id}")
    if not u_data:
        with db_context() as db:
            u = db.get(User, user_id)
        u_data = {"id": u.id, "is_admin": u.is_admin, "is_verified_author": u.is_verified_author}
        cache_set(f"user:{user_id}", u_data, 600)

    payload = make_access_payload(u_data["id"], u_data["is_admin"], u_data["is_verified_author"])
    access_token = jwt_encode(payload, os.getenv("JWT_SECRET", "dev"))
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/logout")
def logout(refresh_token: str = Body(...)):
    keys = redis_client.keys(f"session:*:{refresh_token}")
    for key in keys:
        redis_client.delete(key)
    return {"status": "ok"}

@router.get("/github/login")
async def github_login():
    return await github_sso.get_login_redirect()

@router.get("/github/callback")
async def github_callback(request: Request, db: Session = Depends(get_db)):
    user_info = await github_sso.verify_and_process(request)
    email = user_info.email or f"{user_info.user_id}@users.noreply.github.com"
    name = user_info.display_name or user_info.user_id

    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            name=name,
            email=email,
            is_verified_author=False,
            is_admin=False,
            avatar_url=None
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # Выдаём наши access/refresh токены
    ua = request.headers.get("User-Agent")
    return _issue_tokens(user, ua, db)

@router.get("/sessions")
def my_sessions(user: User = Depends(get_current_user)):
    pattern = f"session:{user.id}:*"
    keys = redis_client.keys(pattern)
    sessions = []

    for key in keys:
        raw = redis_client.get(key)
        if not raw:
            continue
        try:
            data = json.loads(raw)
            sessions.append({
                "key": key,
                "user_agent": data.get("user_agent"),
                "created_at": data.get("created_at"),
                "expires_at": data.get("expires_at"),
            })
        except json.JSONDecodeError:
            continue

    return sessions
