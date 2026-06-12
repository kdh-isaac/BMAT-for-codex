from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


SKILL_ROOT = Path(__file__).resolve().parents[1]
LOOP_CHECK = SKILL_ROOT / "scripts" / "bmat_loop_check.py"


def base_loop_state(loop_type: str = "weekly_literature_watch") -> dict[str, object]:
    return {
        "loop_id": "loop-edge-test",
        "loop_name": "Loop edge test",
        "loop_type": loop_type,
        "plugin_version": "0.4.1",
        "status": "running",
        "public_only": True,
        "private_context_allowed": False,
        "external_tools_allowed": True,
        "connectors_allowed": ["PubMed/NCBI Entrez"],
        "human_review_required": False,
        "human_gate_status": "not-required",
        "state_path": "loop_state.json",
        "source_delta_status": "processed",
        "cycle_count": 1,
        "cycle_budget": 3,
        "open_items": [],
        "reviewer_objections": [],
        "stop_conditions": ["cycle budget reached"],
        "stop_status": "continue",
        "output_artifacts": [],
        "privacy_boundary": "public-only synthetic test state",
    }


def run_loop_state(tmp_path: Path, payload: dict[str, object]) -> subprocess.CompletedProcess[str]:
    path = tmp_path / "loop_state.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(LOOP_CHECK), "--loop-state", str(path)],
        text=True,
        capture_output=True,
        check=False,
    )


def combined_output(result: subprocess.CompletedProcess[str]) -> str:
    return result.stdout + result.stderr


@pytest.mark.parametrize(
    ("loop_type", "connectors"),
    [
        (
            "weekly_literature_watch",
            ["PubMed/NCBI Entrez", "bioRxiv/medRxiv", "DOI/Crossref", "Europe PMC"],
        ),
        (
            "public_omics_dataset_watch",
            ["GEO/SRA", "ArrayExpress/BioStudies", "CELLxGENE", "TCGA/GDC", "NCBI Datasets", "HPA"],
        ),
        (
            "hypothesis_triage",
            ["public omics repositories", "ChEMBL/PubChem", "Reactome/UniProt", "Open Targets"],
        ),
    ],
)
def test_loop_connector_aliases_from_matrix_pass(
    tmp_path: Path,
    loop_type: str,
    connectors: list[str],
) -> None:
    payload = base_loop_state(loop_type)
    payload["connectors_allowed"] = connectors

    result = run_loop_state(tmp_path, payload)

    assert result.returncode == 0, combined_output(result)
    assert "ERROR" not in combined_output(result)


def test_custom_loop_skips_fixed_connector_allowlist(tmp_path: Path) -> None:
    payload = base_loop_state("custom")
    payload["connectors_allowed"] = ["Gmail", "Internal ELN"]

    result = run_loop_state(tmp_path, payload)

    assert result.returncode == 0, combined_output(result)


def test_missing_required_loop_state_field_is_blocking_error(tmp_path: Path) -> None:
    payload = base_loop_state()
    del payload["cycle_budget"]

    result = run_loop_state(tmp_path, payload)

    assert result.returncode == 1
    output = combined_output(result)
    assert "LOOP_STATE_REQUIRED_FIELD_MISSING" in output
    assert "cycle_budget" in output


def test_invalid_cycle_fields_return_policy_error_without_traceback(tmp_path: Path) -> None:
    payload = base_loop_state()
    payload["cycle_count"] = "2"
    payload["cycle_budget"] = True

    result = run_loop_state(tmp_path, payload)

    output = combined_output(result)
    assert result.returncode == 1
    assert "INVALID_INTEGER_FIELD" in output
    assert "Traceback" not in output


def test_invalid_boolean_fields_are_blocking_errors(tmp_path: Path) -> None:
    payload = base_loop_state()
    payload["public_only"] = "false"
    payload["private_context_allowed"] = "true"

    result = run_loop_state(tmp_path, payload)

    output = combined_output(result)
    assert result.returncode == 1
    assert "INVALID_BOOLEAN_FIELD" in output


def test_open_items_block_complete_status(tmp_path: Path) -> None:
    payload = base_loop_state()
    payload["status"] = "complete"
    payload["open_items"] = [
        {
            "item_id": "LI-001",
            "item_type": "source_delta",
            "status": "triaged",
            "description": "unresolved source delta",
        }
    ]

    result = run_loop_state(tmp_path, payload)

    assert result.returncode == 1
    assert "OPEN_ITEMS_BEFORE_COMPLETE" in combined_output(result)


def test_human_review_required_blocks_reviewed_output(tmp_path: Path) -> None:
    payload = base_loop_state()
    payload["human_review_required"] = True
    payload["human_gate_status"] = "pending"
    payload["output_artifacts"] = [
        {
            "artifact_id": "OUT-001",
            "path": "outputs/source_delta.md",
            "artifact_type": "source_delta",
            "status": "reviewed",
        }
    ]

    result = run_loop_state(tmp_path, payload)

    assert result.returncode == 1
    assert "HUMAN_REVIEW_REQUIRED_BEFORE_TERMINAL_STATUS" in combined_output(result)


def test_cycle_budget_overrun_blocks_loop(tmp_path: Path) -> None:
    payload = base_loop_state()
    payload["cycle_count"] = 4
    payload["cycle_budget"] = 3

    result = run_loop_state(tmp_path, payload)

    assert result.returncode == 1
    assert "CYCLE_BUDGET_EXCEEDED" in combined_output(result)
