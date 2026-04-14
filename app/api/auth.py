"""鉴权接口."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_current_user
from app.models.auth import LoginRequest, LoginResponse
from app.services.auth_service import auth_service

router = APIRouter()


@router.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest) -> LoginResponse:
    """用户名密码登录."""
    user = auth_service.authenticate(request.username, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = auth_service.create_access_token(user)
    return LoginResponse(
        access_token=token,
        username=user["username"],
        role=user["role"],
    )


@router.get("/auth/me")
async def get_me(user: dict = Depends(get_current_user)):
    """返回当前用户信息."""
    return user
