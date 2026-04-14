"""会话、消息与工作流持久化服务."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.services.database_service import database_service


def utc_now() -> str:
    """返回 ISO UTC 时间."""
    return datetime.now(timezone.utc).isoformat()


class SessionService:
    """统一管理 sessions/messages/workflow_runs/tool_call_logs."""

    def ensure_session(
        self,
        session_id: str,
        user_id: int,
        title: str | None = None,
        thread_id: str | None = None,
        last_intent: str | None = None,
    ) -> dict[str, Any]:
        """确保会话存在."""
        existing = self.get_session(session_id=session_id, user_id=user_id)
        now = utc_now()
        thread_id = thread_id or session_id
        title = title or "新对话"

        if existing:
            database_service.execute(
                """
                UPDATE sessions
                SET title = ?, thread_id = ?, last_intent = ?, updated_at = ?
                WHERE session_id = ? AND user_id = ?
                """,
                (
                    title or existing["title"],
                    thread_id,
                    last_intent or existing.get("last_intent"),
                    now,
                    session_id,
                    user_id,
                ),
            )
        else:
            database_service.execute(
                """
                INSERT INTO sessions (
                    session_id, user_id, title, thread_id, last_intent, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (session_id, user_id, title, thread_id, last_intent, now, now),
            )

        return self.get_session(session_id=session_id, user_id=user_id) or {}

    def get_session(self, session_id: str, user_id: int) -> dict[str, Any] | None:
        """获取单个会话."""
        return database_service.fetch_one(
            """
            SELECT session_id, user_id, title, thread_id, last_intent, created_at, updated_at
            FROM sessions
            WHERE session_id = ? AND user_id = ?
            """,
            (session_id, user_id),
        )

    def list_sessions(self, user_id: int) -> list[dict[str, Any]]:
        """列出用户全部会话."""
        rows = database_service.fetch_all(
            """
            SELECT session_id, title, thread_id, last_intent, created_at, updated_at
            FROM sessions
            WHERE user_id = ?
            ORDER BY updated_at DESC
            """,
            (user_id,),
        )
        for row in rows:
            row["message_count"] = self.count_messages(row["session_id"])
        return rows

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        intent: str | None = None,
        route: str | None = None,
    ) -> None:
        """追加消息."""
        database_service.execute(
            """
            INSERT INTO messages (session_id, role, content, intent, route, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session_id, role, content, intent, route, utc_now()),
        )
        database_service.execute(
            "UPDATE sessions SET updated_at = ? WHERE session_id = ?",
            (utc_now(), session_id),
        )

    def list_messages(self, session_id: str) -> list[dict[str, Any]]:
        """读取会话历史."""
        return database_service.fetch_all(
            """
            SELECT role, content, intent, route, created_at AS timestamp
            FROM messages
            WHERE session_id = ?
            ORDER BY id ASC
            """,
            (session_id,),
        )

    def clear_session(self, session_id: str, user_id: int) -> bool:
        """清空单个会话及相关记录."""
        session = self.get_session(session_id=session_id, user_id=user_id)
        if not session:
            return False

        database_service.execute("DELETE FROM tool_call_logs WHERE session_id = ?", (session_id,))
        database_service.execute("DELETE FROM workflow_runs WHERE session_id = ?", (session_id,))
        database_service.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        database_service.execute(
            "DELETE FROM sessions WHERE session_id = ? AND user_id = ?",
            (session_id, user_id),
        )
        return True

    def count_messages(self, session_id: str) -> int:
        """统计消息数量."""
        row = database_service.fetch_one(
            "SELECT COUNT(*) AS count FROM messages WHERE session_id = ?",
            (session_id,),
        )
        return int(row["count"]) if row else 0

    def start_workflow_run(
        self,
        session_id: str,
        workflow_type: str,
        input_text: str,
    ) -> str:
        """创建工作流运行记录."""
        run_id = str(uuid4())
        database_service.execute(
            """
            INSERT INTO workflow_runs (run_id, session_id, workflow_type, status, input_text, started_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (run_id, session_id, workflow_type, "running", input_text, utc_now()),
        )
        return run_id

    def finish_workflow_run(
        self,
        run_id: str,
        status: str,
        result_summary: str | None,
        duration_ms: int | None,
    ) -> None:
        """结束工作流运行记录."""
        database_service.execute(
            """
            UPDATE workflow_runs
            SET status = ?, result_summary = ?, completed_at = ?, duration_ms = ?
            WHERE run_id = ?
            """,
            (status, result_summary, utc_now(), duration_ms, run_id),
        )

    def log_tool_call(
        self,
        session_id: str,
        workflow_run_id: str | None,
        tool_name: str,
        status: str,
        latency_ms: int | None,
        server_name: str | None = None,
        input_payload: str | None = None,
        output_payload: str | None = None,
        error_message: str | None = None,
    ) -> None:
        """记录工具调用日志."""
        database_service.execute(
            """
            INSERT INTO tool_call_logs (
                session_id, workflow_run_id, tool_name, server_name, status, latency_ms,
                input_payload, output_payload, error_message, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                workflow_run_id,
                tool_name,
                server_name,
                status,
                latency_ms,
                input_payload,
                output_payload,
                error_message,
                utc_now(),
            ),
        )


session_service = SessionService()
