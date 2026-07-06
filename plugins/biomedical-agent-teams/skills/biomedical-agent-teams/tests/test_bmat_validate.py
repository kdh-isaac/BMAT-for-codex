from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import importlib.util
from pathlib import Path

import pytest


SKILL_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = SKILL_ROOT / "scripts" / "bmat_validate.py"
FIXTURES = SKILL_ROOT / "tests" / "fixtures"
PREFLIGHT_FILE = "runtime_capability_preflight.json"
UTF8_BOM_BYTES = b"\xef\xbb\xbf"


def run_validator(fixture_name: str) -> subprocess.CompletedProcess[str]:
    return run_validator_path(FIXTURES / fixture_name)


def run_validator_path(bundle_path: Path) -> subprocess.CompletedProcess[str]:
    return run_validator_path_with_env(bundle_path, None)


def run_validator_path_with_env(
    bundle_path: Path,
    env: dict[str, str] | None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "--bundle", str(bundle_path)],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def run_validator_args(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def valid_results_integration_payload() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "integration_id": "RI-TEST-001",
        "plugin_version": "1.1.0",
        "source_corpus_lock": "locked",
        "tool_use_log": [
            {
                "tool_id": "spawned-reviewer-lane",
                "status": "used",
                "used": True,
                "source_corpus_rows": ["SC-001"],
                "result_rows": ["RI-ROW-001"],
                "downgrade_reason": "",
            }
        ],
        "rows": [
            {
                "result_id": "RI-ROW-001",
                "result_type": "literature",
                "source_ref": "SC-001",
                "claim_ids": ["CL-001"],
                "status": "support",
                "evidence_direction": "supports",
                "confidence": "moderate",
                "interpretation": "Public literature supports a bounded claim.",
                "limitations": "Synthetic regression fixture.",
                "ledger_action": "update",
            }
        ],
        "final_claim_policy": "ledger-only",
        "human_review_status": "not-needed",
    }


def spawnable_agent_ids() -> list[str]:
    registry = json.loads((SKILL_ROOT / "agent-registry.json").read_text(encoding="utf-8-sig"))
    agents = registry.get("agents", [])
    assert isinstance(agents, list)
    return sorted(
        str(agent["agent_id"])
        for agent in agents
        if isinstance(agent, dict) and agent.get("spawnable") is True
    )


def combined_output(result: subprocess.CompletedProcess[str]) -> str:
    return result.stdout + result.stderr


def load_validator_module():
    spec = importlib.util.spec_from_file_location("bmat_validate_under_test", VALIDATOR)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def prefix_utf8_bom(path: Path) -> None:
    path.write_bytes(UTF8_BOM_BYTES + path.read_bytes())


def add_valid_team_dag(run_state: dict[str, object]) -> None:
    run_state["execution_strategy"] = "team_level_selective_dag"
    run_state["team_spawn_lanes"] = [
        {
            "team": "idea-discovery-team",
            "phase": 1,
            "depends_on": [],
            "status": "complete",
            "nested_spawn_used": False,
            "ledger_handoff": "TEAM-IDEA-001 accepted into CL-IDEA",
        },
        {
            "team": "experiment-design-team",
            "phase": 2,
            "depends_on": ["idea-discovery-team"],
            "status": "complete",
            "nested_spawn_used": False,
            "ledger_handoff": "TEAM-EXPERIMENT-001 accepted into CL-DESIGN",
        },
    ]
    run_state["team_output_artifacts"] = [
        {
            "team": "idea-discovery-team",
            "phase": 1,
            "artifact_id": "TEAM-IDEA-001",
            "path": "team-outputs/idea-discovery-team.md",
            "status": "complete",
            "input_scope": "candidate hypothesis generation",
            "checks_run": ["formal team output contract checked"],
            "ledger_handoff": "TEAM-IDEA-001 accepted into CL-IDEA",
            "depends_on_outputs": [],
        },
        {
            "team": "experiment-design-team",
            "phase": 2,
            "artifact_id": "TEAM-EXPERIMENT-001",
            "path": "team-outputs/experiment-design-team.md",
            "status": "complete",
            "input_scope": "validation design for narrowed candidate",
            "checks_run": ["formal team output contract checked", "phase dependency checked"],
            "ledger_handoff": "TEAM-EXPERIMENT-001 accepted into CL-DESIGN",
            "depends_on_outputs": ["TEAM-IDEA-001"],
        },
    ]


def write_spawned_output_artifact(bundle: Path, artifact_ref: str, body: str = "synthetic spawned review output\n") -> None:
    path = bundle / artifact_ref.split("#", 1)[0]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def write_team_output_artifacts(bundle: Path) -> None:
    for artifact_ref in (
        "team-outputs/idea-discovery-team.md",
        "team-outputs/experiment-design-team.md",
    ):
        path = bundle / artifact_ref
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"synthetic team output: {artifact_ref}\n", encoding="utf-8")


def write_valid_team_workflow_dag(bundle: Path) -> None:
    workflow_dag = {
        "workflow_id": "evidence-audit-team.audit.synthetic-team-dag",
        "runtime": "codex",
        "alias": "evidence-audit-team",
        "mode": "audit",
        "track": "synthetic-team-dag",
        "nodes": [
            {
                "id": "S0",
                "agent": "protocol-context-locker",
                "outputs": ["runtime_capability_preflight"],
                "blocking": True,
            },
            {
                "id": "S1",
                "agent": "life-science-literature-curator",
                "requires": ["S0"],
                "outputs": ["source_corpus"],
                "blocking": True,
            },
            {
                "id": "S3",
                "agent": "post-write-final-validator",
                "requires": ["S1"],
                "outputs": ["post_write_validation"],
                "blocking": True,
                "spawnable": True,
                "toml_template_path": "codex-agents/post-write-final-validator.toml",
                "independence_required": True,
            },
        ],
        "release_gates": ["bmat_validate", "bmat_tool_ledger_check"],
    }
    (bundle / "workflow_dag.json").write_text(json.dumps(workflow_dag, indent=2), encoding="utf-8")


def sync_lead_decision(bundle: Path) -> None:
    run_state = json.loads((bundle / "run_state.json").read_text(encoding="utf-8"))
    preflight = json.loads((bundle / PREFLIGHT_FILE).read_text(encoding="utf-8"))
    lead_path = bundle / "lead_decision.json"
    lead = json.loads(lead_path.read_text(encoding="utf-8"))
    lead["workflow_run_id"] = run_state.get("run_id")
    lead["requested_alias"] = run_state.get("alias")
    lead["selected_mode"] = run_state.get("mode")
    lead["workflow_tier"] = run_state.get("workflow_tier", lead.get("workflow_tier", "compact"))
    lead["omics_subtrack"] = run_state.get("omics_track", preflight.get("requested_omics_track", "not-applicable"))
    lead["execution_strategy"] = run_state.get("execution_strategy")
    lead["spawned_review_plan"] = preflight.get("spawned_review_plan", {})
    lead["team_spawn_plan"] = preflight.get("team_spawn_plan", {})
    lead["post_team_audit_plan"] = preflight.get("post_team_audit_plan", "fixture post-write validation")
    lead_path.write_text(json.dumps(lead, indent=2), encoding="utf-8")


def write_single_cell_other_omics_manifest(bundle: Path) -> None:
    run_state = json.loads((bundle / "run_state.json").read_text(encoding="utf-8"))
    manifest = {
        "schema_version": "2.0",
        "analysis_id": "omics-fixture",
        "workflow_run_id": run_state.get("run_id", "omics-run-fixture"),
        "track": "single-cell-other",
        "data_sources": [],
        "sample_sheet": "samples.csv",
        "assay_metadata": {
            "organism": "Homo sapiens",
            "genome_build": "GRCh38",
            "annotation_release": "GENCODE v44",
        },
        "biological_unit_policy": {
            "unit": "sample",
            "replicate_key": "sample_id",
            "pseudobulk_required": False,
            "pseudobulk_policy": "descriptive fixture",
        },
        "contrast_or_endpoint": "fixture contrast",
        "software_versions": ["fixture"],
        "qc_decisions": {},
        "de_strategy": {
            "cross_sample_method": "not-run",
            "multiplicity_method": "not-run",
        },
        "generated_artifacts": {},
        "review_status": {
            "code_review": "not-run",
            "provenance_review": "not-run",
            "biostats_review": "not-run",
        },
    }
    (bundle / "omics_run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def write_omics_track_context(bundle: Path, track: str) -> None:
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    run_state["alias"] = "omics-analysis-team"
    run_state["omics_track"] = track
    run_state["final_label"] = "Compact standard workflow"
    run_state["downgrade_reasons"] = [f"synthetic compact {track} fixture"]
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    preflight_path = bundle / PREFLIGHT_FILE
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    preflight["requested_alias"] = "omics-analysis-team"
    preflight["requested_omics_track"] = track
    preflight_path.write_text(json.dumps(preflight, indent=2), encoding="utf-8")

    lead_path = bundle / "lead_decision.json"
    lead = json.loads(lead_path.read_text(encoding="utf-8"))
    lead["requested_alias"] = "omics-analysis-team"
    lead["omics_subtrack"] = track
    lead_path.write_text(json.dumps(lead, indent=2), encoding="utf-8")


def valid_tenx_manifest(track: str) -> dict[str, object]:
    cellranger_command = {
        "tenx-citeseq": "multi",
        "tenx-vdj": "vdj",
        "tenx-multiome": "arc",
    }.get(track, "count")
    manifest: dict[str, object] = {
        "schema_version": "2.0",
        "analysis_id": "omics-test",
        "track": track,
        "data_sources": [],
        "sample_sheet": "samples.csv",
        "assay_metadata": {
            "organism": "Homo sapiens",
            "genome_build": "GRCh38",
            "annotation_release": "GENCODE v44",
            "chemistry": "5prime",
            "cellranger_version": "8.0.0",
            "cellranger_command": cellranger_command,
        },
        "biological_unit_policy": {
            "unit": "donor",
            "replicate_key": "donor_id",
            "pseudobulk_required": True,
            "pseudobulk_policy": "donor-aware pseudobulk for cross-sample DE",
        },
        "contrast_or_endpoint": "high vs low expression",
        "software_versions": ["cellranger 8.0.0"],
        "qc_decisions": {
            "cell_calling_method": "Cell Ranger filtered matrix plus emptyDrops review",
            "ambient_rna_method": "SoupX planned",
            "doublet_method": "scDblFinder planned",
            "empty_droplet_method": "DropletUtils emptyDrops planned",
        },
        "de_strategy": {
            "cross_sample_method": "pseudobulk DESeq2",
            "multiplicity_method": "BH-FDR",
        },
        "generated_artifacts": {
            "web_summary_html": "web_summary.html",
            "filtered_feature_bc_matrix": "filtered_feature_bc_matrix",
            "raw_feature_bc_matrix": "raw_feature_bc_matrix",
            "molecule_info_h5": "molecule_info.h5",
        },
        "review_status": {
            "code_review": "not-run",
            "provenance_review": "not-run",
            "biostats_review": "not-run",
        },
    }
    assay_metadata = manifest["assay_metadata"]
    generated_artifacts = manifest["generated_artifacts"]
    assert isinstance(assay_metadata, dict)
    assert isinstance(generated_artifacts, dict)
    if track == "tenx-citeseq":
        assay_metadata.update(
            {
                "feature_reference_ref": "feature_reference.csv",
                "antibody_panel_ref": "adt_panel.tsv",
            }
        )
        generated_artifacts.update(
            {
                "feature_reference_csv": "feature_reference.csv",
                "feature_barcode_matrix": "filtered_feature_bc_matrix/features.tsv.gz",
            }
        )
    if track == "tenx-vdj":
        assay_metadata.update(
            {
                "vdj_reference": "cellranger-vdj-GRCh38-alts-ensembl",
                "gex_linkage_key": "cell_barcode",
            }
        )
        generated_artifacts.update(
            {
                "vdj_contig_annotations": "filtered_contig_annotations.csv",
                "vdj_clonotypes": "clonotypes.csv",
            }
        )
    if track == "tenx-multiome":
        assay_metadata.update(
            {
                "atac_reference": "refdata-cellranger-arc-GRCh38",
                "feature_linkage_ref": "linked_features.csv",
            }
        )
        generated_artifacts.update(
            {
                "fragments_tsv_gz": "atac_fragments.tsv.gz",
                "atac_peak_matrix": "filtered_feature_bc_matrix/peaks.bed",
                "arc_summary_html": "web_summary.html",
            }
        )
    return manifest


def make_omics_run_bundle(
    tmp_path: Path,
    *,
    spawned_review_plan: dict[str, object],
    downgrade_reasons: list[str] | None = None,
    skipped_role_outputs: list[dict[str, str]] | None = None,
    spawned_review_lanes: list[dict[str, object]] | None = None,
    spawned_agent_instances: list[dict[str, object]] | None = None,
    independent_review_status: str = "same-model separate-pass validation",
) -> Path:
    bundle = tmp_path / "omics_bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)

    preflight_path = bundle / PREFLIGHT_FILE
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    preflight["requested_alias"] = "omics-analysis-team"
    preflight["selected_mode"] = "run"
    preflight["requested_omics_track"] = "single-cell-other"
    preflight["deliverable_type"] = "synthetic omics run fixture"
    preflight["required_role_outputs"] = [
        "omics-code-reviewer",
        "omics-provenance-validator",
        "post-write-final-validator",
    ]
    preflight["skipped_role_outputs_with_reason"] = skipped_role_outputs or []
    preflight["spawned_review_plan"] = spawned_review_plan
    preflight["workflow_run_id"] = "omics-run-fixture"
    preflight_path.write_text(json.dumps(preflight, indent=2), encoding="utf-8")

    claim_ledger_path = bundle / "claim_ledger.json"
    claim_ledger = json.loads(claim_ledger_path.read_text(encoding="utf-8"))
    for claim in claim_ledger.get("claims", []):
        if isinstance(claim, dict):
            claim["claim_strength"] = "exploratory"
    claim_ledger_path.write_text(json.dumps(claim_ledger, indent=2), encoding="utf-8")

    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    run_state["run_id"] = "omics-run-fixture"
    run_state["alias"] = "omics-analysis-team"
    run_state["mode"] = "run"
    run_state["omics_track"] = "single-cell-other"
    run_state["execution_strategy"] = "inline_first_selective_review"
    run_state["spawned_review_lanes"] = spawned_review_lanes or []
    run_state["spawned_agent_instances"] = spawned_agent_instances or []
    run_state["final_label"] = "Compact standard workflow"
    run_state["downgrade_reasons"] = downgrade_reasons or []
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    post_write_path = bundle / "post_write_validation.json"
    post_write = json.loads(post_write_path.read_text(encoding="utf-8"))
    post_write["independent_review_status"] = independent_review_status
    post_write["release_ready_claim_strength"] = "exploratory association"
    post_write_path.write_text(json.dumps(post_write, indent=2), encoding="utf-8")

    (bundle / "final.md").write_text(
        "Final workflow label: Compact standard workflow\n"
        "Synthetic omics run fixture for reviewer-spawn policy.\n",
        encoding="utf-8",
    )
    sync_lead_decision(bundle)
    write_single_cell_other_omics_manifest(bundle)
    return bundle


def test_valid_bundle_passes() -> None:
    result = run_validator("valid_full_protocol_bundle")
    assert result.returncode == 0, combined_output(result)
    assert "ERROR" not in result.stdout
    assert "LEGACY_BUNDLE_ARTIFACT_NAME" not in result.stdout


def test_legacy_preflight_alias_passes_with_warning() -> None:
    result = run_validator("valid_legacy_preflight_bundle")
    output = combined_output(result)

    assert result.returncode == 0, output
    assert "LEGACY_BUNDLE_ARTIFACT_NAME" in output
    assert PREFLIGHT_FILE in output


def test_valid_bundle_accepts_utf8_bom_prefixed_artifacts(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    for filename in (
        "run_state.json",
        PREFLIGHT_FILE,
        "source_corpus.json",
        "claim_ledger.json",
        "stage_evaluation.json",
        "post_write_validation.json",
        "final.md",
    ):
        prefix_utf8_bom(bundle / filename)

    result = run_validator_path(bundle)

    assert result.returncode == 0, combined_output(result)
    assert "ERROR" not in result.stdout


def test_results_integration_accepts_utf8_bom_prefix(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    results_integration = bundle / "results_integration.json"
    results_integration.write_text(
        json.dumps(valid_results_integration_payload(), indent=2),
        encoding="utf-8",
    )
    prefix_utf8_bom(results_integration)

    result = run_validator_path(bundle)

    assert result.returncode == 0, combined_output(result)
    assert "ERROR" not in result.stdout


def test_results_integration_artifact_schema_is_validated_when_present(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    payload = valid_results_integration_payload()
    payload["tool_use_log"][0]["used"] = False
    (bundle / "results_integration.json").write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "SCHEMA_VALIDATION_FAILED" in combined_output(result)
    assert "results_integration" in combined_output(result)


def test_complete_reviewer_output_requires_results_integration(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    (bundle / "results_integration.json").unlink()

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "RESULTS_INTEGRATION_REQUIRED" in combined_output(result)


def test_tool_ledger_check_requires_ledger_when_results_use_tool(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    (bundle / "tool_call_ledger.json").unlink()

    result = run_validator_args("--bundle", str(bundle), "--check-tool-ledger")

    assert result.returncode == 1
    assert "TOOL_CALL_LEDGER_REQUIRED" in combined_output(result)


def test_tool_use_wording_uses_token_boundaries_for_translational_alias() -> None:
    module = load_validator_module()

    scaffold_text = (
        "Workflow label: Partial workflow; formal gates skipped\n\n"
        "Scaffold for `translational-scout-team` in `audit` mode.\n\n"
        "Do not replace this with source-backed final wording until the claim "
        "ledger, source corpus, and post-write validation are updated."
    )

    assert module.final_text_has_tool_use_wording(scaffold_text) is False
    assert module.final_text_has_tool_use_wording("We ran PubMed and checked NCBI.") is True


def test_results_integration_used_tool_requires_successful_call(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    ledger_path = bundle / "tool_call_ledger.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger["calls"] = []
    ledger_path.write_text(json.dumps(ledger, indent=2), encoding="utf-8")

    result = run_validator_args("--bundle", str(bundle), "--check-tool-ledger")

    assert result.returncode == 1
    assert "RESULTS_INTEGRATION_TOOL_WITHOUT_SUCCESSFUL_CALL" in combined_output(result)


def test_semantic_scope_mismatch_blocks_high_confidence_claim(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    ledger_path = bundle / "claim_ledger.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger["claims"][0]["scope_match"]["species"] = "mismatch"
    ledger_path.write_text(json.dumps(ledger, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "SCOPE_MISMATCH_BLOCKS_HIGH_CONFIDENCE" in combined_output(result)


def test_full_protocol_without_independent_review_fails() -> None:
    result = run_validator("invalid_full_protocol_without_independent_review")
    assert result.returncode == 1
    assert "FULL_PROTOCOL_REQUIRES_INDEPENDENT_SURFACE" in combined_output(result)


def test_missing_lead_decision_emits_fix_hint_json(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    (bundle / "lead_decision.json").unlink()

    result = run_validator_args("--bundle", str(bundle), "--json")

    assert result.returncode == 1
    findings = json.loads(result.stdout)
    lead_findings = [finding for finding in findings if finding["code"] == "LEAD_DECISION_REQUIRED_FULL_PROTOCOL"]
    assert lead_findings
    assert lead_findings[0]["fix_hint"]
    assert "lead_decision.json" in lead_findings[0]["fix_hint"]


def test_omics_manifest_required_for_explicit_track(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    run_state["alias"] = "omics-analysis-team"
    run_state["omics_track"] = "bulk-rnaseq"
    run_state["final_label"] = "Compact standard workflow"
    run_state["downgrade_reasons"] = ["synthetic compact omics fixture"]
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    preflight_path = bundle / PREFLIGHT_FILE
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    preflight["requested_alias"] = "omics-analysis-team"
    preflight["requested_omics_track"] = "bulk-rnaseq"
    preflight_path.write_text(json.dumps(preflight, indent=2), encoding="utf-8")

    lead_path = bundle / "lead_decision.json"
    lead = json.loads(lead_path.read_text(encoding="utf-8"))
    lead["requested_alias"] = "omics-analysis-team"
    lead["omics_subtrack"] = "bulk-rnaseq"
    lead_path.write_text(json.dumps(lead, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "OMICS_RUN_MANIFEST_REQUIRED" in combined_output(result)
    assert "fix_hint=" in combined_output(result)


def test_tenx_omics_manifest_requires_cellranger_artifacts(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    run_state["alias"] = "omics-analysis-team"
    run_state["omics_track"] = "tenx-gex"
    run_state["final_label"] = "Compact standard workflow"
    run_state["downgrade_reasons"] = ["synthetic compact 10x fixture"]
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    preflight_path = bundle / PREFLIGHT_FILE
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    preflight["requested_alias"] = "omics-analysis-team"
    preflight["requested_omics_track"] = "tenx-gex"
    preflight_path.write_text(json.dumps(preflight, indent=2), encoding="utf-8")

    lead_path = bundle / "lead_decision.json"
    lead = json.loads(lead_path.read_text(encoding="utf-8"))
    lead["requested_alias"] = "omics-analysis-team"
    lead["omics_subtrack"] = "tenx-gex"
    lead_path.write_text(json.dumps(lead, indent=2), encoding="utf-8")

    omics_manifest = {
        "schema_version": "2.0",
        "analysis_id": "omics-test",
        "track": "tenx-gex",
        "data_sources": [],
        "sample_sheet": "samples.csv",
        "assay_metadata": {
            "organism": "Homo sapiens",
            "genome_build": "GRCh38",
            "annotation_release": "GENCODE v44",
            "chemistry": "5prime",
            "cellranger_version": "8.0.0",
            "cellranger_command": "count",
        },
        "biological_unit_policy": {
            "unit": "donor",
            "replicate_key": "donor_id",
            "pseudobulk_required": True,
            "pseudobulk_policy": "donor-aware pseudobulk for cross-sample DE",
        },
        "contrast_or_endpoint": "high vs low expression",
        "software_versions": ["cellranger 8.0.0"],
        "qc_decisions": {
            "cell_calling_method": "Cell Ranger filtered matrix plus emptyDrops review",
            "ambient_rna_method": "SoupX planned",
            "doublet_method": "scDblFinder planned",
            "empty_droplet_method": "DropletUtils emptyDrops planned",
        },
        "de_strategy": {
            "cross_sample_method": "pseudobulk DESeq2",
            "multiplicity_method": "BH-FDR",
        },
        "generated_artifacts": {
            "web_summary_html": "web_summary.html",
            "filtered_feature_bc_matrix": "filtered_feature_bc_matrix",
            "raw_feature_bc_matrix": "raw_feature_bc_matrix"
        },
        "review_status": {
            "code_review": "not-run",
            "provenance_review": "not-run",
            "biostats_review": "not-run",
        },
    }
    (bundle / "omics_run_manifest.json").write_text(json.dumps(omics_manifest, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "SCHEMA_VALIDATION_FAILED" in combined_output(result)
    assert "molecule_info_h5" in combined_output(result)


@pytest.mark.parametrize(
    ("track", "artifact_key"),
    [
        ("tenx-citeseq", "feature_barcode_matrix"),
        ("tenx-vdj", "vdj_clonotypes"),
        ("tenx-multiome", "fragments_tsv_gz"),
    ],
)
def test_p2_tenx_subtracks_require_track_specific_artifacts(
    tmp_path: Path,
    track: str,
    artifact_key: str,
) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    write_omics_track_context(bundle, track)
    omics_manifest = valid_tenx_manifest(track)
    generated_artifacts = omics_manifest["generated_artifacts"]
    assert isinstance(generated_artifacts, dict)
    generated_artifacts.pop(artifact_key)
    (bundle / "omics_run_manifest.json").write_text(json.dumps(omics_manifest, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "SCHEMA_VALIDATION_FAILED" in combined_output(result)
    assert artifact_key in combined_output(result)


def test_tool_ledger_execution_governance_fields_are_policy_checked(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    ledger_path = bundle / "tool_call_ledger.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger["calls"] = [
        {
            "call_id": "TC-GOV-001",
            "tool_id": "pubmed-ncbi-entrez",
            "status": "success",
            "inputs_digest": "synthetic sensitive query",
            "allowed_data_class": "public-only",
            "actual_data_class": "deidentified-human",
            "query_redaction_applied": False,
            "runtime_surface": "mcp_connector",
            "network_boundary": "authenticated-connector",
            "output_ref": "results_integration:RI-ROW-001",
            "retrieval_date": "2026-07-07",
            "affected_claim_ids": ["CL-001"],
        }
    ]
    ledger_path.write_text(json.dumps(ledger, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)
    output = combined_output(result)

    assert result.returncode == 1
    assert "TOOL_CALL_DATA_CLASS_EXCEEDS_ALLOWED_SCOPE" in output
    assert "TOOL_CALL_MCP_SERVER_NAME_REQUIRED" in output
    assert "TOOL_CALL_PRIVACY_APPROVAL_REQUIRED" in output
    assert "TOOL_CALL_QUERY_REDACTION_REQUIRED" in output
    assert "TOOL_CALL_PRIVACY_NETWORK_BOUNDARY_BLOCK" in output


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


def test_compact_standard_label_requires_formal_artifacts(tmp_path: Path) -> None:
    final_text = tmp_path / "final.md"
    final_text.write_text("Final workflow label: Compact standard workflow\n", encoding="utf-8")

    result = run_validator_args("--final-text", str(final_text))

    output = combined_output(result)
    assert result.returncode == 1
    assert "COMPACT_WORKFLOW_REQUIRES_ARTIFACT" in output
    assert PREFLIGHT_FILE in output
    assert "source_corpus.json" in output
    assert "claim_ledger.json" in output
    assert "post_write_validation.json" in output


def test_full_protocol_label_in_final_text_requires_run_state(tmp_path: Path) -> None:
    final_text = tmp_path / "final.md"
    final_text.write_text("Final workflow label: Full protocol followed\n", encoding="utf-8")

    result = run_validator_args("--final-text", str(final_text))

    output = combined_output(result)
    assert result.returncode == 1
    assert "FULL_PROTOCOL_REQUIRES_RUN_STATE" in output
    assert "FULL_PROTOCOL_REQUIRES_PREFLIGHT" in output
    assert "FULL_PROTOCOL_REQUIRES_POST_WRITE" in output


def test_full_protocol_requires_complete_bundle_artifacts(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    for filename in ("source_corpus.json", "claim_ledger.json", "stage_evaluation.json", "final.md"):
        (bundle / filename).unlink()

    result = run_validator_path(bundle)

    output = combined_output(result)
    assert result.returncode == 1
    assert "FULL_PROTOCOL_REQUIRES_SOURCE_CORPUS" in output
    assert "FULL_PROTOCOL_REQUIRES_CLAIM_LEDGER" in output
    assert "FULL_PROTOCOL_REQUIRES_STAGE_EVALUATION" in output
    assert "FULL_PROTOCOL_REQUIRES_FINAL_TEXT" in output


def test_full_protocol_missing_canonical_preflight_fails(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    (bundle / PREFLIGHT_FILE).unlink()

    result = run_validator_path(bundle)

    output = combined_output(result)
    assert result.returncode == 1
    assert "FULL_PROTOCOL_REQUIRES_PREFLIGHT" in output
    assert PREFLIGHT_FILE in output


def test_require_label_enforces_full_protocol_even_without_declared_label(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    run_state["final_label"] = "Partial workflow; formal gates skipped"
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    result = run_validator_args("--bundle", str(bundle), "--require-label", "Full protocol followed")

    output = combined_output(result)
    assert result.returncode == 1
    assert "REQUIRED_LABEL_MISMATCH" in output


def test_negated_full_protocol_label_does_not_trigger_full_policy(tmp_path: Path) -> None:
    final_text = tmp_path / "final.md"
    final_text.write_text(
        "Final workflow label: Compact standard workflow\n"
        "This is not labeled Full protocol followed because independent review was not run.\n",
        encoding="utf-8",
    )

    result = run_validator_args("--final-text", str(final_text))

    output = combined_output(result)
    assert result.returncode == 1
    assert "COMPACT_WORKFLOW_REQUIRES_ARTIFACT" in output
    assert "FULL_PROTOCOL_REQUIRES_" not in output


def test_complete_spawned_review_lane_requires_actual_instance(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    run_state.pop("spawned_agent_instances")
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "SPAWNED_LANE_MISSING_INSTANCE" in combined_output(result)


@pytest.mark.parametrize("agent_id", spawnable_agent_ids())
def test_each_spawnable_agent_instance_contract_passes_validator(tmp_path: Path, agent_id: str) -> None:
    bundle = tmp_path / agent_id
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    run_state["spawned_review_lanes"] = [
        {
            "role": agent_id,
            "status": "complete",
            "rationale": f"{agent_id} synthetic spawned reviewer smoke check",
            "ledger_handoff": f"{agent_id} handoff accepted into CL-001",
        }
    ]
    run_state["spawned_agent_instances"] = [
        {
            "instance_id": f"BMAT-SPAWN-{agent_id}",
            "agent_id": agent_id,
            "execution_surface": "spawned_subagent",
            "spawn_tool": "synthetic-contract-smoke",
            "thread_or_task_id": f"synthetic-{agent_id}",
            "parent_run_id": "run-valid-001",
            "status": "complete",
            "input_scope": "synthetic CL-001/S-001 full-protocol fixture",
            "output_artifact": f"review/{agent_id}.md",
            "checks_run": ["spawn contract smoke", "ledger handoff smoke"],
            "ledger_handoff": f"{agent_id} handoff accepted into CL-001",
        }
    ]
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")
    write_spawned_output_artifact(bundle, f"review/{agent_id}.md")

    post_write_path = bundle / "post_write_validation.json"
    post_write = json.loads(post_write_path.read_text(encoding="utf-8"))
    post_write["independent_review_status"] = f"spawned_subagent {agent_id} complete"
    post_write_path.write_text(json.dumps(post_write, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    assert result.returncode == 0, combined_output(result)
    assert "VALIDATION_PASSED" in combined_output(result)


def test_full_protocol_requires_complete_independent_instance(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    run_state["spawned_review_lanes"] = []
    run_state.pop("spawned_agent_instances")
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "FULL_PROTOCOL_REQUIRES_INDEPENDENT_INSTANCE" in combined_output(result)


def test_failed_spawned_instance_does_not_satisfy_full_protocol(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    run_state["spawned_review_lanes"] = []
    run_state["spawned_agent_instances"][0]["status"] = "failed"
    run_state["spawned_agent_instances"][0]["failure_or_downgrade_reason"] = "synthetic failed reviewer"
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "FULL_PROTOCOL_REQUIRES_INDEPENDENT_INSTANCE" in combined_output(result)


def test_unknown_spawned_instance_agent_fails(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    run_state["spawned_agent_instances"][0]["agent_id"] = "ghost-reviewer"
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "SPAWNED_INSTANCE_UNKNOWN_AGENT" in combined_output(result)


def test_complete_spawned_instance_requires_output_artifact(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    run_state["spawned_agent_instances"][0]["output_artifact"] = ""
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "SPAWNED_INSTANCE_MISSING_OUTPUT_ARTIFACT" in combined_output(result)


def test_complete_spawned_instance_requires_existing_output_artifact(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    run_state["spawned_agent_instances"][0]["output_artifact"] = "review/missing-output.md"
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "SPAWNED_INSTANCE_OUTPUT_ARTIFACT_MISSING" in combined_output(result)


def test_complete_spawned_instance_requires_execution_evidence(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    run_state["spawned_agent_instances"][0]["input_scope"] = " "
    run_state["spawned_agent_instances"][0]["checks_run"] = []
    run_state["spawned_agent_instances"][0]["ledger_handoff"] = ""
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)
    output = combined_output(result)

    assert result.returncode == 1
    assert "SPAWNED_INSTANCE_MISSING_INPUT_SCOPE" in output
    assert "SPAWNED_INSTANCE_MISSING_CHECKS_RUN" in output
    assert "SPAWNED_INSTANCE_MISSING_LEDGER_HANDOFF" in output


def test_complete_spawned_instance_rejects_non_independent_surface(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    run_state["spawned_agent_instances"][0]["execution_surface"] = "same_model_inline"
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)
    output = combined_output(result)

    assert result.returncode == 1
    assert "SPAWNED_INSTANCE_INVALID_EXECUTION_SURFACE" in output
    assert "SPAWNED_LANE_MISSING_INSTANCE" in output


def test_complete_spawned_review_lane_requires_ledger_handoff(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    run_state["spawned_review_lanes"][0]["ledger_handoff"] = ""
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "SPAWNED_LANE_MISSING_LEDGER_HANDOFF" in combined_output(result)


def test_duplicate_complete_spawned_review_lane_fails(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    run_state["spawned_review_lanes"].append(dict(run_state["spawned_review_lanes"][0]))
    run_state["spawned_agent_instances"].append(
        {
            **run_state["spawned_agent_instances"][0],
            "instance_id": "BMAT-SPAWN-002",
        }
    )
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "SPAWNED_LANE_DUPLICATE_ROLE" in combined_output(result)


def test_malformed_spawned_review_lanes_shape_returns_policy_error(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    run_state["spawned_review_lanes"] = {"role": "citation-verifier"}
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    output = combined_output(result)
    assert result.returncode == 1
    assert "INVALID_SPAWNED_REVIEW_LANES" in output
    assert "Traceback" not in output


def test_duplicate_spawned_instance_id_fails(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    run_state["spawned_agent_instances"].append(dict(run_state["spawned_agent_instances"][0]))
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "SPAWNED_INSTANCE_DUPLICATE_ID" in combined_output(result)


def test_malformed_spawned_instances_shape_returns_policy_error(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    run_state["spawned_agent_instances"] = {"agent_id": "citation-verifier"}
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    assert result.returncode == 1
    output = combined_output(result)
    assert "INVALID_SPAWNED_AGENT_INSTANCES" in output
    assert "Traceback" not in output


def test_omics_run_reviewer_budget_zero_without_exception_fails(tmp_path: Path) -> None:
    bundle = make_omics_run_bundle(
        tmp_path,
        spawned_review_plan={
            "allowed": False,
            "budget": 0,
            "selected_roles": [],
            "rationale": "Inline deterministic checks were considered sufficient.",
        },
        downgrade_reasons=["No spawned independent reviewer."],
    )

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "OMICS_RUN_REVIEWER_SPAWN_REQUIRED" in combined_output(result)


def test_omics_run_reviewer_budget_zero_with_runtime_exception_warns(tmp_path: Path) -> None:
    bundle = make_omics_run_bundle(
        tmp_path,
        spawned_review_plan={
            "allowed": False,
            "budget": 0,
            "selected_roles": [],
            "rationale": "Spawned-subagent support unavailable in this runtime.",
        },
        skipped_role_outputs=[
            {
                "role": "omics-code-reviewer",
                "reason": "spawned-subagent support unavailable; compact inline-only downgrade recorded",
            }
        ],
        downgrade_reasons=["spawned-subagent support unavailable; downgraded to Compact standard workflow"],
    )

    result = run_validator_path(bundle)

    assert result.returncode == 0, combined_output(result)
    assert "OMICS_RUN_REVIEWER_SPAWN_SKIPPED_WITH_DOWNGRADE" in combined_output(result)


def test_omics_run_requires_core_reviewer_role(tmp_path: Path) -> None:
    bundle = make_omics_run_bundle(
        tmp_path,
        spawned_review_plan={
            "allowed": True,
            "budget": 1,
            "selected_roles": ["citation-verifier"],
            "rationale": "Incorrectly selected a non-core reviewer for omics run.",
        },
    )

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "OMICS_RUN_CORE_REVIEWER_REQUIRED" in combined_output(result)


def test_omics_run_core_reviewer_instance_passes(tmp_path: Path) -> None:
    bundle = make_omics_run_bundle(
        tmp_path,
        spawned_review_plan={
            "allowed": True,
            "budget": 1,
            "selected_roles": ["omics-code-reviewer"],
            "rationale": "Core reviewer spawned after S1-S3 locks.",
        },
        spawned_review_lanes=[
            {
                "role": "omics-code-reviewer",
                "status": "complete",
                "rationale": "Reviewed code, leakage, and reproducibility.",
                "ledger_handoff": "CL-001 code/provenance checks accepted",
            }
        ],
        spawned_agent_instances=[
            {
                "instance_id": "OMICS-CODE-REVIEW-001",
                "agent_id": "omics-code-reviewer",
                "execution_surface": "spawned_subagent",
                "spawn_tool": "multi_agent_v1.spawn_agent",
                "thread_or_task_id": "synthetic-omics-code-review",
                "parent_run_id": "omics-run-fixture",
                "status": "complete",
                "input_scope": "synthetic omics scripts and result tables",
                "output_artifact": "review/omics-code-reviewer.md",
                "checks_run": ["script reproducibility", "raw-data safety", "leakage review"],
                "ledger_handoff": "CL-001 code/provenance checks accepted",
            }
        ],
        independent_review_status="spawned_subagent omics-code-reviewer complete",
    )
    write_spawned_output_artifact(bundle, "review/omics-code-reviewer.md")

    result = run_validator_path(bundle)

    assert result.returncode == 0, combined_output(result)
    assert "VALIDATION_PASSED" in combined_output(result)


def test_valid_team_level_selective_dag_passes(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    add_valid_team_dag(run_state)
    write_valid_team_workflow_dag(bundle)
    write_team_output_artifacts(bundle)
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")
    sync_lead_decision(bundle)

    result = run_validator_path(bundle)

    assert result.returncode == 0, combined_output(result)
    assert "ERROR" not in result.stdout


def test_complete_team_output_artifact_path_must_exist(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    add_valid_team_dag(run_state)
    write_valid_team_workflow_dag(bundle)
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "TEAM_OUTPUT_PATH_MISSING" in combined_output(result)


def test_workflow_dag_mode_must_match_run_state(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    add_valid_team_dag(run_state)
    write_valid_team_workflow_dag(bundle)
    workflow_dag_path = bundle / "workflow_dag.json"
    workflow_dag = json.loads(workflow_dag_path.read_text(encoding="utf-8"))
    workflow_dag["mode"] = "run"
    workflow_dag_path.write_text(json.dumps(workflow_dag, indent=2), encoding="utf-8")
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "WORKFLOW_DAG_MODE_MISMATCH" in combined_output(result)


def test_workflow_dag_id_must_match_run_state_when_declared(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    add_valid_team_dag(run_state)
    run_state["workflow_dag_id"] = "evidence-audit-team.audit.synthetic-team-dag"
    write_valid_team_workflow_dag(bundle)
    workflow_dag_path = bundle / "workflow_dag.json"
    workflow_dag = json.loads(workflow_dag_path.read_text(encoding="utf-8"))
    workflow_dag["workflow_id"] = "evidence-audit-team.run.synthetic-team-dag"
    workflow_dag_path.write_text(json.dumps(workflow_dag, indent=2), encoding="utf-8")
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "WORKFLOW_DAG_ID_MISMATCH" in combined_output(result)


def test_workflow_dag_track_must_match_declared_omics_track(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    run_state["alias"] = "omics-analysis-team"
    run_state["workflow_dag_id"] = "omics-analysis-team.audit"
    run_state["omics_track"] = "survival"
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    preflight_path = bundle / PREFLIGHT_FILE
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    preflight["requested_alias"] = "omics-analysis-team"
    preflight["requested_omics_track"] = "survival"
    preflight_path.write_text(json.dumps(preflight, indent=2), encoding="utf-8")

    manifest = {
        "schema_version": "2.0",
        "analysis_id": "survival-track-fixture",
        "workflow_run_id": run_state["run_id"],
        "track": "survival",
        "data_sources": [],
        "sample_sheet": "samples.tsv",
        "assay_metadata": {
            "organism": "Homo sapiens",
            "genome_build": "not-applicable",
            "annotation_release": "fixture",
        },
        "biological_unit_policy": {
            "unit": "sample",
            "replicate_key": "sample_id",
            "pseudobulk_required": False,
        },
        "contrast_or_endpoint": "OS",
        "software_versions": ["fixture"],
        "qc_decisions": {},
        "de_strategy": {
            "cross_sample_method": "CoxPH",
            "multiplicity_method": "BH-FDR",
        },
        "generated_artifacts": {},
        "review_status": {
            "code_review": "fixture",
            "provenance_review": "fixture",
            "biostats_review": "fixture",
        },
    }
    (bundle / "omics_run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    workflow_dag = {
        "workflow_id": "omics-analysis-team.audit",
        "runtime": "codex",
        "alias": "omics-analysis-team",
        "mode": "audit",
        "track": "omics",
        "nodes": [
            {
                "id": "S0",
                "agent": "protocol-context-locker",
                "outputs": ["runtime_capability_preflight"],
                "blocking": True,
            }
        ],
        "release_gates": ["bmat_validate"],
    }
    (bundle / "workflow_dag.json").write_text(json.dumps(workflow_dag, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "WORKFLOW_DAG_TRACK_MISMATCH" in combined_output(result)


def test_workflow_dag_track_required_when_omics_track_declared(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    write_omics_track_context(bundle, "tenx-gex")

    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    run_state["mode"] = "run"
    run_state["workflow_dag_id"] = "omics-analysis-team.run"
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")
    sync_lead_decision(bundle)

    omics_manifest = valid_tenx_manifest("tenx-gex")
    omics_manifest["workflow_run_id"] = run_state["run_id"]
    (bundle / "omics_run_manifest.json").write_text(json.dumps(omics_manifest, indent=2), encoding="utf-8")

    workflow_dag = {
        "workflow_id": "omics-analysis-team.run",
        "runtime": "codex",
        "alias": "omics-analysis-team",
        "mode": "run",
        "nodes": [
            {
                "id": "S0",
                "agent": "protocol-context-locker",
                "outputs": ["runtime_capability_preflight"],
                "blocking": True,
            }
        ],
        "release_gates": ["bmat_validate"],
    }
    (bundle / "workflow_dag.json").write_text(json.dumps(workflow_dag, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "WORKFLOW_DAG_TRACK_MISSING" in combined_output(result)


def test_complete_team_spawn_lane_requires_team_output_artifact(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    add_valid_team_dag(run_state)
    run_state["team_output_artifacts"] = run_state["team_output_artifacts"][:1]
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "TEAM_SPAWN_LANE_MISSING_OUTPUT_ARTIFACT" in combined_output(result)


def test_team_nested_spawn_requires_explicit_approval(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    add_valid_team_dag(run_state)
    run_state["team_spawn_lanes"][0]["nested_spawn_used"] = True
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "TEAM_NESTED_SPAWN_NOT_ALLOWED" in combined_output(result)


def test_team_phase_dependency_must_resolve_to_prior_complete_output(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    add_valid_team_dag(run_state)
    run_state["team_spawn_lanes"][1]["depends_on"] = ["missing-team"]
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "TEAM_DAG_DEPENDENCY_UNRESOLVED" in combined_output(result)


def test_malformed_team_output_artifacts_shape_returns_policy_error(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    run_state["team_output_artifacts"] = {"team": "idea-discovery-team"}
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    output = combined_output(result)
    assert result.returncode == 1
    assert "INVALID_TEAM_OUTPUT_ARTIFACTS" in output
    assert "Traceback" not in output


def test_team_output_dependency_must_resolve_to_complete_artifact(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    add_valid_team_dag(run_state)
    run_state["team_output_artifacts"][1]["depends_on_outputs"] = ["missing-output"]
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "TEAM_OUTPUT_DEPENDENCY_UNRESOLVED" in combined_output(result)


def test_duplicate_complete_team_spawn_lane_fails(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    add_valid_team_dag(run_state)
    run_state["team_spawn_lanes"].append(dict(run_state["team_spawn_lanes"][0]))
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "TEAM_SPAWN_LANE_DUPLICATE" in combined_output(result)


def test_duplicate_complete_team_output_key_fails(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    add_valid_team_dag(run_state)
    duplicate_output = dict(run_state["team_output_artifacts"][0])
    duplicate_output["artifact_id"] = "TEAM-IDEA-DUPLICATE"
    duplicate_output["path"] = "team-outputs/idea-discovery-team-duplicate.md"
    run_state["team_output_artifacts"].append(duplicate_output)
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "TEAM_OUTPUT_DUPLICATE" in combined_output(result)


def test_duplicate_complete_team_output_artifact_id_fails(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    add_valid_team_dag(run_state)
    run_state["team_output_artifacts"][1]["artifact_id"] = "TEAM-IDEA-001"
    run_state["team_output_artifacts"][1]["depends_on_outputs"] = []
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "TEAM_OUTPUT_DUPLICATE_ARTIFACT_ID" in combined_output(result)


def test_team_output_dependency_cannot_self_reference(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    add_valid_team_dag(run_state)
    run_state["team_output_artifacts"][1]["depends_on_outputs"] = ["TEAM-EXPERIMENT-001"]
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "TEAM_OUTPUT_DEPENDENCY_SELF_REFERENCE" in combined_output(result)


def test_team_output_dependency_must_reference_prior_phase(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    add_valid_team_dag(run_state)
    run_state["team_output_artifacts"][0]["depends_on_outputs"] = ["TEAM-EXPERIMENT-001"]
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "TEAM_OUTPUT_DEPENDENCY_ORDER_INVALID" in combined_output(result)


def test_missing_run_state_required_field_fails_without_jsonschema(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    del run_state["final_label"]
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    blocker = tmp_path / "no_jsonschema"
    blocker.mkdir()
    (blocker / "jsonschema.py").write_text('raise ImportError("blocked by test")\n', encoding="utf-8")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(blocker) + os.pathsep + env.get("PYTHONPATH", "")

    result = run_validator_path_with_env(bundle, env)

    output = combined_output(result)
    assert result.returncode == 1
    assert "SCHEMA_VALIDATION_SKIPPED" in output
    assert "RUN_STATE_REQUIRED_FIELD_MISSING" in output
    assert "final_label" in output
    assert "Traceback" not in output
