"""Authentication helpers for the Agent Web API."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import secrets

import bcrypt
from fastapi import HTTPException, Request, status
import jwt
from jwt import InvalidTokenError

from api_view.web_config import (
    AUTH_COOKIE_NAME,
    AUTH_ISSUER,
    AUTH_JWT_SECRET,
    AUTH_TOKEN_EXPIRE_MINUTES,
)
from erp_backend import database


@dataclass(frozen=True)
class CurrentUser:
    """Trusted user identity reconstructed from the signed session token."""

    user_id: str
    username: str
    display_name: str
    role: str
    department: str | None = None

    def public_dict(self) -> dict:
        return asdict(self)


def _require_secret() -> str:
    if not AUTH_JWT_SECRET or len(AUTH_JWT_SECRET) < 32:
        raise RuntimeError(
            "AUTH_JWT_SECRET must be configured with at least 32 characters"
        )
    return AUTH_JWT_SECRET


def validate_auth_config() -> None:
    """Fail startup early when secure session signing is not configured."""
    _require_secret()


def find_active_user(username: str) -> dict | None:
    """Load an enabled ERP user by username."""
    return database.fetch_one(
        """
        SELECT id, username, password, real_name, role, department
        FROM `user`
        WHERE username = %s AND status = 1 AND deleted = 0
        LIMIT 1
        """,
        (username,),
    )


def _to_current_user(row: dict) -> CurrentUser:
    username = str(row["username"])
    return CurrentUser(
        user_id=username,
        username=username,
        display_name=row.get("real_name") or username,
        role=row.get("role") or "purchase",
        department=row.get("department"),
    )


def authenticate_user(username: str, password: str) -> CurrentUser | None:
    """Validate a username/password pair against the ERP user table."""
    row = find_active_user(username.strip())
    if row is None:
        # Keep the missing-user and bad-password paths closer in timing.
        bcrypt.hashpw(b"invalid-password", bcrypt.gensalt(rounds=4))
        return None

    stored_hash = str(row.get("password") or "").encode("utf-8")
    try:
        valid = bcrypt.checkpw(password.encode("utf-8"), stored_hash)
    except (ValueError, TypeError):
        valid = False
    return _to_current_user(row) if valid else None


def create_session_token(user: CurrentUser) -> str:
    """Create a short-lived signed JWT for the authenticated user."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user.user_id,
        "username": user.username,
        "name": user.display_name,
        "role": user.role,
        "iss": AUTH_ISSUER,
        "iat": now,
        "exp": now + timedelta(minutes=AUTH_TOKEN_EXPIRE_MINUTES),
        "jti": secrets.token_urlsafe(16),
    }
    return jwt.encode(payload, _require_secret(), algorithm="HS256")


def decode_session_token(token: str) -> dict:
    """Decode and validate a session token."""
    return jwt.decode(
        token,
        _require_secret(),
        algorithms=["HS256"],
        issuer=AUTH_ISSUER,
        options={"require": ["sub", "iss", "iat", "exp"]},
    )


def get_current_user(request: Request) -> CurrentUser:
    """FastAPI dependency that resolves the authenticated ERP user."""
    token = request.cookies.get(AUTH_COOKIE_NAME)
    if not token:
        authorization = request.headers.get("Authorization", "")
        scheme, _, credentials = authorization.partition(" ")
        if scheme.lower() == "bearer":
            token = credentials.strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录或登录已过期",
        )

    try:
        payload = decode_session_token(token)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录状态无效或已过期",
        ) from exc

    row = find_active_user(str(payload["sub"]))
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已被停用",
        )
    return _to_current_user(row)
