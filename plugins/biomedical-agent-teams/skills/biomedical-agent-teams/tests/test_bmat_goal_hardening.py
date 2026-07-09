from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = SKILL_ROOT / "scripts" / "bmat_validate.py"
BMAT_RUN = SKILL_ROOT / "scripts" / "bmat_run.py"
SOURCE_CHECK = SKILL_ROOT / "scripts" / "bmat_source_check.py"
OMICS_CHECK = SKILL_ROOT / "scripts" / "bmat_omics_metadata_check.py"
EXPERIMENT_CHECK = SKILL_ROOT / "scripts" / "bmat_experiment_design_check.py"
FIXTURES = SKILL_ROOT / "tests" / "fixtures"
PREFLIGHT_FILE = "runtime_capability_preflight.json"


def combined_output(result: subprocess.CompletedProcess[str]) -> str:
    return result.stdout + result.stderr


def run_validator(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(VALIDATOR), *args], text=True, capture_output=True, check=False, env=env)


def copy_valid_bundle(tmp_path: Path) -> Path:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    return bundle


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_release_mode_requires_jsonschema_or_fails(tmp_path: Path) -> None:
    bundle = copy_valid_bundle(tmp_path)
    blocker = tmp_path / "no_jsonschema"
    blocker.mkdir()
    (blocker / "jsonschema.py").write_text('raise ImportError("blocked by test")\n', encoding="utf-8")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(blocker) + os.pathsep + env.get("PYTHONPATH", "")

    result = run_validator("--bundle", str(bundle), "--release", env=env)

    assert result.returncode == 1
    assert "SCHEMA_VALIDATION_SKIPPED" in combined_output(result)


def test_release_mode_requires_tool_ledger_for_tool_wording(tmp_path: Path) -> None:
    bundle = copy_valid_bundle(tmp_path)
    (bundle / "tool_call_ledger.json").unlink()
    (bundle / "final.md").write_text(
        "Workflow label: Full protocol followed\n\nPubMed was queried for this claim.\n",
        encoding="utf-8",
    )

    result = run_validator("--bundle", str(bundle), "--release")

    assert result.returncode == 1
    assert "TOOL_CALL_LEDGER_REQUIRED" in combined_output(result)


def test_release_mode_does_not_upgrade_partial_scaffold(tmp_path: Path) -> None:
    bundle = tmp_path / "partial"
    init_bundle = SKILL_ROOT / "scripts" / "bmat_init_bundle.py"
    created = subprocess.run(
        [
            sys.executable,
            str(init_bundle),
            "--workflow",
            "evidence-audit-team",
            "--mode",
            "standard",
            "--out",
            str(bundle),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert created.returncode == 0, combined_output(created)

    result = run_validator("--bundle", str(bundle), "--release", "--require-label", "Full protocol followed")

    assert result.returncode == 1
    assert "FULL_PROTOCOL_REQUIRES" in combined_output(result)


def test_release_mode_rejects_sample_mode_as_live_model_evidence(tmp_path: Path) -> None:
    bundle = copy_valid_bundle(tmp_path)
    run_state = read_json(bundle / "run_state.json")
    run_state["model_validation_mode"] = "sample-mode"
    write_json(bundle / "run_state.json", run_state)
    (bundle / "final.md").write_text(
        "Workflow label: Full protocol followed\n\nSample-mode golden eval is live model performance validation.\nSynthetic public fixture supports a conservative audit claim.\n",
        encoding="utf-8",
    )

    result = run_validator("--bundle", str(bundle), "--release")

    assert result.returncode == 1
    assert "SAMPLE_MODE_CANNOT_BE_LIVE_MODEL_EVIDENCE" in combined_output(result)


def test_source_verification_required_for_release_source_backed_claim(tmp_path: Path) -> None:
    bundle = copy_valid_bundle(tmp_path)
    (bundle / "source_verification.json").unlink()

    result = run_validator("--bundle", str(bundle), "--release")

    assert result.returncode == 1
    assert "SOURCE_VERIFICATION_REQUIRED" in combined_output(result)


def test_source_verification_verified_source_passes(tmp_path: Path) -> None:
    bundle = copy_valid_bundle(tmp_path)

    result = run_validator(
        "--bundle",
        str(bundle),
        "--release",
        "--check-tool-ledger",
        "--require-label",
        "Full protocol followed",
    )

    assert result.returncode == 0, combined_output(result)


def test_source_verification_not_found_blocks_high_confidence(tmp_path: Path) -> None:
    bundle = copy_valid_bundle(tmp_path)
    verification = read_json(bundle / "source_verification.json")
    verification["rows"][0]["identifier_status"] = "not-found"
    write_json(bundle / "source_verification.json", verification)

    result = run_validator("--bundle", str(bundle), "--release")

    assert result.returncode == 1
    assert "SOURCE_VERIFICATION_BLOCKS_HIGH_CONFIDENCE" in combined_output(result)


def test_tool_backed_source_verification_requires_successful_tool_call(tmp_path: Path) -> None:
    bundle = copy_valid_bundle(tmp_path)
    verification = read_json(bundle / "source_verification.json")
    verification["rows"][0]["tool_call_id"] = "TC-MISSING"
    write_json(bundle / "source_verification.json", verification)

    result = run_validator("--bundle", str(bundle), "--release")

    assert result.returncode == 1
    assert "SOURCE_VERIFICATION_TOOL_CALL_NOT_SUCCESSFUL" in combined_output(result)


def test_source_verification_unknown_source_id_fails(tmp_path: Path) -> None:
    bundle = copy_valid_bundle(tmp_path)
    verification = read_json(bundle / "source_verification.json")
    verification["rows"][0]["source_id"] = "S-MISSING"
    write_json(bundle / "source_verification.json", verification)

    result = run_validator("--bundle", str(bundle), "--release")

    assert result.returncode == 1
    assert "SOURCE_VERIFICATION_UNKNOWN_SOURCE_ID" in combined_output(result)


def test_release_source_backed_claim_requires_strict_fields(tmp_path: Path) -> None:
    bundle = copy_valid_bundle(tmp_path)
    ledger = read_json(bundle / "claim_ledger.json")
    ledger["claims"][0]["claim_profile"] = "source_backed"
    del ledger["claims"][0]["uncertainty"]
    write_json(bundle / "claim_ledger.json", ledger)

    result = run_validator("--bundle", str(bundle), "--release")

    assert result.returncode == 1
    assert "RELEASE_SOURCE_BACKED_CLAIM_FIELD_MISSING" in combined_output(result)


def test_release_high_confidence_requires_support_and_no_scope_mismatch(tmp_path: Path) -> None:
    bundle = copy_valid_bundle(tmp_path)
    ledger = read_json(bundle / "claim_ledger.json")
    ledger["claims"][0]["claim_profile"] = "high_confidence"
    ledger["claims"][0]["scope_match"]["assay"] = "mismatch"
    write_json(bundle / "claim_ledger.json", ledger)

    result = run_validator("--bundle", str(bundle), "--release")

    assert result.returncode == 1
    assert "HIGH_CONFIDENCE_REQUIRES_SUPPORT_AND_SCOPE" in combined_output(result)


def test_evidence_span_ref_must_resolve(tmp_path: Path) -> None:
    bundle = copy_valid_bundle(tmp_path)
    ledger = read_json(bundle / "claim_ledger.json")
    ledger["claims"][0]["evidence_edges"] = [
        {
            "subject": "synthetic claim",
            "predicate": "supported_by",
            "object": "synthetic source",
            "source_id": "S-001",
            "evidence_span_ref": "S-001-missing-span",
        }
    ]
    write_json(bundle / "claim_ledger.json", ledger)

    result = run_validator("--bundle", str(bundle), "--release")

    assert result.returncode == 1
    assert "EVIDENCE_SPAN_REF_UNRESOLVED" in combined_output(result)


def test_blocked_claim_cannot_appear_in_final(tmp_path: Path) -> None:
    bundle = copy_valid_bundle(tmp_path)
    ledger = read_json(bundle / "claim_ledger.json")
    ledger["claims"].append(
        {
            "claim_id": "CL-BLOCKED",
            "atomic_claim": "This blocked claim must not be final.",
            "claim_profile": "blocked",
            "block_reason": "synthetic block",
        }
    )
    write_json(bundle / "claim_ledger.json", ledger)
    (bundle / "final.md").write_text(
        "Workflow label: Full protocol followed\n\nSynthetic public fixture supports a conservative audit claim.\nThis blocked claim must not be final.\n",
        encoding="utf-8",
    )

    result = run_validator("--bundle", str(bundle), "--release")

    assert result.returncode == 1
    assert "BLOCKED_CLAIM_IN_FINAL_TEXT" in combined_output(result)


def test_tool_backed_claim_requires_results_and_successful_tool_call(tmp_path: Path) -> None:
    bundle = copy_valid_bundle(tmp_path)
    ledger = read_json(bundle / "claim_ledger.json")
    ledger["claims"].append(
        {
            "claim_id": "CL-TOOL",
            "atomic_claim": "Tool-backed synthetic claim.",
            "claim_profile": "tool_backed",
            "tool_ids": ["pubmed"],
            "source_ids": ["S-001"],
        }
    )
    write_json(bundle / "claim_ledger.json", ledger)

    result = run_validator("--bundle", str(bundle), "--release")

    assert result.returncode == 1
    assert "TOOL_BACKED_CLAIM_REQUIRES_RESULTS_AND_SUCCESSFUL_TOOL_CALL" in combined_output(result)


def test_claim_support_matrix_required_for_high_confidence_release(tmp_path: Path) -> None:
    bundle = copy_valid_bundle(tmp_path)
    (bundle / "claim_support_matrix.json").unlink()

    result = run_validator("--bundle", str(bundle), "--release")

    assert result.returncode == 1
    assert "CLAIM_SUPPORT_MATRIX_REQUIRED" in combined_output(result)


def test_weak_support_cannot_be_high_confidence(tmp_path: Path) -> None:
    bundle = copy_valid_bundle(tmp_path)
    matrix = read_json(bundle / "claim_support_matrix.json")
    matrix["rows"][0]["support_verdict"] = "weakly_supports"
    write_json(bundle / "claim_support_matrix.json", matrix)

    result = run_validator("--bundle", str(bundle), "--release")

    assert result.returncode == 1
    assert "WEAK_SUPPORT_CANNOT_BE_HIGH_CONFIDENCE" in combined_output(result)


def test_contradicting_support_row_blocks_final_claim(tmp_path: Path) -> None:
    bundle = copy_valid_bundle(tmp_path)
    matrix = read_json(bundle / "claim_support_matrix.json")
    matrix["rows"][0]["support_verdict"] = "contradicts"
    matrix["rows"][0]["allowed_in_final"] = True
    write_json(bundle / "claim_support_matrix.json", matrix)

    result = run_validator("--bundle", str(bundle), "--release")

    assert result.returncode == 1
    assert "CLAIM_SUPPORT_BLOCKING_VERDICT_ALLOWED_IN_FINAL" in combined_output(result)


def test_support_matrix_wording_conflict_fails(tmp_path: Path) -> None:
    bundle = copy_valid_bundle(tmp_path)
    matrix = read_json(bundle / "claim_support_matrix.json")
    matrix["rows"][0]["allowed_final_wording"] = "Conflicting wording."
    write_json(bundle / "claim_support_matrix.json", matrix)

    result = run_validator("--bundle", str(bundle), "--release")

    assert result.returncode == 1
    assert "CLAIM_SUPPORT_WORDING_CONFLICT" in combined_output(result)


def test_omics_run_without_track_blocks(tmp_path: Path) -> None:
    bundle = tmp_path / "omics-run-no-track"
    result = subprocess.run(
        [
            sys.executable,
            str(BMAT_RUN),
            "--alias",
            "omics-analysis-team",
            "--mode",
            "run",
            "--question",
            "synthetic omics run without track",
            "--out",
            str(bundle),
            "--force",
            "--validate",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "OMICS_RUN_TRACK_REQUIRED" in combined_output(result)
    assert not (bundle / "omics_run_manifest.json").exists()


def test_omics_plan_without_track_allowed_with_ambiguity_note(tmp_path: Path) -> None:
    bundle = tmp_path / "omics-plan-no-track"
    result = subprocess.run(
        [
            sys.executable,
            str(BMAT_RUN),
            "--alias",
            "omics-analysis-team",
            "--mode",
            "plan",
            "--question",
            "synthetic omics plan without track",
            "--out",
            str(bundle),
            "--force",
            "--validate",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    preflight = read_json(bundle / PREFLIGHT_FILE)

    assert result.returncode == 0, combined_output(result)
    assert preflight["requested_omics_track"] == "track_ambiguous"
    assert "omics_track_ambiguity_note" in preflight
    assert not (bundle / "omics_run_manifest.json").exists()


def test_omics_run_with_track_aligns_all_track_fields(tmp_path: Path) -> None:
    bundle = tmp_path / "omics-run-with-track"
    result = subprocess.run(
        [
            sys.executable,
            str(BMAT_RUN),
            "--alias",
            "omics-analysis-team",
            "--mode",
            "run",
            "--track",
            "survival",
            "--question",
            "synthetic survival omics run",
            "--out",
            str(bundle),
            "--force",
            "--validate",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, combined_output(result)
    assert read_json(bundle / "run_state.json")["omics_track"] == "survival"
    assert read_json(bundle / PREFLIGHT_FILE)["requested_omics_track"] == "survival"
    assert read_json(bundle / "lead_decision.json")["omics_subtrack"] == "survival"
    assert read_json(bundle / "workflow_dag.json")["track"] == "survival"
    assert read_json(bundle / "omics_run_manifest.json")["track"] == "survival"


def test_full_protocol_requires_review_artifact_manifest(tmp_path: Path) -> None:
    bundle = copy_valid_bundle(tmp_path)
    (bundle / "review_artifact_manifest.json").unlink()

    result = run_validator("--bundle", str(bundle), "--release", "--require-label", "Full protocol followed")

    assert result.returncode == 1
    assert "REVIEW_ARTIFACT_MANIFEST_REQUIRED" in combined_output(result)


def test_review_manifest_output_hash_mismatch_fails(tmp_path: Path) -> None:
    bundle = copy_valid_bundle(tmp_path)
    manifest = read_json(bundle / "review_artifact_manifest.json")
    manifest["review_instances"][0]["output_sha256"] = "0" * 64
    write_json(bundle / "review_artifact_manifest.json", manifest)

    result = run_validator("--bundle", str(bundle), "--release")

    assert result.returncode == 1
    assert "REVIEW_MANIFEST_OUTPUT_HASH_MISMATCH" in combined_output(result)


def test_review_changed_claim_requires_results_integration(tmp_path: Path) -> None:
    bundle = copy_valid_bundle(tmp_path)
    manifest = read_json(bundle / "review_artifact_manifest.json")
    manifest["review_instances"][0]["changed_claim_ids"] = ["CL-MISSING"]
    write_json(bundle / "review_artifact_manifest.json", manifest)

    result = run_validator("--bundle", str(bundle), "--release")

    assert result.returncode == 1
    assert "REVIEW_CHANGED_CLAIM_REQUIRES_RESULTS_INTEGRATION" in combined_output(result)


def test_bulk_metadata_check_missing_design_blocks(tmp_path: Path) -> None:
    manifest = {
        "workflow_run_id": "bulk-missing-design",
        "track": "bulk-rnaseq",
        "sample_sheet": "samples.tsv",
        "assay_metadata": {
            "organism": "Homo sapiens",
            "genome_build": "GRCh38",
            "annotation_release": "GENCODE v44",
        },
        "biological_unit_policy": {"unit": "sample", "replicate_key": "sample_id"},
        "contrast_or_endpoint": "treated vs control",
        "de_strategy": {"multiplicity_method": "BH-FDR"},
        "generated_artifacts": {},
    }
    manifest_path = tmp_path / "omics_run_manifest.json"
    write_json(manifest_path, manifest)
    out = tmp_path / "omics_metadata_check.json"

    result = subprocess.run(
        [sys.executable, str(OMICS_CHECK), "--track", "bulk-rnaseq", "--omics-run-manifest", str(manifest_path), "--out", str(out), "--json"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "design_formula" in combined_output(result)


def test_tenx_metadata_check_missing_molecule_info_blocks(tmp_path: Path) -> None:
    manifest = {
        "workflow_run_id": "tenx-missing-molecule",
        "track": "tenx-gex",
        "sample_sheet": "samples.tsv",
        "assay_metadata": {
            "organism": "Homo sapiens",
            "genome_build": "GRCh38",
            "annotation_release": "GENCODE v44",
            "cellranger_version": "8.0.0",
            "cellranger_command": "count",
        },
        "biological_unit_policy": {
            "unit": "donor",
            "replicate_key": "donor_id",
            "pseudobulk_required": True,
            "pseudobulk_policy": "donor-aware pseudobulk",
        },
        "contrast_or_endpoint": "high vs low",
        "qc_decisions": {
            "cell_calling_method": "Cell Ranger",
            "ambient_rna_method": "SoupX",
            "doublet_method": "scDblFinder",
            "empty_droplet_method": "emptyDrops",
        },
        "generated_artifacts": {
            "web_summary_html": "web_summary.html",
            "filtered_feature_bc_matrix": "filtered",
            "raw_feature_bc_matrix": "raw",
        },
    }
    manifest_path = tmp_path / "omics_run_manifest.json"
    write_json(manifest_path, manifest)
    out = tmp_path / "omics_metadata_check.json"

    result = subprocess.run(
        [sys.executable, str(OMICS_CHECK), "--track", "tenx-gex", "--omics-run-manifest", str(manifest_path), "--out", str(out), "--json"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "molecule_info_h5" in combined_output(result)


def test_experiment_design_missing_controls_blocks_release(tmp_path: Path) -> None:
    design = {
        "design_id": "exp-test",
        "workflow_run_id": "run-exp",
        "plugin_version": "1.1.0",
        "hypothesis": "synthetic",
        "experimental_objective": "synthetic",
        "experimental_unit": {"unit_type": "donor", "justification": "biological replicate"},
        "primary_endpoint": "endpoint",
        "positive_controls": [],
        "negative_controls": [],
        "vehicle_or_mock_controls": [],
        "biological_replicates": {"planned_n": 3, "rationale": "synthetic"},
        "technical_replicates": {"planned_n": 2, "rationale": "synthetic"},
        "randomization": {"planned": True, "method_or_reason": "synthetic"},
        "blinding": {"planned": False, "method_or_reason": "synthetic"},
        "exclusion_criteria": [],
        "confounders": [],
        "causal_kill_tests": [],
        "statistical_plan": {"model": "linear model", "multiplicity": "BH-FDR", "effect_size_or_decision_threshold": "delta"},
        "go_no_go_gates": [],
        "safety_ethics_privacy_boundary": "public synthetic",
        "reagent_provenance_policy": "verify before use",
        "source_ids": [],
        "claim_ids_supported": [],
    }
    design_path = tmp_path / "experiment_design.json"
    write_json(design_path, design)

    result = subprocess.run(
        [sys.executable, str(EXPERIMENT_CHECK), "--experiment-design", str(design_path), "--json"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "EXPERIMENT_DESIGN_CONTROL_MISSING" in combined_output(result)


def test_source_check_offline_fixture_writes_verified_rows(tmp_path: Path) -> None:
    bundle = copy_valid_bundle(tmp_path)
    out = tmp_path / "source_verification.json"

    result = subprocess.run(
        [
            sys.executable,
            str(SOURCE_CHECK),
            "--source-corpus",
            str(bundle / "source_corpus.json"),
            "--claim-ledger",
            str(bundle / "claim_ledger.json"),
            "--tool-call-ledger",
            str(bundle / "tool_call_ledger.json"),
            "--out",
            str(out),
            "--offline-fixture",
            "--json",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, combined_output(result)
    payload = read_json(out)
    assert payload["rows"][0]["identifier_status"] == "verified"
    assert payload["rows"][0]["metadata_match"] == "pass"
