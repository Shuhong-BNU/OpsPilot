import asyncio
from types import SimpleNamespace

from langchain_core.documents import Document

from app.services.chat_service import chat_service
from app.services.intent_service import INTENT_KNOWLEDGE_QA, IntentResult, intent_service
from app.services.retrieval_service import RetrievalTrace, retrieval_service


class FakeModel:
    async def ainvoke(self, messages):
        return SimpleNamespace(content="CPU 高负载通常先看进程、负载均值和上下文切换。")


def test_stream_chat_exposes_generation_timing(monkeypatch):
    monkeypatch.setattr(
        intent_service,
        "classify",
        lambda question: IntentResult(INTENT_KNOWLEDGE_QA, "命中文档规则", 0.99),
    )
    monkeypatch.setattr(
        retrieval_service,
        "hybrid_search",
        lambda question: (
            [Document(page_content="CPU 排查步骤", metadata={"_file_name": "cpu_high_usage.md"})],
            RetrievalTrace(
                query=question,
                dense_hits=6,
                sparse_hits=0,
                fusion_hits=3,
                rerank_hits=3,
                dense_latency_ms=120,
                sparse_latency_ms=0,
                rerank_latency_ms=15,
                final_sources=["cpu_high_usage.md"],
            ),
        ),
    )
    monkeypatch.setattr(chat_service, "_get_model", lambda: FakeModel())

    async def collect_events():
        events = []
        async for event in chat_service.stream_chat(
            "结合文档解释慢响应告警一般如何定位",
            "session-stream",
            {"id": 1, "role": "viewer"},
        ):
            events.append(event)
        return events

    events = asyncio.run(collect_events())

    trace_titles = [
        event["data"]["title"]
        for event in events
        if event.get("type") == "trace_step"
    ]
    complete = next(event for event in events if event.get("type") == "complete")
    timing = complete["data"]

    assert "LLM 调用开始" in trace_titles
    assert "首段输出" in trace_titles
    assert timing["retrieval_duration_ms"] == 135
    assert timing["llm_duration_ms"] >= 0
    assert timing["time_to_first_chunk_ms"] >= timing["llm_duration_ms"]
    assert timing["llm_started_at"]
    assert timing["first_chunk_at"]
