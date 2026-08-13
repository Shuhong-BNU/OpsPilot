from __future__ import annotations

from pathlib import Path

from opspilot.evaluation import (
    OfflineEvaluationCase,
    build_offline_retrieval_tool,
    evaluate_offline_cases,
    load_markdown_corpus,
)


def test_offline_evaluation_runs_production_retrieval_tool_with_stage_evidence(
    tmp_path: Path,
) -> None:
    (tmp_path / "cpu.md").write_text("CPU usage exceeds 80 percent. Restart the worker.")
    (tmp_path / "memory.md").write_text("Memory OOM and garbage collection troubleshooting.")
    tool = build_offline_retrieval_tool(load_markdown_corpus(tmp_path))

    result = evaluate_offline_cases(
        tool,
        [
            OfflineEvaluationCase(
                id="cpu-1",
                question="How should I handle CPU usage over 80 percent?",
                relevant_sources=("cpu.md",),
            )
        ],
    )[0]

    assert result.hit_at_1 == 1
    assert result.hit_at_3 == 1
    assert result.recall_at_3 == 1.0
    assert result.stage_evidence[0]["vector_rank"] == 1
    assert result.stage_evidence[0]["bm25_rank"] == 1
    assert result.stage_evidence[0]["rerank_rank"] == 1
