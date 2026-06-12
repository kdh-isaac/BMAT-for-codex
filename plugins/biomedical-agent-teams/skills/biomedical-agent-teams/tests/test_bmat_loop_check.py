from __future__ import annotations

import subprocess
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
LOOP_CHECK = SKILL_ROOT / "scripts" / "bmat_loop_check.py"
FIXTURES = SKILL_ROOT / "tests" / "fixtures"


def run_loop_check(fixture_name: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(LOOP_CHECK),
            "--loop-state",
            str(FIXTURES / fixture_name / "loop_state.json"),
        ],
        text=True,
        capture_output=True,
        check=False,
    )


def combined_output(result: subprocess.CompletedProcess[str]) -> str:
    return result.stdout + result.stderr


def test_valid_loop_state_passes() -> None:
    result = run_loop_check("loop_check_valid")
    assert result.returncode == 0, combined_output(result)
    assert "ERROR" not in result.stdout


def test_private_external_loop_requires_human_gate() -> None:
    result = run_loop_check("loop_check_invalid_private_external")
    assert result.returncode == 1
    assert "PRIVATE_CONTEXT_REQUIRES_HUMAN_GATE" in combined_output(result)


def test_pending_source_delta_blocks_release() -> None:
    result = run_loop_check("loop_check_invalid_stale_source_delta")
    assert result.returncode == 1
    assert "SOURCE_DELTA_PENDING" in combined_output(result)


def test_open_reviewer_objection_blocks_release() -> None:
    result = run_loop_check("loop_check_invalid_unhandled_objection")
    assert result.returncode == 1
    assert "OPEN_REVIEWER_OBJECTION" in combined_output(result)


def test_disallowed_connector_blocks_loop() -> None:
    result = run_loop_check("loop_check_invalid_connector")
    assert result.returncode == 1
    assert "CONNECTOR_NOT_ALLOWED_FOR_LOOP" in combined_output(result)


def test_disallowed_release_artifact_blocks_loop() -> None:
    result = run_loop_check("loop_check_invalid_release_artifact")
    assert result.returncode == 1
    assert "LOOP_ARTIFACT_TYPE_NOT_ALLOWED" in combined_output(result)
