"""Run a lightweight OpsPilot RAG retrieval evaluation.

This runner evaluates the real retrieval stack exposed by
app.services.retrieval_service.hybrid_search:

Milvus dense retrieval + SQLite FTS5 sparse retrieval + RRF + existing rerank.

It does not evaluate answer generation, groundedness, AIOps, MCP tools, or LLM
judge behavior.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = REPO_ROOT / "evals" / "datasets" / "opspilot_rag_cases.jsonl"
DEFAULT_RESULTS = REPO_ROOT / "evals" / "results" / "opspilot_rag_eval_results.jsonl"
DEFAULT_REPORT = REPO_ROOT / "evals" / "reports" / "opspilot_rag_eval_report.md"

STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_INFRA_BLOCKED = "INFRA_BLOCKED"
MODE_HYBRID = "Hybrid Retrieval"
RUNNER_MODE_MEASUREMENT = "measurement"
RUNNER_MODE_CI = "ci"


@dataclass
class InfraCheck:
    name: str
    status: str
    detail: str


@dataclass
class CaseResult:
    id: str
    question: str
    relevant_sources: list[str]
    tags: list[str]
    status: str
    hit_at_3: int
    reciprocal_rank: float
    first_relevant_rank: int | None
    top3_sources: list[str]
    wall_time_ms: int
    dense_latency_ms: int | None = None
    sparse_latency_ms: int | None = None
    rerank_latency_ms: int | None = None
    trace: dict[str, Any] | None = None
    results: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None


def load_cases(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            case = json.loads(stripped)
            if not case.get("id"):
                raise ValueError(f"{path}:{line_number} missing id")
            if not case.get("question"):
                raise ValueError(f"{path}:{line_number} missing question")
            relevant_sources = case.get("relevant_sources")
            if not isinstance(relevant_sources, list) or not relevant_sources:
                raise ValueError(f"{path}:{line_number} missing relevant_sources")
            cases.append(case)
    return cases


def read_aiops_sources() -> set[str]:
    docs_dir = REPO_ROOT / "aiops-docs"
    return {path.name for path in docs_dir.glob("*.md")}


def validate_cases(cases: list[dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    existing_sources = read_aiops_sources()
    for case in cases:
        for source in case["relevant_sources"]:
            if source not in existing_sources:
                warnings.append(
                    f"Case {case['id']} references missing source {source!r}; "
                    f"known sources: {sorted(existing_sources)}"
                )
    return warnings


def git_output(args: list[str]) -> str:
    try:
        return subprocess.check_output(
            ["git", *args],
            cwd=REPO_ROOT,
            text=True,
            stderr=subprocess.STDOUT,
        ).strip()
    except Exception as exc:  # pragma: no cover - diagnostic only
        return f"unavailable: {exc}"


def tcp_port_open(host: str, port: int, timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def inspect_environment() -> tuple[dict[str, Any], list[InfraCheck], Any]:
    """Import app modules after basic path setup and collect config checks."""
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))

    from app.config import config
    from app.services.database_service import database_service
    from app.services.retrieval_service import retrieval_service

    api_key = config.dashscope_api_key
    api_key_configured = bool(api_key and api_key not in {"your-api-key", "your-api-key-here"})
    milvus_reachable = tcp_port_open(config.milvus_host, int(config.milvus_port))

    try:
        chunk_row = database_service.fetch_one("SELECT COUNT(*) AS count FROM document_chunks")
        sqlite_chunk_count = int(chunk_row["count"]) if chunk_row else 0
        sqlite_status = STATUS_PASS if sqlite_chunk_count > 0 else STATUS_INFRA_BLOCKED
        sqlite_detail = (
            f"SQLite document_chunks contains {sqlite_chunk_count} chunks"
            if sqlite_chunk_count > 0
            else "SQLite document_chunks is empty; run indexing before formal hybrid eval"
        )
    except Exception as exc:
        sqlite_chunk_count = 0
        sqlite_status = STATUS_INFRA_BLOCKED
        sqlite_detail = f"Could not inspect SQLite document_chunks: {type(exc).__name__}: {exc}"

    checks = [
        InfraCheck(
            "dashscope_api_key",
            STATUS_PASS if api_key_configured else STATUS_INFRA_BLOCKED,
            "DASHSCOPE_API_KEY is configured" if api_key_configured else "DASHSCOPE_API_KEY is empty or placeholder",
        ),
        InfraCheck(
            "milvus_tcp",
            STATUS_PASS if milvus_reachable else STATUS_INFRA_BLOCKED,
            f"{config.milvus_host}:{config.milvus_port} is reachable"
            if milvus_reachable
            else f"{config.milvus_host}:{config.milvus_port} is not reachable",
        ),
        InfraCheck("sqlite_chunks", sqlite_status, sqlite_detail),
    ]

    env = {
        "commit": git_output(["rev-parse", "HEAD"]),
        "branch": git_output(["branch", "--show-current"]),
        "status": git_output(["status", "-sb"]),
        "remote": git_output(["remote", "-v"]),
        "evaluation_mode": MODE_HYBRID,
        "python": sys.version.split()[0],
        "dataset_sources": sorted(read_aiops_sources()),
        "retrieval_config": {
            "dense_top_k": config.dense_top_k,
            "sparse_top_k": config.sparse_top_k,
            "hybrid_top_k": config.hybrid_top_k,
            "rerank_top_k": config.rerank_top_k,
            "milvus_host": config.milvus_host,
            "milvus_port": config.milvus_port,
            "embedding_model": config.dashscope_embedding_model,
            "sqlite_chunk_count": sqlite_chunk_count,
        },
    }
    return env, checks, retrieval_service


def critical_infra_blocked(checks: list[InfraCheck]) -> str | None:
    critical_names = {"dashscope_api_key", "milvus_tcp", "sqlite_chunks", "dataset_sources"}
    blocked = [
        f"{check.name}: {check.detail}"
        for check in checks
        if check.name in critical_names and check.status != STATUS_PASS
    ]
    return "; ".join(blocked) if blocked else None


def blocked_case_result(case: dict[str, Any], reason: str) -> CaseResult:
    return CaseResult(
        id=case["id"],
        question=case["question"],
        relevant_sources=list(case["relevant_sources"]),
        tags=list(case.get("tags", [])),
        status=STATUS_INFRA_BLOCKED,
        hit_at_3=0,
        reciprocal_rank=0.0,
        first_relevant_rank=None,
        top3_sources=[],
        wall_time_ms=0,
        error=reason,
    )


def source_name(metadata: dict[str, Any]) -> str:
    source = metadata.get("_file_name")
    if source:
        return str(source)
    raw_source = metadata.get("_source") or metadata.get("source")
    if raw_source:
        return Path(str(raw_source)).name
    return "unknown"


def first_relevant_rank(results: list[dict[str, Any]], relevant_sources: set[str]) -> int | None:
    for item in results:
        if item["source"] in relevant_sources:
            return int(item["rank"])
    return None


def run_case(case: dict[str, Any], retrieval_service: Any) -> CaseResult:
    started = time.perf_counter()
    try:
        docs, trace = retrieval_service.hybrid_search(case["question"])
        wall_time_ms = int((time.perf_counter() - started) * 1000)
        trace_dict = trace.to_dict() if hasattr(trace, "to_dict") else dict(trace)

        ranked_results: list[dict[str, Any]] = []
        for rank, doc in enumerate(docs, start=1):
            metadata = dict(getattr(doc, "metadata", {}) or {})
            ranked_results.append(
                {
                    "rank": rank,
                    "source": source_name(metadata),
                    "chunk_id": metadata.get("_chunk_id"),
                    "metadata": metadata,
                    "content_preview": getattr(doc, "page_content", "")[:240],
                }
            )

        relevant = set(case["relevant_sources"])
        rank = first_relevant_rank(ranked_results, relevant)
        hit = 1 if rank is not None and rank <= 3 else 0
        reciprocal = 0.0 if rank is None else 1.0 / rank
        return CaseResult(
            id=case["id"],
            question=case["question"],
            relevant_sources=list(case["relevant_sources"]),
            tags=list(case.get("tags", [])),
            status=STATUS_PASS if hit else STATUS_FAIL,
            hit_at_3=hit,
            reciprocal_rank=reciprocal,
            first_relevant_rank=rank,
            top3_sources=[item["source"] for item in ranked_results[:3]],
            wall_time_ms=wall_time_ms,
            dense_latency_ms=trace_dict.get("dense_latency_ms"),
            sparse_latency_ms=trace_dict.get("sparse_latency_ms"),
            rerank_latency_ms=trace_dict.get("rerank_latency_ms"),
            trace=trace_dict,
            results=ranked_results,
        )
    except Exception as exc:
        wall_time_ms = int((time.perf_counter() - started) * 1000)
        return CaseResult(
            id=case["id"],
            question=case["question"],
            relevant_sources=list(case["relevant_sources"]),
            tags=list(case.get("tags", [])),
            status=STATUS_INFRA_BLOCKED,
            hit_at_3=0,
            reciprocal_rank=0.0,
            first_relevant_rank=None,
            top3_sources=[],
            wall_time_ms=wall_time_ms,
            error=f"{type(exc).__name__}: {exc}",
        )


def average(values: list[int | float | None]) -> float:
    numeric = [float(value) for value in values if value is not None]
    return sum(numeric) / len(numeric) if numeric else 0.0


def determine_evaluation_status(results: list[CaseResult]) -> str:
    if any(result.status == STATUS_INFRA_BLOCKED for result in results):
        return STATUS_INFRA_BLOCKED
    if any(result.status == STATUS_FAIL for result in results):
        return STATUS_FAIL
    return STATUS_PASS


def determine_exit_code(results: list[CaseResult], ci_mode: bool = False) -> int:
    evaluation_status = determine_evaluation_status(results)
    if evaluation_status == STATUS_INFRA_BLOCKED:
        return 2
    if ci_mode and evaluation_status == STATUS_FAIL:
        return 1
    return 0


def write_jsonl(path: Path, env: dict[str, Any], checks: list[InfraCheck], results: list[CaseResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "type": "environment",
                    "environment": env,
                    "infrastructure_checks": [asdict(check) for check in checks],
                },
                ensure_ascii=False,
            )
            + "\n"
        )
        for result in results:
            handle.write(json.dumps({"type": "case_result", **asdict(result)}, ensure_ascii=False) + "\n")


def markdown_table_row(values: list[Any]) -> str:
    return "| " + " | ".join(str(value) for value in values) + " |"


def build_report(
    env: dict[str, Any],
    checks: list[InfraCheck],
    results: list[CaseResult],
    dataset_path: Path,
    runner_mode: str = RUNNER_MODE_MEASUREMENT,
) -> str:
    total = len(results)
    infra_blocked = [result for result in results if result.status == STATUS_INFRA_BLOCKED]
    scorable = [result for result in results if result.status != STATUS_INFRA_BLOCKED]
    evaluation_status = determine_evaluation_status(results)
    hit_at_3 = average([result.hit_at_3 for result in scorable])
    mrr = average([result.reciprocal_rank for result in scorable])
    avg_wall = average([result.wall_time_ms for result in scorable])

    lines = [
        "# OpsPilot RAG Retrieval Eval Report",
        "",
        "## Environment",
        "",
        f"- Commit: `{env['commit']}`",
        f"- Branch: `{env['branch']}`",
        f"- Evaluation Mode: {env['evaluation_mode']}",
        f"- Runner Mode: {runner_mode}",
        f"- Evaluation Status: {evaluation_status}",
        f"- Dataset: `{dataset_path.relative_to(REPO_ROOT)}`",
        f"- Dataset Size: {total}",
        f"- Python: {env['python']}",
        f"- Git Status: `{env['status']}`",
        f"- Known Sources: {', '.join(env['dataset_sources'])}",
        f"- Retrieval Configuration: `{json.dumps(env['retrieval_config'], ensure_ascii=False)}`",
        "",
        "## Summary",
        "",
        f"- Total Cases: {total}",
        f"- Scorable Cases: {len(scorable)}",
        f"- Infrastructure Blocked Cases: {len(infra_blocked)}",
        f"- Hit@3: {hit_at_3:.3f}",
        f"- MRR: {mrr:.3f}",
        f"- Average Wall-Clock Latency: {avg_wall:.1f} ms",
        "",
        "## Stage Latency",
        "",
        f"- Dense Average: {average([result.dense_latency_ms for result in scorable]):.1f} ms",
        f"- Sparse Average: {average([result.sparse_latency_ms for result in scorable]):.1f} ms",
        f"- Rerank Average: {average([result.rerank_latency_ms for result in scorable]):.1f} ms",
        "",
        "## Case Results",
        "",
        markdown_table_row(["id", "pass", "first relevant rank", "top3 sources", "wall time"]),
        markdown_table_row(["---", "---", "---", "---", "---"]),
    ]

    for result in results:
        passed = "yes" if result.status == STATUS_PASS else "no"
        if result.status == STATUS_INFRA_BLOCKED:
            passed = "infra_blocked"
        lines.append(
            markdown_table_row(
                [
                    result.id,
                    passed,
                    result.first_relevant_rank if result.first_relevant_rank is not None else "-",
                    ", ".join(result.top3_sources) if result.top3_sources else "-",
                    f"{result.wall_time_ms} ms",
                ]
            )
        )

    lines.extend(["", "## Failure Analysis", ""])
    failures = [result for result in results if result.status == STATUS_FAIL]
    if not failures:
        lines.append("- No retrieval misses among scorable cases.")
    else:
        for result in failures:
            lines.append(
                f"- {result.id}: expected {result.relevant_sources}; "
                f"actual top3 {result.top3_sources or ['<none>']}; "
                "possible reason: relevant source not ranked in top 3 by current hybrid retrieval."
            )

    if infra_blocked:
        lines.extend(["", "## Infrastructure Blocked Cases", ""])
        for result in infra_blocked:
            lines.append(f"- {result.id}: {result.error}")

    lines.extend(["", "## Infrastructure Warnings", ""])
    warning_lines = [check for check in checks if check.status != STATUS_PASS]
    if not warning_lines:
        lines.append("- None.")
    else:
        for check in warning_lines:
            lines.append(f"- {check.name}: {check.status} - {check.detail}")

    lines.extend(
        [
            "",
            "## Metric Definitions",
            "",
            "- Hit@3: case-level hit. A case scores 1 when at least one relevant source appears in top 3, otherwise 0.",
            "- MRR: reciprocal rank of the first relevant source; 0 when no relevant source is retrieved.",
            "- Wall-clock latency: runner-measured elapsed time around `retrieval_service.hybrid_search`.",
            "- Stage latency: dense, sparse, and rerank latency reported by `RetrievalTrace`.",
            "",
        ]
    )
    return "\n".join(lines)


def write_report(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run OpsPilot RAG retrieval eval MVP.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument(
        "--ci",
        action="store_true",
        help="Return exit code 1 for retrieval misses while preserving measurement outputs.",
    )
    args = parser.parse_args()
    runner_mode = RUNNER_MODE_CI if args.ci else RUNNER_MODE_MEASUREMENT

    cases = load_cases(args.dataset)
    case_warnings = validate_cases(cases)
    env, checks, retrieval_service = inspect_environment()
    checks.extend(InfraCheck("dataset_sources", STATUS_INFRA_BLOCKED, warning) for warning in case_warnings)

    blocked_reason = critical_infra_blocked(checks)
    if blocked_reason:
        results = [blocked_case_result(case, blocked_reason) for case in cases]
    else:
        results = [run_case(case, retrieval_service) for case in cases]
    write_jsonl(args.results, env, checks, results)
    write_report(args.report, build_report(env, checks, results, args.dataset, runner_mode))

    total = len(results)
    blocked = sum(1 for result in results if result.status == STATUS_INFRA_BLOCKED)
    scorable = [result for result in results if result.status != STATUS_INFRA_BLOCKED]
    print(f"Evaluation Mode: {MODE_HYBRID}")
    print(f"Runner Mode: {runner_mode}")
    print(f"Evaluation Status: {determine_evaluation_status(results)}")
    print(f"Total Cases: {total}")
    print(f"Infrastructure Blocked Cases: {blocked}")
    print(f"Hit@3: {average([result.hit_at_3 for result in scorable]):.3f}")
    print(f"MRR: {average([result.reciprocal_rank for result in scorable]):.3f}")
    print(f"Average Wall-Clock Latency: {average([result.wall_time_ms for result in scorable]):.1f} ms")
    print(f"Results: {args.results}")
    print(f"Report: {args.report}")

    return determine_exit_code(results, ci_mode=args.ci)


if __name__ == "__main__":
    raise SystemExit(main())
