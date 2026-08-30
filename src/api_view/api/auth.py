"""Login, logout, and current-user endpoints."""

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from api_view.auth import (
    CurrentUser,
    authenticate_user,
    create_demo_user,
    create_session_token,
    demo_mode_enabled,
    get_current_user,
)
from api_view.web_config import (
    AUTH_COOKIE_NAME,
    AUTH_COOKIE_SAMESITE,
    AUTH_COOKIE_SECURE,
    AUTH_TOKEN_EXPIRE_MINUTES,
)


router = APIRouter()


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)


def _set_session_cookie(response: Response, user: CurrentUser) -> None:
    token = create_session_token(user)
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        max_age=AUTH_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=AUTH_COOKIE_SECURE,
        samesite=AUTH_COOKIE_SAMESITE,
        path="/",
    )


@router.post("/auth/login")
def login(payload: LoginRequest, response: Response):
    user = authenticate_user(payload.username, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    _set_session_cookie(response, user)
    return {"user": user.public_dict()}


@router.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie(
        key=AUTH_COOKIE_NAME,
        path="/",
        secure=AUTH_COOKIE_SECURE,
        httponly=True,
        samesite=AUTH_COOKIE_SAMESITE,
    )
    return {"success": True}


@router.get("/auth/me")
def me(request: Request, response: Response):
    demo_mode = demo_mode_enabled()
    try:
        current_user = get_current_user(request)
    except HTTPException as exc:
        if exc.status_code != status.HTTP_401_UNAUTHORIZED or not demo_mode:
            raise
        current_user = create_demo_user()
        _set_session_cookie(response, current_user)
    else:
        # Demo deployments must not inherit an old yyf/admin browser session.
        if demo_mode and not current_user.is_demo:
            current_user = create_demo_user()
            _set_session_cookie(response, current_user)
    return {"user": current_user.public_dict()}

