"""对话接口。"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from sse_starlette.sse import EventSourceResponse

from app.api.dependencies import require_viewer
from app.models.request import ChatRequest, ClearRequest
from app.models.response import SessionInfoResponse, ApiResponse
from app.services.chat_service import chat_service
from app.services.session_service import session_service

router = APIRouter()


@router.post("/chat")
async def chat(request: ChatRequest, user: dict = Depends(require_viewer)):
    """快速对话接口。"""
    try:
        logger.info(f"[会话 {request.id}] 收到快速对话请求: {request.question}")
        result = await chat_service.chat(request.question, request.id, user)
        logger.info(f"[会话 {request.id}] 快速对话完成")

        return {
            "code": 200,
            "message": "success",
            "data": {
                "success": True,
                "answer": result["answer"],
                "route": result["route"],
                "timing": result["timing"],
                "errorMessage": None,
            },
        }
    except Exception as exc:
        logger.error(f"对话接口错误: {exc}")
        return {
            "code": 500,
            "message": "error",
            "data": {
                "success": False,
                "answer": None,
                "errorMessage": str(exc),
            },
        }


@router.post("/chat_stream")
async def chat_stream(request: ChatRequest, user: dict = Depends(require_viewer)):
    """流式对话接口（SSE）。"""
    logger.info(f"[会话 {request.id}] 收到流式对话请求: {request.question}")

    async def event_generator():
        try:
            async for chunk in chat_service.stream_chat(request.question, request.id, user):
                chunk_type = chunk.get("type", "unknown")
                chunk_data = chunk.get("data", None)

                if chunk_type in {"tool_call", "search_results", "route", "status", "content", "trace_step"}:
                    yield {
                        "event": "message",
                        "data": json.dumps(
                            {
                                "type": chunk_type,
                                "data": chunk_data,
                            },
                            ensure_ascii=False,
                        ),
                    }
                elif chunk_type == "complete":
                    payload = chunk_data or {}
                    yield {
                        "event": "message",
                        "data": json.dumps(
                            {
                                "type": "done",
                                "data": {
                                    **payload,
                                    "answer": payload.get("answer", ""),
                                },
                            },
                            ensure_ascii=False,
                        ),
                    }
                elif chunk_type == "error":
                    yield {
                        "event": "message",
                        "data": json.dumps(
                            {
                                "type": "error",
                                "data": chunk_data,
                            },
                            ensure_ascii=False,
                        ),
                    }
                else:
                    yield {
                        "event": "message",
                        "data": json.dumps(chunk, ensure_ascii=False),
                    }

            logger.info(f"[会话 {request.id}] 流式对话完成")
        except Exception as exc:
            logger.error(f"流式对话接口错误: {exc}")
            yield {
                "event": "message",
                "data": json.dumps(
                    {
                        "type": "error",
                        "data": str(exc),
                    },
                    ensure_ascii=False,
                ),
            }

    return EventSourceResponse(event_generator())


@router.post("/chat/clear", response_model=ApiResponse)
async def clear_session(request: ClearRequest, user: dict = Depends(require_viewer)):
    """清空会话历史。"""
    try:
        success = session_service.clear_session(request.session_id, user["id"])
        logger.info(f"清空会话: {request.session_id}, 结果: {success}")

        return ApiResponse(
            status="success" if success else "error",
            message="会话已清空" if success else "清空会话失败",
            data=None,
        )
    except Exception as exc:
        logger.error(f"清空会话错误: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/chat/session/{session_id}", response_model=SessionInfoResponse)
async def get_session_info(
    session_id: str,
    user: dict = Depends(require_viewer),
) -> SessionInfoResponse:
    """查询会话历史。"""
    try:
        session = session_service.get_session(session_id, user["id"])
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")

        history = session_service.list_messages(session_id)
        return SessionInfoResponse(
            session_id=session_id,
            message_count=len(history),
            history=history,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"获取会话信息错误: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
