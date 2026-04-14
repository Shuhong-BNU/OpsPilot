"""会话相关模型."""

from typing import Any

from pydantic import BaseModel, Field


class SessionSummary(BaseModel):
    session_id: str = Field(..., description="会话 ID")
    title: str = Field(..., description="会话标题")
    thread_id: str = Field(..., description="持久化 thread_id")
    last_intent: str | None = Field(default=None, description="最近一次意图")
    message_count: int = Field(default=0, description="消息数量")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")


class ChatRouteMetadata(BaseModel):
    intent: str = Field(..., description="识别出的意图")
    route: str = Field(..., description="命中的执行链路")
    reason: str = Field(..., description="路由原因")
    trace: dict[str, Any] | None = Field(default=None, description="检索 trace")
