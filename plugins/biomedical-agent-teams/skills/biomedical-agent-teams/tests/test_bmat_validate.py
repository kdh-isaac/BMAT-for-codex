from __future__ import annotations

import subprocess
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = SKILL_ROOT / "scripts" / "bmat_validate.py"
FIXTURES = SKILL_ROOT / "tests" / "fixtures"


def run_validator(fixture_name: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "--bundle", str(FIXTURES / fixture_name)],
        text=True,
        capture_output=True,
        check=False,
    )


def combined_output(result: subprocess.CompletedProcess[str]) -> str:
    return result.stdout + result.stderr


def test_valid_bundle_passes() -> None:
    result = run_validator("valid_full_protocol_bundle")
    assert result.returncode == 0, combined_output(result)
    assert "ERROR" not in result.stdout


def test_full_protocol_without_independent_review_fails() -> None:
    result = run_validator("invalid_full_protocol_without_independent_review")
    assert result.returncode == 1
    assert "FULL_PROTOCOL_REQUIRES_INDEPENDENT_SURFACE" in combined_output(result)


def test_s3_block_blocks_high_confidence_claim() -> None:
    result = run_validator("invalid_s3_block_high_confidence")
    assert result.returncode == 1
    assert "S3_BLOCKS_HIGH_CONFIDENCE" in combined_output(result)


def test_missing_source_for_source_backed_claim_fails() -> None:
    result = run_validator("invalid_missing_source_for_claim")
    assert result.returncode == 1
    assert "SOURCE_BACKED_CLAIM_MISSING_SOURCE" in combined_output(result)


def test_final_wording_drift_fails() -> None:
    result = run_validator("invalid_final_wording_drift")
    assert result.returncode == 1
    assert "FINAL_WORDING_DRIFT" in combined_output(result)
