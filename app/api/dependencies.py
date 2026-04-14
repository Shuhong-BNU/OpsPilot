"""FastAPI 依赖注入."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.services.auth_service import (
    ROLE_ADMIN,
    ROLE_OPERATOR,
    ROLE_VIEWER,
    auth_service,
)


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    """解析当前登录用户."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录或缺少访问令牌",
        )

    try:
        payload = auth_service.verify_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    user = auth_service.get_user_by_username(payload["sub"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )
    return user


def require_viewer(user: dict = Depends(get_current_user)) -> dict:
    """最小 viewer 权限."""
    if not auth_service.require_role(user["role"], ROLE_VIEWER):
        raise HTTPException(status_code=403, detail="权限不足")
    return user


def require_operator(user: dict = Depends(get_current_user)) -> dict:
    """最小 operator 权限."""
    if not auth_service.require_role(user["role"], ROLE_OPERATOR):
        raise HTTPException(status_code=403, detail="仅 operator/admin 可访问")
    return user


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """最小 admin 权限."""
    if not auth_service.require_role(user["role"], ROLE_ADMIN):
        raise HTTPException(status_code=403, detail="仅 admin 可访问")
    return user
