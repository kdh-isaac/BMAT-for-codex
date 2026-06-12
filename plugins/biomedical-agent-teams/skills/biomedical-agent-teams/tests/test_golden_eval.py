from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
EVAL_SCRIPT = SKILL_ROOT / "evals" / "run_golden_eval.py"
TASKS = SKILL_ROOT / "evals" / "golden_tasks.jsonl"


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
            {"task_id": "GT-021", "detected_failure_modes": [], "blocked": True, "word_count": 10},
            {"task_id": "GT-022", "detected_failure_modes": [], "blocked": False, "word_count": 20},
        ],
    )

    result = run_eval(outputs)

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["false_positive_block_rate"] == 0.5
    assert payload["output_integrity_ok"] is False
    assert "GT-001" in payload["missing_output_task_ids"]
