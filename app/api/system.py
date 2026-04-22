"""系统运行状态接口."""

from fastapi import APIRouter, Depends

from app.api.dependencies import require_viewer
from app.services.runtime_status_service import runtime_status_service

router = APIRouter()


@router.get("/system/status")
async def get_system_status(user: dict = Depends(require_viewer)):
    """返回运行状态、模型配置与依赖可用性。"""
    return {
        "code": 200,
        "message": "success",
        "data": runtime_status_service.get_status(),
    }
