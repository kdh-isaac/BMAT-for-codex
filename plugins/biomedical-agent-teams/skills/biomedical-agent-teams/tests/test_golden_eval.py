from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
EVAL_SCRIPT = SKILL_ROOT / "evals" / "run_golden_eval.py"
MODEL_EVAL_SCRIPT = SKILL_ROOT / "evals" / "run_model_golden_eval.py"
SCHEMA_WRAPPER = SKILL_ROOT / "evals" / "validate_golden_eval_schema.py"
TASKS = SKILL_ROOT / "evals" / "golden_tasks.jsonl"
SAMPLE_OUTPUTS = SKILL_ROOT / "evals" / "sample_outputs.jsonl"
UTF8_BOM_BYTES = b"\xef\xbb\xbf"


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def prefix_utf8_bom(src: Path, dest: Path) -> None:
    dest.write_bytes(UTF8_BOM_BYTES + src.read_bytes())


def run_eval_with_tasks(tasks: Path, outputs: Path, *extra_args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(EVAL_SCRIPT),
            "--tasks",
            str(tasks),
            "--outputs",
            str(outputs),
            *extra_args,
        ],
        text=True,
        capture_output=True,
        check=False,
    )


def run_eval(outputs: Path, *extra_args: str) -> subprocess.CompletedProcess[str]:
    return run_eval_with_tasks(TASKS, outputs, *extra_args)


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def run_schema_wrapper_with_tasks(
    tasks: Path,
    outputs: Path | None = None,
    *extra_args: str,
) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        str(SCHEMA_WRAPPER),
        "--tasks",
        str(tasks),
        *extra_args,
    ]
    if outputs is not None:
        cmd.extend(["--outputs", str(outputs)])
    return subprocess.run(cmd, text=True, capture_output=True, check=False)


def run_schema_wrapper(outputs: Path | None = None, *extra_args: str) -> subprocess.CompletedProcess[str]:
    return run_schema_wrapper_with_tasks(TASKS, outputs, *extra_args)


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
    assert payload["task_count"] == 24
    assert payload["output_integrity_ok"] is True
    assert payload["gate"]["passed"] is True
    assert payload["missing_output_task_ids"] == []
    assert payload["unknown_output_task_ids"] == []
    assert payload["duplicate_output_task_ids"] == []
    assert payload["pmid_drift_detection_rate"] == 1.0
    assert payload["contradiction_detection_rate"] == 1.0
    assert payload["overclaim_downgrade_rate"] == 1.0
    assert payload["tournament_loop_detection_rate"] == 1.0
    assert payload["tournament_ranking_detection_rate"] == 1.0
    assert payload["codex_runtime_detection_rate"] == 1.0
    assert payload["semantic_scope_detection_rate"] == 1.0
    assert payload["expected_block_action_rate"] == 1.0


def test_model_golden_eval_sample_mode_generates_scoreable_outputs(tmp_path: Path) -> None:
    outputs = tmp_path / "model_sample_outputs.jsonl"
    result = subprocess.run(
        [
            sys.executable,
            str(MODEL_EVAL_SCRIPT),
            "--tasks",
            str(TASKS),
            "--alias",
            "evidence-audit-team",
            "--runtime",
            "codex",
            "--model",
            "sample-model",
            "--out",
            str(outputs),
            "--sample-mode",
            "--then-score",
            "--gate",
        ],
        env={**os.environ, "SHELL": "/bin/zsh"},
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    rows = read_jsonl(outputs)
    assert len(rows) == 24
    assert rows[0]["runtime"] == "codex"
    assert rows[0]["shell_family"] == "zsh"
    assert "prompt_hash" in rows[0]


def test_model_golden_eval_adapter_command_generates_scoreable_outputs(tmp_path: Path) -> None:
    adapter = tmp_path / "adapter.py"
    adapter.write_text(
        "\n".join(
            [
                "import json, sys",
                "task = json.loads(sys.stdin.read())",
                "expected = task.get('expected_detection', [])",
                "blocked = bool(task.get('expected_block', False))",
                "print(json.dumps({",
                "    'task_id': task['task_id'],",
                "    'detected_failure_modes': expected if blocked else [],",
                "    'blocked': blocked,",
                "    'downgraded': blocked,",
                "    'output_text': 'adapter smoke output',",
                "}))",
            ]
        ),
        encoding="utf-8",
    )
    outputs = tmp_path / "model_adapter_outputs.jsonl"
    result = subprocess.run(
        [
            sys.executable,
            str(MODEL_EVAL_SCRIPT),
            "--tasks",
            str(TASKS),
            "--alias",
            "evidence-audit-team",
            "--runtime",
            "codex",
            "--model",
            "adapter-smoke-model",
            "--out",
            str(outputs),
            "--adapter-command",
            f"{sys.executable} {adapter}",
            "--then-score",
            "--gate",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    rows = read_jsonl(outputs)
    assert len(rows) == 24
    assert rows[0]["model_name"] == "adapter-smoke-model"
    assert rows[0]["output_text"] == "adapter smoke output"


def test_model_golden_eval_requires_sample_or_adapter(tmp_path: Path) -> None:
    outputs = tmp_path / "model_outputs.jsonl"
    result = subprocess.run(
        [
            sys.executable,
            str(MODEL_EVAL_SCRIPT),
            "--tasks",
            str(TASKS),
            "--out",
            str(outputs),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "Use --sample-mode for CI or provide --adapter-command" in result.stderr


def test_model_golden_eval_rejects_malformed_adapter_output(tmp_path: Path) -> None:
    adapter = tmp_path / "bad_adapter.py"
    adapter.write_text("print('not json')\n", encoding="utf-8")
    outputs = tmp_path / "model_bad_adapter_outputs.jsonl"
    result = subprocess.run(
        [
            sys.executable,
            str(MODEL_EVAL_SCRIPT),
            "--tasks",
            str(TASKS),
            "--out",
            str(outputs),
            "--adapter-command",
            f"{sys.executable} {adapter}",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "adapter output is not valid JSON" in result.stderr


def test_schema_wrapper_accepts_sample_tasks_and_outputs() -> None:
    result = run_schema_wrapper(SAMPLE_OUTPUTS, "--json")

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_valid"] is True
    assert payload["schema_errors"] == []


def test_golden_eval_accepts_utf8_bom_prefixed_jsonl(tmp_path: Path) -> None:
    tasks = tmp_path / "golden_tasks.jsonl"
    outputs = tmp_path / "sample_outputs.jsonl"
    prefix_utf8_bom(TASKS, tasks)
    prefix_utf8_bom(SAMPLE_OUTPUTS, outputs)

    schema_result = run_schema_wrapper_with_tasks(tasks, outputs, "--json")
    eval_result = run_eval_with_tasks(tasks, outputs, "--strict", "--gate")

    assert schema_result.returncode == 0, schema_result.stdout + schema_result.stderr
    assert json.loads(schema_result.stdout)["schema_valid"] is True
    assert eval_result.returncode == 0, eval_result.stdout + eval_result.stderr
    assert json.loads(eval_result.stdout)["gate"]["passed"] is True


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


def test_gate_fails_when_tournament_loop_case_is_missed(tmp_path: Path) -> None:
    outputs = tmp_path / "outputs.jsonl"
    write_jsonl(outputs, sample_rows_with_task("GT-021", detected_failure_modes=[], downgraded=False))

    result = run_eval(outputs, "--strict", "--gate")

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["tournament_loop_detection_rate"] < 1.0
    assert "tournament_loop_detection_rate below threshold" in payload["gate"]["failures"]


def test_gate_fails_when_tournament_ranking_case_is_missed(tmp_path: Path) -> None:
    outputs = tmp_path / "outputs.jsonl"
    write_jsonl(outputs, sample_rows_with_task("GT-022", detected_failure_modes=[], downgraded=False))

    result = run_eval(outputs, "--strict", "--gate")

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["tournament_ranking_detection_rate"] < 1.0
    assert "tournament_ranking_detection_rate below threshold" in payload["gate"]["failures"]


def test_gate_fails_when_codex_runtime_case_is_missed(tmp_path: Path) -> None:
    outputs = tmp_path / "outputs.jsonl"
    write_jsonl(outputs, sample_rows_with_task("GT-023", detected_failure_modes=[], downgraded=False))

    result = run_eval(outputs, "--strict", "--gate")

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["codex_runtime_detection_rate"] < 1.0
    assert "codex_runtime_detection_rate below threshold" in payload["gate"]["failures"]


def test_gate_fails_when_semantic_scope_case_is_missed(tmp_path: Path) -> None:
    outputs = tmp_path / "outputs.jsonl"
    write_jsonl(outputs, sample_rows_with_task("GT-024", detected_failure_modes=[], downgraded=False))

    result = run_eval(outputs, "--strict", "--gate")

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["semantic_scope_detection_rate"] < 1.0
    assert "semantic_scope_detection_rate below threshold" in payload["gate"]["failures"]


def test_gate_fails_when_expected_block_case_detects_but_does_not_block_or_downgrade(tmp_path: Path) -> None:
    outputs = tmp_path / "outputs.jsonl"
    write_jsonl(
        outputs,
        sample_rows_with_task(
            "GT-021",
            detected_failure_modes=["iteration_budget_violation"],
            blocked=False,
            downgraded=False,
        ),
    )

    result = run_eval(outputs, "--strict", "--gate")

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["tournament_loop_detection_rate"] == 1.0
    assert payload["expected_block_action_rate"] < 1.0
    assert "expected_block_action_rate below threshold" in payload["gate"]["failures"]


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
