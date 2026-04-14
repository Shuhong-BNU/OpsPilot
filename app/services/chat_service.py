"""聊天编排服务：意图识别、分流与持久化."""

from __future__ import annotations

import asyncio
from time import perf_counter
from typing import Any, AsyncGenerator

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_qwq import ChatQwen

from app.config import config
from app.services.aiops_service import aiops_service
from app.services.intent_service import (
    INTENT_AIOPS,
    INTENT_KNOWLEDGE_QA,
    INTENT_SIMPLE_QA,
    INTENT_SMALLTALK,
    INTENT_UNSUPPORTED,
    intent_service,
)
from app.services.metrics_service import metrics_service
from app.services.request_context_service import (
    RequestContext,
    reset_request_context,
    set_request_context,
)
from app.services.retrieval_service import retrieval_service
from app.services.session_service import session_service


class ChatService:
    """对外提供同步与流式聊天能力."""

    def __init__(self) -> None:
        self._model = None

    def _get_model(self) -> ChatQwen:
        if self._model is None:
            self._model = ChatQwen(
                model=config.rag_model,
                api_key=config.dashscope_api_key,
                temperature=0.3,
                streaming=False,
            )
        return self._model

    async def chat(
        self,
        question: str,
        session_id: str,
        user: dict[str, Any],
    ) -> dict[str, Any]:
        """执行非流式对话."""
        start = perf_counter()
        intent = intent_service.classify(question)
        session_service.ensure_session(
            session_id=session_id,
            user_id=user["id"],
            title=question[:30] or "新对话",
            thread_id=session_id,
            last_intent=intent.intent,
        )
        session_service.add_message(session_id, "user", question, intent=intent.intent, route=intent.intent)

        if intent.intent == INTENT_UNSUPPORTED:
            answer = "这个请求超出了 OpsPilot 的职责范围。我更适合处理运维知识问答、告警分析和排障建议。"
            trace = None
        elif intent.intent == INTENT_AIOPS:
            answer = await self._run_aiops(question, session_id, user["role"])
            trace = None
        elif intent.intent == INTENT_KNOWLEDGE_QA:
            answer, trace = await self._answer_with_knowledge(question, session_id, user["role"])
        elif intent.intent in {INTENT_SMALLTALK, INTENT_SIMPLE_QA}:
            answer = await self._answer_direct(question)
            trace = None
        else:
            answer = await self._answer_direct(question)
            trace = None

        session_service.add_message(session_id, "assistant", answer, intent=intent.intent, route=intent.intent)
        metrics_service.increment("request_total")
        metrics_service.observe("request_latency", int((perf_counter() - start) * 1000))
        return {
            "answer": answer,
            "route": {
                "intent": intent.intent,
                "route": intent.intent,
                "reason": intent.reason,
                "trace": trace,
            },
        }

    async def stream_chat(
        self,
        question: str,
        session_id: str,
        user: dict[str, Any],
    ) -> AsyncGenerator[dict[str, Any], None]:
        """执行流式对话."""
        start = perf_counter()
        intent = intent_service.classify(question)
        session_service.ensure_session(
            session_id=session_id,
            user_id=user["id"],
            title=question[:30] or "新对话",
            thread_id=session_id,
            last_intent=intent.intent,
        )
        session_service.add_message(session_id, "user", question, intent=intent.intent, route=intent.intent)
        yield {
            "type": "route",
            "data": {
                "intent": intent.intent,
                "route": intent.intent,
                "reason": intent.reason,
            },
        }

        if intent.intent == INTENT_UNSUPPORTED:
            answer = "这个请求超出了 OpsPilot 的职责范围。我更适合处理运维知识问答、告警分析和排障建议。"
            async for chunk in self._yield_text(answer):
                yield chunk
            session_service.add_message(session_id, "assistant", answer, intent=intent.intent, route=intent.intent)
        elif intent.intent == INTENT_AIOPS:
            final_answer = ""
            async for event in aiops_service.diagnose(session_id=session_id):
                if event.get("type") == "complete":
                    final_answer = event.get("diagnosis", {}).get("report", "")
                yield event
            session_service.add_message(
                session_id,
                "assistant",
                final_answer or "AIOps 诊断已完成。",
                intent=intent.intent,
                route=intent.intent,
            )
        elif intent.intent == INTENT_KNOWLEDGE_QA:
            answer, trace = await self._answer_with_knowledge(question, session_id, user["role"])
            yield {"type": "search_results", "data": trace}
            async for chunk in self._yield_text(answer):
                yield chunk
            session_service.add_message(session_id, "assistant", answer, intent=intent.intent, route=intent.intent)
        else:
            answer = await self._answer_direct(question)
            async for chunk in self._yield_text(answer):
                yield chunk
            session_service.add_message(session_id, "assistant", answer, intent=intent.intent, route=intent.intent)

        metrics_service.increment("request_total")
        metrics_service.observe("request_latency", int((perf_counter() - start) * 1000))
        yield {"type": "complete", "data": {"intent": intent.intent}}

    async def _answer_direct(self, question: str) -> str:
        if not config.dashscope_api_key:
            return "当前未配置 LLM 密钥，暂时只能提供路由与会话能力。"

        messages = [
            SystemMessage(
                content=(
                    "你是 OpsPilot，定位是基于 RAG 与 MCP 的智能运维助手。"
                    "对于简单问题请直接、简洁、专业地回答，不要夸大能力。"
                )
            ),
            HumanMessage(content=question),
        ]
        result = await self._get_model().ainvoke(messages)
        return result.content if hasattr(result, "content") else str(result)

    async def _answer_with_knowledge(
        self,
        question: str,
        session_id: str,
        role: str,
    ) -> tuple[str, dict[str, Any]]:
        docs, trace = retrieval_service.hybrid_search(question)
        context = retrieval_service.format_docs(docs)
        if not config.dashscope_api_key:
            return (
                "当前未配置 LLM 密钥，但已完成混合检索。你可以先查看检索 trace。",
                trace.to_dict(),
            )

        run_id = session_service.start_workflow_run(
            session_id=session_id,
            workflow_type="knowledge_qa",
            input_text=question,
        )
        token = set_request_context(
            RequestContext(
                session_id=session_id,
                workflow_run_id=run_id,
                user_role=role,
                allowed_mcp_tools=set(),
            )
        )
        try:
            messages = [
                SystemMessage(
                    content=(
                        "你是 OpsPilot 的知识问答模块。请严格基于给定资料回答，"
                        "如果资料不足就明确说明，不要编造。回答尽量贴近运维场景。"
                    )
                ),
                HumanMessage(content=f"问题：{question}\n\n参考资料：\n{context}"),
            ]
            result = await self._get_model().ainvoke(messages)
            answer = result.content if hasattr(result, "content") else str(result)
            session_service.finish_workflow_run(
                run_id,
                status="completed",
                result_summary=answer[:500],
                duration_ms=trace.dense_latency_ms + trace.sparse_latency_ms + trace.rerank_latency_ms,
            )
            return answer, trace.to_dict()
        except Exception as exc:
            session_service.finish_workflow_run(
                run_id,
                status="failed",
                result_summary=str(exc),
                duration_ms=trace.dense_latency_ms + trace.sparse_latency_ms + trace.rerank_latency_ms,
            )
            raise
        finally:
            reset_request_context(token)

    async def _run_aiops(self, question: str, session_id: str, role: str) -> str:
        final_report = ""
        run_id = session_service.start_workflow_run(
            session_id=session_id,
            workflow_type="aiops_diagnosis",
            input_text=question,
        )
        token = set_request_context(
            RequestContext(
                session_id=session_id,
                workflow_run_id=run_id,
                user_role=role,
                allowed_mcp_tools=set(),
            )
        )
        started_at = perf_counter()
        try:
            async for event in aiops_service.execute(question, session_id=session_id):
                if event.get("type") == "report":
                    final_report = event.get("report", "")
                if event.get("type") == "complete":
                    final_report = event.get("response", final_report)
            duration_ms = int((perf_counter() - started_at) * 1000)
            metrics_service.observe("aiops_workflow_latency", duration_ms)
            session_service.finish_workflow_run(
                run_id,
                status="completed",
                result_summary=final_report[:500],
                duration_ms=duration_ms,
            )
            return final_report or "AIOps 诊断已执行完成。"
        except Exception as exc:
            duration_ms = int((perf_counter() - started_at) * 1000)
            session_service.finish_workflow_run(
                run_id,
                status="failed",
                result_summary=str(exc),
                duration_ms=duration_ms,
            )
            raise
        finally:
            reset_request_context(token)

    async def _yield_text(self, text: str) -> AsyncGenerator[dict[str, Any], None]:
        for start in range(0, len(text), 48):
            await asyncio.sleep(0)
            yield {"type": "content", "data": text[start:start + 48]}


chat_service = ChatService()
