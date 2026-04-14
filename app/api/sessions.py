"""会话管理接口."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import require_viewer
from app.services.session_service import session_service

router = APIRouter()


@router.get("/sessions")
async def list_sessions(user: dict = Depends(require_viewer)):
    """列出当前用户的会话."""
    return {
        "code": 200,
        "message": "success",
        "data": session_service.list_sessions(user["id"]),
    }


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, user: dict = Depends(require_viewer)):
    """读取会话详情."""
    session = session_service.get_session(session_id, user["id"])
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {
        "code": 200,
        "message": "success",
        "data": {
            **session,
            "history": session_service.list_messages(session_id),
        },
    }


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, user: dict = Depends(require_viewer)):
    """删除单个会话."""
    success = session_service.clear_session(session_id, user["id"])
    if not success:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {
        "code": 200,
        "message": "success",
        "data": {"session_id": session_id},
    }
