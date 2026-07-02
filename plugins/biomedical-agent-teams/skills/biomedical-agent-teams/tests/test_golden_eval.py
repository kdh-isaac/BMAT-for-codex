from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
EVAL_SCRIPT = SKILL_ROOT / "evals" / "run_golden_eval.py"
SCHEMA_WRAPPER = SKILL_ROOT / "evals" / "validate_golden_eval_schema.py"
TASKS = SKILL_ROOT / "evals" / "golden_tasks.jsonl"
SAMPLE_OUTPUTS = SKILL_ROOT / "evals" / "sample_outputs.jsonl"


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def run_eval(outputs: Path, *extra_args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(EVAL_SCRIPT),
            "--tasks",
            str(TASKS),
            "--outputs",
            str(outputs),
            *extra_args,
        ],
        text=True,
        capture_output=True,
        check=False,
    )


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def run_schema_wrapper(outputs: Path | None = None, *extra_args: str) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        str(SCHEMA_WRAPPER),
        "--tasks",
        str(TASKS),
        *extra_args,
    ]
    if outputs is not None:
        cmd.extend(["--outputs", str(outputs)])
    return subprocess.run(cmd, text=True, capture_output=True, check=False)


def sample_rows_with_task(task_id: str, **updates: object) -> list[dict[str, object]]:
    rows = read_jsonl(SAMPLE_OUTPUTS)
    for row in rows:
        if row["task_id"] == task_id:
            row.update(updates)
    return rows


def test_readme_sample_outputs_exist_and_strict_gate_passes() -> None:
    result = run_eval(SAMPLE_OUTPUTS, "--strict", "--gate")

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_valid"] is True
    assert payload["task_count"] == 23
    assert payload["output_integrity_ok"] is True
    assert payload["gate"]["passed"] is True
    assert payload["missing_output_task_ids"] == []
    assert payload["unknown_output_task_ids"] == []
    assert payload["duplicate_output_task_ids"] == []
    assert payload["pmid_drift_detection_rate"] == 1.0
    assert payload["contradiction_detection_rate"] == 1.0
    assert payload["overclaim_downgrade_rate"] == 1.0


def test_schema_wrapper_accepts_sample_tasks_and_outputs() -> None:
    result = run_schema_wrapper(SAMPLE_OUTPUTS, "--json")

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_valid"] is True
    assert payload["schema_errors"] == []


def test_schema_wrapper_flags_malformed_output_shape(tmp_path: Path) -> None:
    outputs = tmp_path / "outputs.jsonl"
    write_jsonl(
        outputs,
        [
            {
                "task_id": "GT-001",
                "detected_failure_modes": "fabricated_identifier",
                "blocked": "yes",
            },
        ],
    )

    result = run_schema_wrapper(outputs, "--json")

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["schema_valid"] is False
    assert any("detected_failure_modes" in error for error in payload["schema_errors"])
    assert any("blocked" in error for error in payload["schema_errors"])


def test_gate_fails_when_pmid_drift_case_is_missed(tmp_path: Path) -> None:
    outputs = tmp_path / "outputs.jsonl"
    write_jsonl(outputs, sample_rows_with_task("GT-002", detected_failure_modes=[], downgraded=False))

    result = run_eval(outputs, "--strict", "--gate")

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["pmid_drift_detection_rate"] < 1.0
    assert "pmid_drift_detection_rate below threshold" in payload["gate"]["failures"]


def test_gate_fails_when_contradiction_case_is_missed(tmp_path: Path) -> None:
    outputs = tmp_path / "outputs.jsonl"
    write_jsonl(outputs, sample_rows_with_task("GT-004", detected_failure_modes=[], downgraded=False))

    result = run_eval(outputs, "--strict", "--gate")

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["contradiction_detection_rate"] < 1.0
    assert "contradiction_detection_rate below threshold" in payload["gate"]["failures"]


def test_gate_fails_when_mixed_case_only_downgrades_overclaim_not_contradiction(tmp_path: Path) -> None:
    outputs = tmp_path / "outputs.jsonl"
    write_jsonl(
        outputs,
        sample_rows_with_task(
            "GT-005",
            detected_failure_modes=["overclaim"],
            downgraded=True,
        ),
    )

    result = run_eval(outputs, "--strict", "--gate")

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["contradiction_detection_rate"] < 1.0
    assert payload["overclaim_downgrade_rate"] == 1.0
    assert "contradiction_detection_rate below threshold" in payload["gate"]["failures"]


def test_gate_fails_when_pmid_drift_case_only_downgrades_overclaim(tmp_path: Path) -> None:
    outputs = tmp_path / "outputs.jsonl"
    write_jsonl(
        outputs,
        sample_rows_with_task(
            "GT-002",
            detected_failure_modes=["overclaim"],
            downgraded=True,
        ),
    )

    result = run_eval(outputs, "--strict", "--gate")

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["pmid_drift_detection_rate"] < 1.0
    assert "pmid_drift_detection_rate below threshold" in payload["gate"]["failures"]


def test_gate_fails_when_overclaim_case_is_neither_detected_nor_downgraded(tmp_path: Path) -> None:
    outputs = tmp_path / "outputs.jsonl"
    write_jsonl(outputs, sample_rows_with_task("GT-006", detected_failure_modes=[], downgraded=False))

    result = run_eval(outputs, "--strict", "--gate")

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["overclaim_downgrade_rate"] < 1.0
    assert "overclaim_downgrade_rate below threshold" in payload["gate"]["failures"]


def test_eval_reports_unknown_and_duplicate_output_task_ids(tmp_path: Path) -> None:
    outputs = tmp_path / "outputs.jsonl"
    write_jsonl(
        outputs,
        [
            {"task_id": "GT-001", "detected_failure_modes": ["fabricated_identifier"], "blocked": True},
            {"task_id": "GT-001", "detected_failure_modes": [], "blocked": False},
            {"task_id": "GT-999", "detected_failure_modes": [], "blocked": False},
        ],
    )

    result = run_eval(outputs)

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["unknown_output_task_ids"] == ["GT-999"]
    assert payload["duplicate_output_task_ids"] == ["GT-001"]
    assert "GT-002" in payload["missing_output_task_ids"]
    assert payload["output_integrity_ok"] is False


def test_eval_strict_fails_on_unknown_or_duplicate_outputs(tmp_path: Path) -> None:
    outputs = tmp_path / "outputs.jsonl"
    write_jsonl(
        outputs,
        [
            {"task_id": "GT-001", "detected_failure_modes": ["fabricated_identifier"], "blocked": True},
            {"task_id": "GT-999", "detected_failure_modes": [], "blocked": False},
        ],
    )

    result = run_eval(outputs, "--strict")

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["unknown_output_task_ids"] == ["GT-999"]
    assert payload["output_integrity_ok"] is False


def test_eval_strict_fails_on_missing_outputs(tmp_path: Path) -> None:
    outputs = tmp_path / "outputs.jsonl"
    write_jsonl(
        outputs,
        [
            {"task_id": "GT-001", "detected_failure_modes": ["fabricated_identifier"], "blocked": True},
            {"task_id": "GT-021", "detected_failure_modes": [], "blocked": False},
            {"task_id": "GT-022", "detected_failure_modes": [], "blocked": False},
        ],
    )

    result = run_eval(outputs, "--strict")

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert "GT-002" in payload["missing_output_task_ids"]
    assert payload["output_integrity_ok"] is False


def test_eval_false_positive_rate_has_negative_control_denominator(tmp_path: Path) -> None:
    outputs = tmp_path / "outputs.jsonl"
    write_jsonl(
        outputs,
        [
            {"task_id": "GT-019", "detected_failure_modes": [], "blocked": True, "word_count": 10},
            {"task_id": "GT-020", "detected_failure_modes": [], "blocked": False, "word_count": 20},
        ],
    )

    result = run_eval(outputs)

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["false_positive_block_rate"] == 0.5
    assert payload["output_integrity_ok"] is False
    assert "GT-001" in payload["missing_output_task_ids"]
