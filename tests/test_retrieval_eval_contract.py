import sys

import evals.run_retrieval_eval as runner
from evals.run_retrieval_eval import (
    CaseResult,
    DEFAULT_DATASET,
    RUNNER_MODE_CI,
    RUNNER_MODE_MEASUREMENT,
    STATUS_FAIL,
    STATUS_INFRA_BLOCKED,
    STATUS_PASS,
    build_report,
    determine_evaluation_status,
    determine_exit_code,
)


def make_result(status: str) -> CaseResult:
    hit = 1 if status == STATUS_PASS else 0
    return CaseResult(
        id=f"case_{status.lower()}",
        question="CPU 使用率持续超过 80% 应该如何排查？",
        relevant_sources=["cpu_high_usage.md"],
        tags=["cpu"],
        status=status,
        hit_at_3=hit,
        reciprocal_rank=1.0 if hit else 0.0,
        first_relevant_rank=1 if hit else None,
        top3_sources=["cpu_high_usage.md"] if hit else ["disk_high_usage.md"],
        wall_time_ms=100,
    )


def make_results(pass_count: int, fail_count: int, infra_count: int) -> list[CaseResult]:
    return (
        [make_result(STATUS_PASS) for _ in range(pass_count)]
        + [make_result(STATUS_FAIL) for _ in range(fail_count)]
        + [make_result(STATUS_INFRA_BLOCKED) for _ in range(infra_count)]
    )


def test_measurement_all_pass_reports_pass_and_exits_zero():
    results = make_results(pass_count=10, fail_count=0, infra_count=0)

    assert determine_evaluation_status(results) == STATUS_PASS
    assert determine_exit_code(results, ci_mode=False) == 0


def test_measurement_capability_fail_reports_fail_and_exits_zero():
    results = make_results(pass_count=9, fail_count=1, infra_count=0)

    assert determine_evaluation_status(results) == STATUS_FAIL
    assert determine_exit_code(results, ci_mode=False) == 0


def test_measurement_infra_blocked_reports_blocked_and_exits_two():
    results = make_results(pass_count=9, fail_count=0, infra_count=1)

    assert determine_evaluation_status(results) == STATUS_INFRA_BLOCKED
    assert determine_exit_code(results, ci_mode=False) == 2


def test_ci_all_pass_reports_pass_and_exits_zero():
    results = make_results(pass_count=10, fail_count=0, infra_count=0)

    assert determine_evaluation_status(results) == STATUS_PASS
    assert determine_exit_code(results, ci_mode=True) == 0


def test_ci_capability_fail_reports_fail_and_exits_one():
    results = make_results(pass_count=9, fail_count=1, infra_count=0)

    assert determine_evaluation_status(results) == STATUS_FAIL
    assert determine_exit_code(results, ci_mode=True) == 1


def test_ci_infra_blocked_reports_blocked_and_exits_two():
    results = make_results(pass_count=9, fail_count=1, infra_count=1)

    assert determine_evaluation_status(results) == STATUS_INFRA_BLOCKED
    assert determine_exit_code(results, ci_mode=True) == 2


def test_mode_does_not_change_capability_status():
    results = make_results(pass_count=9, fail_count=1, infra_count=0)

    assert determine_evaluation_status(results) == STATUS_FAIL
    assert determine_exit_code(results, ci_mode=False) == 0
    assert determine_exit_code(results, ci_mode=True) == 1


def test_report_includes_runner_mode_and_fail_status():
    env = {
        "commit": "test",
        "branch": "test",
        "evaluation_mode": "Hybrid Retrieval",
        "python": "3.x",
        "status": "clean",
        "dataset_sources": ["cpu_high_usage.md"],
        "retrieval_config": {},
    }
    results = make_results(pass_count=9, fail_count=1, infra_count=0)

    report = build_report(env, [], results, DEFAULT_DATASET, RUNNER_MODE_CI)

    assert "- Runner Mode: ci" in report
    assert "- Evaluation Status: FAIL" in report


def test_report_defaults_to_measurement_mode():
    env = {
        "commit": "test",
        "branch": "test",
        "evaluation_mode": "Hybrid Retrieval",
        "python": "3.x",
        "status": "clean",
        "dataset_sources": ["cpu_high_usage.md"],
        "retrieval_config": {},
    }
    results = make_results(pass_count=10, fail_count=0, infra_count=0)

    report = build_report(env, [], results, DEFAULT_DATASET, RUNNER_MODE_MEASUREMENT)

    assert "- Runner Mode: measurement" in report
    assert "- Evaluation Status: PASS" in report


def test_main_ci_flag_returns_one_for_capability_fail(monkeypatch, tmp_path):
    case = {
        "id": "rag_cpu_001",
        "question": "CPU 使用率持续超过 80% 应该如何排查？",
        "relevant_sources": ["cpu_high_usage.md"],
        "tags": ["cpu"],
    }
    env = {
        "commit": "test",
        "branch": "test",
        "evaluation_mode": "Hybrid Retrieval",
        "python": "3.x",
        "status": "clean",
        "dataset_sources": ["cpu_high_usage.md"],
        "retrieval_config": {},
    }
    results_path = tmp_path / "results.jsonl"
    report_path = tmp_path / "report.md"

    monkeypatch.setattr(runner, "load_cases", lambda path: [case])
    monkeypatch.setattr(runner, "validate_cases", lambda cases: [])
    monkeypatch.setattr(runner, "inspect_environment", lambda: (env, [], object()))
    monkeypatch.setattr(runner, "run_case", lambda case, retrieval_service: make_result(STATUS_FAIL))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_retrieval_eval.py",
            "--ci",
            "--dataset",
            str(DEFAULT_DATASET),
            "--results",
            str(results_path),
            "--report",
            str(report_path),
        ],
    )

    assert runner.main() == 1
    assert "- Runner Mode: ci" in report_path.read_text(encoding="utf-8")
    assert "- Evaluation Status: FAIL" in report_path.read_text(encoding="utf-8")
