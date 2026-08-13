"""Run deterministic OpsPilot retrieval evaluation against the v2 tool path."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_SRC = REPO_ROOT / "apps" / "backend" / "src"
DEFAULT_DATASET = REPO_ROOT / "evals" / "datasets" / "opspilot_rag_cases.jsonl"
DEFAULT_CORPUS = REPO_ROOT / "evals" / "corpus"
DEFAULT_RESULTS = REPO_ROOT / "evals" / "results" / "opspilot_rag_eval_v2_results.jsonl"
DEFAULT_REPORT = REPO_ROOT / "evals" / "reports" / "opspilot_rag_eval_v2_report.md"

if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

from opspilot.evaluation import (  # noqa: E402
    OfflineEvaluationCase,
    build_offline_retrieval_tool,
    evaluate_offline_cases,
    load_markdown_corpus,
)


def load_cases(path: Path) -> list[OfflineEvaluationCase]:
    """Read and validate the versioned JSONL retrieval cases."""
    cases: list[OfflineEvaluationCase] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        value = json.loads(line)
        try:
            cases.append(
                OfflineEvaluationCase(
                    id=str(value["id"]),
                    question=str(value["question"]),
                    relevant_sources=tuple(str(item) for item in value["relevant_sources"]),
                    tags=tuple(str(item) for item in value.get("tags", [])),
                )
            )
        except (KeyError, TypeError) as exc:
            raise ValueError(f"{path}:{line_number} has an invalid evaluation case") from exc
    if not cases:
        raise ValueError(f"{path} has no evaluation cases")
    return cases


def git_output(args: list[str]) -> str:
    """Read Git metadata without allowing metadata failures to block evaluation."""
    try:
        return subprocess.check_output(
            ["git", *args], cwd=REPO_ROOT, text=True, stderr=subprocess.STDOUT
        ).strip()
    except subprocess.CalledProcessError:
        return "unavailable"


def average(values: list[float | int]) -> float:
    return sum(float(value) for value in values) / len(values) if values else 0.0


def build_report(
    *,
    dataset: Path,
    corpus: Path,
    rows: list[dict[str, Any]],
) -> str:
    """Build a human-readable report from the same evidence written to JSONL."""
    hit_at_1 = average([row["hit_at_1"] for row in rows])
    hit_at_3 = average([row["hit_at_3"] for row in rows])
    mrr = average([row["reciprocal_rank"] for row in rows])
    recall_at_3 = average([row["recall_at_3"] for row in rows])
    lines = [
        "# OpsPilot Retrieval Eval v2 Report",
        "",
        "## Scope",
        "",
        "- Mode: deterministic offline regression evaluation.",
        "- Production code exercised: `KnowledgeRetrievalTool`, scope filtering, BM25L, RRF,",
        "  rerank result shaping, and stage-rank evidence.",
        "- Replaced dependencies: Milvus, remote embedding, and remote Qwen rerank",
        "  use deterministic local adapters.",
        "- This is not a latency or quality claim about the production Milvus/Qwen deployment.",
        "",
        "## Inputs",
        "",
        f"- Commit: `{git_output(['rev-parse', 'HEAD'])}`",
        f"- Branch: `{git_output(['branch', '--show-current'])}`",
        f"- Dataset: `{dataset.relative_to(REPO_ROOT)}`",
        f"- Corpus: `{corpus.relative_to(REPO_ROOT)}`",
        f"- Cases: {len(rows)}",
        "",
        "## Metrics",
        "",
        f"- Hit@1: {hit_at_1:.3f}",
        f"- Hit@3: {hit_at_3:.3f}",
        f"- MRR: {mrr:.3f}",
        f"- Recall@3: {recall_at_3:.3f}",
        "",
        "## Case Results",
        "",
        "| id | Hit@1 | Hit@3 | first relevant rank | Recall@3 | top sources |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        rank = row["first_relevant_rank"] or "-"
        lines.append(
            "| {id} | {hit_at_1} | {hit_at_3} | {rank} | {recall_at_3:.3f} | {sources} |".format(
                id=row["id"],
                hit_at_1=row["hit_at_1"],
                hit_at_3=row["hit_at_3"],
                rank=rank,
                recall_at_3=row["recall_at_3"],
                sources=", ".join(row["top_sources"]),
            )
        )
    lines.extend(["", "## Stage Evidence", ""])
    for row in rows:
        lines.append(f"### {row['id']}")
        for evidence in row["stage_evidence"]:
            lines.append(
                "- `{source}`: vector={vector_rank}, bm25={bm25_rank}, "
                "rrf={rrf_score:.6f}, rerank={rerank_rank}".format(**evidence)
            )
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run OpsPilot retrieval evaluation v2.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    cases = load_cases(args.dataset)
    chunks = load_markdown_corpus(args.corpus)
    expected_sources = {chunk.source for chunk in chunks}
    missing = sorted(
        source
        for case in cases
        for source in case.relevant_sources
        if source not in expected_sources
    )
    if missing:
        raise ValueError(f"Dataset references unknown corpus source(s): {', '.join(missing)}")
    results = evaluate_offline_cases(build_offline_retrieval_tool(chunks), cases)
    rows = [
        {
            "id": result.case.id,
            "question": result.case.question,
            "relevant_sources": result.case.relevant_sources,
            "tags": result.case.tags,
            "top_sources": result.sources,
            "first_relevant_rank": result.first_relevant_rank,
            "hit_at_1": result.hit_at_1,
            "hit_at_3": result.hit_at_3,
            "reciprocal_rank": result.reciprocal_rank,
            "recall_at_3": result.recall_at_3,
            "stage_evidence": result.stage_evidence,
        }
        for result in results
    ]
    args.results.parent.mkdir(parents=True, exist_ok=True)
    args.results.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        build_report(dataset=args.dataset, corpus=args.corpus, rows=rows), encoding="utf-8"
    )
    print(f"Hit@1: {average([row['hit_at_1'] for row in rows]):.3f}")
    print(f"Hit@3: {average([row['hit_at_3'] for row in rows]):.3f}")
    print(f"MRR: {average([row['reciprocal_rank'] for row in rows]):.3f}")
    print(f"Recall@3: {average([row['recall_at_3'] for row in rows]):.3f}")
    return 0 if all(row["hit_at_3"] for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
