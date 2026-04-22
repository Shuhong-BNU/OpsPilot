"""聊天编排服务：意图识别、分流与持久化。"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
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


def iso_utc_now() -> str:
    """返回 ISO UTC 时间。"""
    return datetime.now(timezone.utc).isoformat()


class ChatService:
    """对外提供同步与流式聊天能力。"""

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

    def _build_timing(
        self,
        request_started_at: str,
        assistant_started_at: str,
        assistant_completed_at: str,
        duration_ms: int,
        **extra_fields: Any,
    ) -> dict[str, Any]:
        payload = {
            "request_started_at": request_started_at,
            "assistant_started_at": assistant_started_at,
            "assistant_completed_at": assistant_completed_at,
            "duration_ms": duration_ms,
        }
        for key, value in extra_fields.items():
            if value is not None:
                payload[key] = value
        return payload

    @staticmethod
    def _duration_between(started_at: str | None, completed_at: str | None) -> int | None:
        if not started_at or not completed_at:
            return None
        try:
            started = datetime.fromisoformat(started_at)
            completed = datetime.fromisoformat(completed_at)
        except ValueError:
            return None
        return max(0, int((completed - started).total_seconds() * 1000))

    def _make_trace_step(
        self,
        title: str,
        detail: str,
        status: str = "info",
        phase: str = "processing",
        duration_ms: int | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "title": title,
            "detail": detail,
            "status": status,
            "phase": phase,
            "timestamp": iso_utc_now(),
        }
        if duration_ms is not None:
            payload["duration_ms"] = duration_ms
        return {"type": "trace_step", "data": payload}

    async def chat(
        self,
        question: str,
        session_id: str,
        user: dict[str, Any],
    ) -> dict[str, Any]:
        """执行非流式对话。"""
        started_at = perf_counter()
        request_started_at = iso_utc_now()
        intent = intent_service.classify(question)
        session_service.ensure_session(
            session_id=session_id,
            user_id=user["id"],
            title=question[:30] or "新对话",
            thread_id=session_id,
            last_intent=intent.intent,
        )
        session_service.add_message(session_id, "user", question, intent=intent.intent, route=intent.intent)

        assistant_started_at = iso_utc_now()
        trace: dict[str, Any] | None = None

        if intent.intent == INTENT_UNSUPPORTED:
            answer = "这个请求超出了 OpsPilot 的职责范围。我更适合处理运维知识问答、告警分析和排障建议。"
        elif intent.intent == INTENT_AIOPS:
            answer = await self._run_aiops(question, session_id, user["role"])
        elif intent.intent == INTENT_KNOWLEDGE_QA:
            answer, trace = await self._answer_with_knowledge(question, session_id, user["role"])
        elif intent.intent in {INTENT_SMALLTALK, INTENT_SIMPLE_QA}:
            answer = await self._answer_direct(question)
        else:
            answer = await self._answer_direct(question)

        assistant_completed_at = iso_utc_now()
        duration_ms = int((perf_counter() - started_at) * 1000)

        session_service.add_message(session_id, "assistant", answer, intent=intent.intent, route=intent.intent)
        metrics_service.increment("request_total")
        metrics_service.observe("request_latency", duration_ms)
        return {
            "answer": answer,
            "route": {
                "intent": intent.intent,
                "route": intent.intent,
                "reason": intent.reason,
                "trace": trace,
            },
            "timing": self._build_timing(
                request_started_at=request_started_at,
                assistant_started_at=assistant_started_at,
                assistant_completed_at=assistant_completed_at,
                duration_ms=duration_ms,
            ),
        }

    async def stream_chat(
        self,
        question: str,
        session_id: str,
        user: dict[str, Any],
    ) -> AsyncGenerator[dict[str, Any], None]:
        """执行流式对话。"""
        started_at = perf_counter()
        request_started_at = iso_utc_now()
        assistant_started_at: str | None = None
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
                "timestamp": request_started_at,
            },
        }

        def ensure_assistant_started() -> str:
            nonlocal assistant_started_at
            if assistant_started_at is None:
                assistant_started_at = iso_utc_now()
            return assistant_started_at

        stream_timing: dict[str, Any] = {
            "retrieval_completed_at": None,
            "retrieval_duration_ms": None,
            "llm_started_at": None,
            "llm_duration_ms": None,
            "first_chunk_at": None,
            "time_to_first_chunk_ms": None,
        }

        async def emit_answer(answer_text: str, first_chunk_detail: str) -> AsyncGenerator[dict[str, Any], None]:
            first_chunk_emitted = False
            async for chunk in self._yield_text(answer_text):
                if not first_chunk_emitted:
                    first_chunk_emitted = True
                    first_chunk_at = iso_utc_now()
                    stream_timing["first_chunk_at"] = first_chunk_at
                    stream_timing["time_to_first_chunk_ms"] = self._duration_between(
                        stream_timing.get("llm_started_at"),
                        first_chunk_at,
                    )
                    yield self._make_trace_step(
                        "首段输出",
                        first_chunk_detail,
                        status="success",
                        phase="respond",
                        duration_ms=stream_timing.get("time_to_first_chunk_ms"),
                    )
                yield chunk

        answer = ""

        if intent.intent == INTENT_UNSUPPORTED:
            ensure_assistant_started()
            yield self._make_trace_step(
                "边界控制",
                "命中越界问题，返回能力边界说明。",
                status="error",
                phase="guardrail",
            )
            answer = "这个请求超出了 OpsPilot 的职责范围。我更适合处理运维知识问答、告警分析和排障建议。"
            async for chunk in emit_answer(answer, "模型结果已返回，开始向界面输出内容。"):
                yield chunk
        elif intent.intent == INTENT_AIOPS:
            ensure_assistant_started()
            yield self._make_trace_step(
                "意图路由",
                "已切换到 AIOps 诊断链路，将按 Plan-Execute-Replan 执行。",
                phase="route",
            )

            final_answer = ""
            async for event in aiops_service.execute(question, session_id=session_id):
                event_type = event.get("type", "")

                if event_type == "plan":
                    plan = event.get("plan", []) or []
                    detail = event.get("message", "执行计划已生成")
                    if plan:
                        detail = f"{detail}\n" + "\n".join(
                            f"{index + 1}. {item}" for index, item in enumerate(plan)
                        )
                    yield self._make_trace_step("执行计划", detail, phase="plan")
                elif event_type == "step_complete":
                    step_name = event.get("current_step") or "步骤执行完成"
                    remaining = event.get("remaining_steps")
                    detail = step_name if remaining is None else f"{step_name}\n剩余步骤：{remaining}"
                    yield self._make_trace_step("执行步骤", detail, status="success", phase="execute")
                elif event_type == "report":
                    final_answer = event.get("report", "") or final_answer
                    yield self._make_trace_step(
                        "报告整理",
                        event.get("message", "诊断报告已生成"),
                        status="success",
                        phase="report",
                    )
                elif event_type == "status":
                    yield self._make_trace_step(
                        "链路状态",
                        event.get("message", "正在执行诊断链路"),
                        phase=event.get("stage", "status"),
                    )
                elif event_type == "error":
                    final_answer = final_answer or f"本次 AIOps 诊断未完成：{event.get('message', '未知错误')}"
                    yield self._make_trace_step(
                        "AIOps 错误",
                        event.get("message", "AIOps 诊断失败"),
                        status="error",
                        phase="error",
                    )
                elif event_type == "complete":
                    final_answer = event.get("response", "") or final_answer

            answer = final_answer or "AIOps 诊断流程已结束，但未生成有效报告。"
            yield self._make_trace_step(
                "回答生成",
                "正在输出诊断报告。",
                status="success",
                phase="respond",
            )
            async for chunk in emit_answer(answer, "模型结果已返回，开始向界面输出内容。"):
                yield chunk
        elif intent.intent == INTENT_KNOWLEDGE_QA:
            ensure_assistant_started()
            yield self._make_trace_step(
                "检索准备",
                "开始检索运维文档与知识库内容。",
                phase="retrieval",
            )

            retrieval_started_at = perf_counter()
            docs, trace = retrieval_service.hybrid_search(question)
            retrieval_duration_ms = int((perf_counter() - retrieval_started_at) * 1000)
            if retrieval_duration_ms <= 0:
                retrieval_duration_ms = trace.dense_latency_ms + trace.sparse_latency_ms + trace.rerank_latency_ms
            stream_timing["retrieval_completed_at"] = iso_utc_now()
            stream_timing["retrieval_duration_ms"] = retrieval_duration_ms
            yield {"type": "search_results", "data": {**trace.to_dict(), "timestamp": iso_utc_now()}}
            yield self._make_trace_step(
                "混合检索",
                (
                    f"dense={trace.dense_hits} | sparse={trace.sparse_hits} | "
                    f"fusion={trace.fusion_hits} | rerank={trace.rerank_hits}"
                ),
                status="success",
                phase="retrieval",
                duration_ms=retrieval_duration_ms,
            )

            yield self._make_trace_step(
                "答案生成",
                "已完成文档召回与重排，正在生成回答。",
                phase="generation",
            )
            llm_started_at = iso_utc_now()
            llm_started_perf = perf_counter()
            stream_timing["llm_started_at"] = llm_started_at
            yield self._make_trace_step(
                "LLM 调用开始",
                "已完成文档召回与重排，正在请求模型生成回答。",
                phase="generation",
            )
            answer = await self._answer_with_context(question, session_id, user["role"], docs, trace)
            stream_timing["llm_duration_ms"] = int((perf_counter() - llm_started_perf) * 1000)
            async for chunk in emit_answer(answer, "模型结果已返回，开始向界面输出内容。"):
                yield chunk
        else:
            ensure_assistant_started()
            yield self._make_trace_step(
                "答案生成",
                "正在生成回答。",
                phase="generation",
            )
            answer = await self._answer_direct(question)
            async for chunk in emit_answer(answer, "模型结果已返回，开始向界面输出内容。"):
                yield chunk

        assistant_completed_at = iso_utc_now()
        duration_ms = int((perf_counter() - started_at) * 1000)
        session_service.add_message(session_id, "assistant", answer, intent=intent.intent, route=intent.intent)

        metrics_service.increment("request_total")
        metrics_service.observe("request_latency", duration_ms)

        yield {
            "type": "complete",
            "data": {
                "intent": intent.intent,
                "answer": answer,
                **self._build_timing(
                    request_started_at=request_started_at,
                    assistant_started_at=assistant_started_at or assistant_completed_at,
                    assistant_completed_at=assistant_completed_at,
                    duration_ms=duration_ms,
                    retrieval_completed_at=stream_timing.get("retrieval_completed_at"),
                    retrieval_duration_ms=stream_timing.get("retrieval_duration_ms"),
                    llm_started_at=stream_timing.get("llm_started_at"),
                    llm_duration_ms=stream_timing.get("llm_duration_ms"),
                    first_chunk_at=stream_timing.get("first_chunk_at"),
                    time_to_first_chunk_ms=stream_timing.get("time_to_first_chunk_ms"),
                ),
            },
        }

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
        answer = await self._answer_with_context(question, session_id, role, docs, trace)
        return answer, trace.to_dict()

    async def _answer_with_context(
        self,
        question: str,
        session_id: str,
        role: str,
        docs: list[Any],
        trace: Any,
    ) -> str:
        context = retrieval_service.format_docs(docs)
        if not config.dashscope_api_key:
            return "当前未配置 LLM 密钥，但已完成混合检索。你可以先查看检索 trace。"

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
        started_at = perf_counter()
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
            total_duration_ms = trace.dense_latency_ms + trace.sparse_latency_ms + trace.rerank_latency_ms + int(
                (perf_counter() - started_at) * 1000
            )
            session_service.finish_workflow_run(
                run_id,
                status="completed",
                result_summary=answer[:500],
                duration_ms=total_duration_ms,
            )
            return answer
        except Exception as exc:
            total_duration_ms = trace.dense_latency_ms + trace.sparse_latency_ms + trace.rerank_latency_ms + int(
                (perf_counter() - started_at) * 1000
            )
            session_service.finish_workflow_run(
                run_id,
                status="failed",
                result_summary=str(exc),
                duration_ms=total_duration_ms,
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
                if event.get("type") == "error" and not final_report:
                    final_report = f"本次 AIOps 诊断未完成：{event.get('message', '未知错误')}"

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
        chunk_size = 18
        for start in range(0, len(text), chunk_size):
            await asyncio.sleep(0.04)
            yield {"type": "content", "data": text[start:start + chunk_size]}


chat_service = ChatService()
