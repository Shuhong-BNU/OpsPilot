"""请求上下文，用于工具日志和权限透传."""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field


@dataclass
class RequestContext:
    session_id: str = "default"
    workflow_run_id: str | None = None
    user_role: str = "viewer"
    allowed_mcp_tools: set[str] = field(default_factory=set)


request_context_var: ContextVar[RequestContext] = ContextVar(
    "request_context",
    default=RequestContext(),
)


def set_request_context(context: RequestContext):
    """设置当前请求上下文."""
    return request_context_var.set(context)


def get_request_context() -> RequestContext:
    """获取当前请求上下文."""
    return request_context_var.get()


def reset_request_context(token) -> None:
    """恢复上下文."""
    request_context_var.reset(token)
