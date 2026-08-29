"""Login, logout, and current-user endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field

from api_view.auth import CurrentUser, authenticate_user, create_session_token, get_current_user
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


@router.post("/auth/login")
def login(payload: LoginRequest, response: Response):
    user = authenticate_user(payload.username, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

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
def me(current_user: CurrentUser = Depends(get_current_user)):
    return {"user": current_user.public_dict()}

