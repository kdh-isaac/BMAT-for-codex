from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
CASES = SKILL_ROOT / "evals" / "public_omics_benchmark_cases.jsonl"
SMOKE = SKILL_ROOT / "scripts" / "bmat_public_omics_benchmark_smoke.py"


def load_cases() -> list[dict]:
    return [json.loads(line) for line in CASES.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_public_omics_benchmark_cases_cover_improvement_plan_table() -> None:
    cases = load_cases()
    by_id = {case["case_id"]: case for case in cases}

    assert set(by_id) == {
        "TENX-PBMC10K-V31",
        "GSE115189",
        "GSE246624",
        "GSE224333",
        "GSE227412",
        "GSE196297",
    }
    assert {case["track"] for case in cases} >= {"tenx-gex", "tenx-cellplex", "bulk-rnaseq"}

    for case in cases:
        assert case["official_url"].startswith("https://")
        assert case["expected_checks"]
        overlay = case["manifest_overlay"]
        assert overlay["data_sources"][0]["raw_data_downloaded"] is False
        assert overlay["review_status"]["provenance_review"]


def test_public_omics_benchmark_smoke_runner_validates_representative_cases(tmp_path: Path) -> None:
    out = tmp_path / "public-omics-benchmark"
    result = subprocess.run(
        [
            sys.executable,
            str(SMOKE),
            "--out",
            str(out),
            "--case",
            "TENX-PBMC10K-V31",
            "--case",
            "GSE196297",
            "--validate",
            "--force",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    summary = json.loads((out / "public_omics_benchmark_summary.json").read_text(encoding="utf-8"))
    assert summary["case_count"] == 2
    assert summary["validated"] is True
    assert summary["raw_data_downloaded"] is False
    assert {row["status"] for row in summary["results"]} == {"pass"}
