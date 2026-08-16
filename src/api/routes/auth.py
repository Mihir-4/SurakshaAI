"""Authentication routes — register, login, me."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, field_validator

router = APIRouter(prefix="/auth", tags=["auth"])

# ── JWT Config ────────────────────────────────────────────────────────────────
SECRET_KEY = "surakshaai-secret-jwt-key-change-in-production"
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 72


# ── Schemas ───────────────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: str
    password: str
    confirm_password: str

    @field_validator("email")
    @classmethod
    def email_lower(cls, v: str) -> str:
        return v.strip().lower()


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def email_lower(cls, v: str) -> str:
        return v.strip().lower()


# ── Helpers ───────────────────────────────────────────────────────────────────
def _hash_password(password: str) -> str:
    try:
        import bcrypt
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    except ImportError:
        import hashlib, os
        salt = os.urandom(16).hex()
        return salt + ":" + hashlib.sha256((salt + password).encode()).hexdigest()


def _verify_password(password: str, hashed: str) -> bool:
    try:
        import bcrypt
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ImportError:
        import hashlib
        parts = hashed.split(":")
        if len(parts) != 2:
            return False
        salt, digest = parts
        return hashlib.sha256((salt + password).encode()).hexdigest() == digest


def _create_token(user_id: str, email: str) -> str:
    try:
        from jose import jwt
        payload = {
            "sub": user_id,
            "email": email,
            "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS),
        }
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    except ImportError:
        import base64, json
        payload = {"sub": user_id, "email": email}
        return base64.b64encode(json.dumps(payload).encode()).decode()


def _decode_token(token: str) -> dict:
    try:
        from jose import jwt, JWTError
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        try:
            import base64, json
            return json.loads(base64.b64decode(token.encode()).decode())
        except Exception:
            return {}


# ── Routes ────────────────────────────────────────────────────────────────────
@router.post("/register")
def register(payload: RegisterRequest) -> dict:
    if payload.password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")

    from src.db.connection import check_db, db_session

    if check_db():
        try:
            from src.db.models import User
            with db_session() as db:
                existing = db.query(User).filter(User.email == payload.email).first()
                if existing:
                    raise HTTPException(status_code=409, detail="An account with this email already exists.")
                user = User(
                    id=uuid.uuid4(),
                    email=payload.email,
                    hashed_password=_hash_password(payload.password),
                )
                db.add(user)
            return {"message": "Account created successfully.", "email": payload.email}
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Registration failed: {str(exc)}")

    raise HTTPException(status_code=503, detail="Database unavailable.")


@router.post("/login")
def login(payload: LoginRequest) -> dict:
    from src.db.connection import check_db, db_session

    if check_db():
        try:
            from src.db.models import User
            with db_session() as db:
                user = db.query(User).filter(User.email == payload.email).first()
                if not user or not _verify_password(payload.password, user.hashed_password):
                    raise HTTPException(status_code=401, detail="Incorrect email or password.")
                token = _create_token(str(user.id), user.email)
                return {
                    "token": token,
                    "email": user.email,
                    "preferred_language": user.preferred_language,
                    "message": "Login successful."
                }
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Login failed: {str(exc)}")

    raise HTTPException(status_code=503, detail="Database unavailable.")


@router.get("/me")
def me(authorization: str = "") -> dict:
    """Decode JWT from Authorization header."""
    token = authorization.replace("Bearer ", "").strip()
    if not token:
        raise HTTPException(status_code=401, detail="No token provided.")
    payload = _decode_token(token)
    if not payload.get("sub"):
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    return {"user_id": payload["sub"], "email": payload.get("email", "")}
