#!/usr/bin/env python3
"""Create and optionally validate a BMAT workflow bundle.

The runner is intentionally local. It scaffolds deterministic artifacts,
selects a machine-readable workflow DAG, and can export a Markdown workbench.
It does not call external models or databases.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

import bmat_init_bundle


SKILL_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS_ROOT = SKILL_ROOT / "workflows"
DOMAIN_PACKS_ROOT = SKILL_ROOT / "domain-packs"
VALIDATOR = SKILL_ROOT / "scripts" / "bmat_validate.py"
TOOL_LEDGER_CHECK = SKILL_ROOT / "scripts" / "bmat_tool_ledger_check.py"
BUNDLE_MANIFEST = SKILL_ROOT / "scripts" / "bmat_bundle_manifest.py"
OMICS_TRACKS = (
    "bulk-rnaseq",
    "tenx-gex",
    "tenx-cellplex",
    "tenx-citeseq",
    "tenx-vdj",
    "tenx-multiome",
    "single-cell-other",
    "survival",
    "multi-omics",
    "other",
    "not-applicable",
)
TENX_TRACKS = {"tenx-gex", "tenx-cellplex", "tenx-citeseq", "tenx-vdj", "tenx-multiome"}
AMBIGUOUS_OMICS_TRACKS = {"not-applicable", "track_ambiguous", "ambiguous", ""}


def available_domain_packs() -> tuple[str, ...]:
    if not DOMAIN_PACKS_ROOT.exists():
        return ("generic-biomedical",)
    packs = tuple(sorted(path.name for path in DOMAIN_PACKS_ROOT.iterdir() if path.is_dir()))
    return packs or ("generic-biomedical",)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a local BMAT scaffold workflow.")
    parser.add_argument("--alias", choices=bmat_init_bundle.WORKFLOWS, required=True)
    parser.add_argument("--mode", choices=bmat_init_bundle.MODES, default="standard")
    parser.add_argument("--tier", choices=("compact", "full"), default="compact")
    parser.add_argument("--track", choices=OMICS_TRACKS, help="Requested omics subtrack for omics-analysis-team runs.")
    parser.add_argument("--question", required=True, help="Locked research question or audit object.")
    parser.add_argument("--out", type=Path, required=True, help="Output bundle directory.")
    parser.add_argument("--domain-pack", choices=available_domain_packs(), default="generic-biomedical")
    parser.add_argument("--dry-run", action="store_true", help="Create scaffold artifacts only.")
    parser.add_argument("--validate", action="store_true", help="Run validator and tool ledger checks after scaffolding.")
    parser.add_argument("--export", choices=["none", "markdown"], default="none")
    parser.add_argument("--force", action="store_true", help="Overwrite existing scaffold files.")
    return parser.parse_args()


def write_json(path: Path, payload: dict[str, Any], force: bool) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"{path} exists; use --force to overwrite scaffold files")
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def write_text(path: Path, text: str, force: bool) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"{path} exists; use --force to overwrite scaffold files")
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_results_integration(run_id: str, version: str) -> dict[str, Any]:
    return {
        "schema_version": "2.0",
        "integration_id": f"ri-{run_id}",
        "plugin_version": version,
        "workflow_run_id": run_id,
        "created_at": utc_now(),
        "source_corpus_lock": "scaffold-only",
        "input_artifacts": [],
        "tool_use_log": [],
        "rows": [
            {
                "result_id": "RI-SCAFFOLD-001",
                "result_type": "other",
                "source_ref": "not-applicable",
                "claim_ids": ["CLAIM-SCAFFOLD-PLACEHOLDER"],
                "status": "not-reviewed",
                "evidence_direction": "not-applicable",
                "confidence": "not-assessed",
                "interpretation": "Scaffold placeholder; replace with real result-to-claim mapping before release.",
                "limitations": "No tool or reviewer output has been integrated yet.",
                "ledger_action": "no-change",
                "reviewer_or_human_gate": "not-run"
            }
        ],
        "final_claim_policy": "blocked",
        "human_review_status": "pending",
        "release_notes": ["scaffold placeholder; not release-ready"]
    }


def default_tool_call_ledger(run_id: str, version: str) -> dict[str, Any]:
    return {
        "schema_version": "2.0",
        "ledger_id": f"tcl-{run_id}",
        "plugin_version": version,
        "workflow_run_id": run_id,
        "created_at": utc_now(),
        "calls": []
    }


def default_source_verification(run_id: str, version: str) -> dict[str, Any]:
    return {
        "schema_version": "2.0",
        "verification_id": f"sv-{run_id}",
        "plugin_version": version,
        "workflow_run_id": run_id,
        "checked_at": utc_now(),
        "rows": [],
    }


def default_claim_support_matrix(run_id: str, version: str) -> dict[str, Any]:
    return {
        "schema_version": "2.0",
        "support_matrix_id": f"csm-{run_id}",
        "plugin_version": version,
        "workflow_run_id": run_id,
        "created_at": utc_now(),
        "rows": [],
    }


def default_omics_metadata_check(run_id: str, version: str, track: str) -> dict[str, Any]:
    return {
        "schema_version": "2.0",
        "check_id": f"omc-{run_id}",
        "plugin_version": version,
        "workflow_run_id": run_id,
        "checked_at": utc_now(),
        "track": track,
        "status": "block",
        "blocking_issues": [
            "scaffold placeholder; run bmat_omics_metadata_check.py after locking metadata and generated artifact paths"
        ],
        "warnings": [],
        "artifact_refs": [],
        "claim_ids_affected": [],
        "downgrade_recommendations": [
            "do not upgrade omics claims until metadata and artifact consistency checks pass"
        ],
    }


def default_experiment_design(run_id: str, version: str, question: str) -> dict[str, Any]:
    return {
        "schema_version": "2.0",
        "design_id": f"exp-{run_id}",
        "workflow_run_id": run_id,
        "plugin_version": version,
        "created_at": utc_now(),
        "design_stage": "exploratory",
        "recommendation_confidence": "low",
        "decision_authority": "research-assistance-only",
        "hypothesis": question,
        "experimental_objective": "TBD: define the bounded experimental objective before execution",
        "primary_estimand": {
            "population_or_model": "not yet determined",
            "treatment_or_exposure": "not yet determined",
            "comparator": "not yet determined",
            "outcome": "not yet determined",
            "summary_measure": "not yet determined",
        },
        "primary_endpoint": {
            "endpoint_id": "endpoint-not-yet-determined",
            "name": "not yet determined",
            "measurement_scale": "other",
            "measurement_unit": "not yet determined",
            "assessment_timepoint": "not yet determined",
            "direction_of_benefit": "not-applicable",
        },
        "secondary_endpoints": [],
        "expected_effect_size": {
            "measure": "not yet determined",
            "value": None,
            "unit": "not yet determined",
            "direction": "not-applicable",
            "assumption_basis": "feasibility-bound",
            "rationale": "No effect-size assumption has been supplied; release remains blocked.",
            "source_ids": [],
        },
        "variance_or_event_rate_assumption": {
            "assumption_type": "other",
            "value": None,
            "unit": "not yet determined",
            "assumption_basis": "feasibility-bound",
            "rationale": "No variance or event-rate assumption has been supplied; release remains blocked.",
            "source_ids": [],
        },
        "alpha": None,
        "power": None,
        "sidedness": "not-applicable",
        "planned_n": None,
        "dropout_or_failure_allowance": None,
        "positive_controls": ["not yet determined"],
        "negative_controls": ["not yet determined"],
        "vehicle_or_mock_controls": ["not yet determined"],
        "biological_replicates": {
            "planned_n": None,
            "allocation": "not yet determined",
            "rationale": "No biological-unit count has been justified; release remains blocked.",
        },
        "technical_replicates": {
            "planned_n": 0,
            "rationale": "Technical replicate handling has not yet been determined.",
        },
        "randomization_unit": "not yet determined",
        "analysis_unit": "not yet determined",
        "biological_unit": "not yet determined",
        "unit_mismatch_handling": None,
        "randomization_plan": {
            "planned": False,
            "method_or_reason": "not yet determined",
            "allocation_concealment_or_reason": "not yet determined",
        },
        "blocking_factors": [],
        "blinding_plan": {
            "planned": False,
            "masked_roles": [],
            "method_or_reason": "not yet determined",
        },
        "exclusion_criteria": ["not yet determined"],
        "confounders": ["not yet determined"],
        "causal_kill_tests": ["not yet determined"],
        "statistical_plan": {
            "model": "not yet determined",
            "covariates": [],
            "clustering_or_repeated_measures": "not yet determined",
            "effect_size_reporting": "not yet determined",
        },
        "multiplicity_plan": {
            "method": "not-assessed",
            "family_definition": "not yet determined",
            "alpha_allocation": "not yet determined",
            "rationale": "Multiplicity handling must be specified before release.",
        },
        "interim_analysis": {
            "planned": False,
            "timing_or_reason": "not yet determined",
            "alpha_spending_or_reason": "not yet determined",
        },
        "stopping_rule": {
            "rule_type": "not-assessed",
            "criteria": "not yet determined",
            "decision_authority": "responsible human investigator",
        },
        "sensitivity_analyses": [],
        "sample_size_method": "not yet determined",
        "sample_size_artifact_status": "not-produced",
        "sample_size_code_ref": None,
        "sample_size_output_ref": None,
        "sample_size_output_sha256": None,
        "go_no_go_gates": ["not yet determined"],
        "design_scope": "conceptual",
        "safety_ethics_privacy_boundary": {
            "operational_details_included": False,
            "risk_triggers": ["none"],
            "required_oversight": ["responsible human investigator review before execution"],
            "privacy_boundary": "No private data are included in this scaffold.",
            "dual_use_boundary": "No operational dual-use detail is included in this scaffold.",
            "patent_sensitive_boundary": "No confidential or patent-sensitive detail is included in this scaffold.",
            "limitations": "BMAT provides research planning assistance only and does not grant experimental, clinical, IRB, IACUC, or IBC approval.",
            "bmat_role": "research-assistance-only",
        },
        "reagent_provenance_policy": "Verify reagent-specific claims with eligible source receipts or mark them unknown.",
        "reagent_specific_claims": [],
        "source_ids": [],
        "claim_ids_supported": [],
        "limitations": [
            "This is an incomplete scaffold. Missing quantitative assumptions remain unknown and are not release eligible."
        ],
    }


def default_review_artifact_manifest(run_id: str, version: str) -> dict[str, Any]:
    return {
        "schema_version": "2.0",
        "review_manifest_id": f"ram-{run_id}",
        "workflow_run_id": run_id,
        "plugin_version": version,
        "created_at": utc_now(),
        "review_instances": [],
    }


def selected_omics_track(args: argparse.Namespace) -> str:
    if args.track:
        return args.track
    if args.alias == "omics-analysis-team":
        if args.mode == "plan":
            return "track_ambiguous"
        return "not-applicable"
    return "not-applicable"


def cellranger_command_for_track(track: str) -> str:
    if track in {"tenx-cellplex", "tenx-citeseq"}:
        return "multi"
    if track == "tenx-vdj":
        return "vdj"
    if track == "tenx-multiome":
        return "arc"
    return "count"


def default_omics_manifest(run_id: str, version: str, track: str) -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "schema_version": "2.0",
        "analysis_id": f"omics-{run_id}",
        "workflow_run_id": run_id,
        "plugin_version": version,
        "created_at": utc_now(),
        "track": track,
        "data_sources": [],
        "sample_sheet": "TODO: lock sample sheet path or accession sample table before analysis",
        "assay_metadata": {
            "organism": "TODO",
            "genome_build": "TODO",
            "annotation_release": "TODO",
        },
        "biological_unit_policy": {
            "unit": "sample",
            "replicate_key": "TODO",
            "pseudobulk_required": False,
            "pseudobulk_policy": "TODO: justify for descriptive-only runs; use donor/sample-aware pseudobulk for cross-sample testing",
        },
        "contrast_or_endpoint": "TODO",
        "software_versions": ["TODO"],
        "qc_decisions": {},
        "de_strategy": {
            "cross_sample_method": "TODO",
            "multiplicity_method": "TODO",
        },
        "generated_artifacts": {},
        "review_status": {
            "code_review": "not-run",
            "provenance_review": "not-run",
            "biostats_review": "not-run",
        },
    }

    if track in TENX_TRACKS:
        manifest["assay_metadata"].update(
            {
                "chemistry": "TODO",
                "cellranger_version": "TODO",
                "cellranger_command": cellranger_command_for_track(track),
            }
        )
        manifest["biological_unit_policy"].update(
            {
                "unit": "donor",
                "donor_key": "TODO",
                "pseudobulk_required": True,
                "pseudobulk_policy": "Donor/sample-aware pseudobulk is required for cross-sample DE; cell-level tests are descriptive unless justified.",
                "cell_level_tests_limited_to": "descriptive markers, QC, and annotation support only",
            }
        )
        manifest["qc_decisions"].update(
            {
                "cell_calling_method": "TODO",
                "ambient_rna_method": "TODO",
                "doublet_method": "TODO",
                "empty_droplet_method": "TODO",
            }
        )
        manifest["generated_artifacts"].update(
            {
                "web_summary_html": "TODO",
                "filtered_feature_bc_matrix": "TODO",
                "raw_feature_bc_matrix": "TODO",
                "molecule_info_h5": "TODO",
            }
        )
        if track == "tenx-cellplex":
            manifest["assay_metadata"].update(
                {
                    "multiplexing_method": "CellPlex/CMO",
                    "sample_barcode_mapping_ref": "TODO",
                }
            )
            manifest["generated_artifacts"]["sample_barcode_mapping"] = "TODO"
        if track == "tenx-citeseq":
            manifest["assay_metadata"].update(
                {
                    "feature_reference_ref": "TODO",
                    "antibody_panel_ref": "TODO",
                }
            )
            manifest["generated_artifacts"].update(
                {
                    "feature_reference_csv": "TODO",
                    "feature_barcode_matrix": "TODO",
                }
            )
        if track == "tenx-vdj":
            manifest["assay_metadata"].update(
                {
                    "vdj_reference": "TODO",
                    "gex_linkage_key": "TODO",
                }
            )
            manifest["generated_artifacts"].update(
                {
                    "vdj_contig_annotations": "TODO",
                    "vdj_clonotypes": "TODO",
                }
            )
        if track == "tenx-multiome":
            manifest["assay_metadata"].update(
                {
                    "atac_reference": "TODO",
                    "feature_linkage_ref": "TODO",
                }
            )
            manifest["generated_artifacts"].update(
                {
                    "fragments_tsv_gz": "TODO",
                    "atac_peak_matrix": "TODO",
                    "arc_summary_html": "TODO",
                }
            )

    if track == "bulk-rnaseq":
        manifest["assay_metadata"].update(
            {
                "quantifier": "TODO",
                "transcriptome_reference": "TODO",
                "tx_to_gene_method": "TODO",
                "read_layout": "TODO",
            }
        )
        manifest["qc_decisions"].update(
            {
                "fastq_qc": "TODO",
                "multiqc_ref": "TODO",
                "low_count_filter": "TODO",
                "outlier_policy": "TODO",
            }
        )
        manifest["de_strategy"].update(
            {
                "design_formula": "TODO",
                "design_matrix_rank_checked": False,
                "count_model": "TODO",
            }
        )
        manifest["generated_artifacts"].update(
            {
                "multiqc_html": "TODO",
                "count_matrix": "TODO",
                "design_matrix": "TODO",
                "de_results_table": "TODO",
            }
        )
    return manifest


def select_workflow_dag(alias: str) -> dict[str, Any]:
    path = WORKFLOWS_ROOT / f"{alias}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def workflow_dag_for_run(alias: str, mode: str) -> dict[str, Any]:
    workflow_dag = copy.deepcopy(select_workflow_dag(alias))
    workflow_dag["mode"] = mode
    workflow_dag["workflow_id"] = f"{alias}.{mode}"
    return workflow_dag


def workflow_declared_outputs(workflow_dag: dict[str, Any]) -> set[str]:
    outputs: set[str] = set()
    for node in workflow_dag.get("nodes", []):
        if isinstance(node, dict):
            outputs.update(str(output) for output in node.get("outputs", []) if output)
    return outputs


def enrich_payloads(payloads: dict[str, dict[str, Any] | str], args: argparse.Namespace) -> None:
    version = bmat_init_bundle.plugin_version()
    run_state = payloads["run_state.json"]
    preflight = payloads["runtime_capability_preflight.json"]
    lead_decision = payloads["lead_decision.json"]
    assert isinstance(run_state, dict)
    assert isinstance(preflight, dict)
    assert isinstance(lead_decision, dict)
    run_id = str(run_state["run_id"])
    created_at = utc_now()
    workflow_dag = workflow_dag_for_run(args.alias, args.mode)
    omics_track = selected_omics_track(args)
    omics_track_locked = omics_track not in AMBIGUOUS_OMICS_TRACKS
    if args.alias == "omics-analysis-team" and not omics_track_locked:
        note = (
            "omics track is ambiguous; lock --track before run-mode execution"
            if args.mode == "run"
            else "omics track is ambiguous in plan mode; do not treat this scaffold as run-ready"
        )
        preflight_note = payloads["runtime_capability_preflight.json"]
        run_state_note = payloads["run_state.json"]
        assert isinstance(preflight_note, dict)
        assert isinstance(run_state_note, dict)
        preflight_note["omics_track_ambiguity_note"] = note
        run_state_note.setdefault("downgrade_reasons", []).append(note)
        if args.mode == "run":
            run_state_note["final_label"] = "Blocked"
            run_state_note["execution_strategy"] = "blocked"
    if omics_track_locked:
        workflow_dag["track"] = omics_track

    domain_pack_root = DOMAIN_PACKS_ROOT / args.domain_pack
    domain_profile = json.loads((domain_pack_root / "domain-pack.json").read_text(encoding="utf-8"))
    domain_version = str(domain_profile.get("domain_pack_version", "unknown"))
    domain_assumptions = list(domain_profile.get("domain_specific_assumptions", []))
    selection_reason = (
        "default domain-neutral pack for a request without an explicit specialty context"
        if args.domain_pack == "generic-biomedical"
        else "explicit specialty context selected by --domain-pack"
    )

    preflight["domain_pack"] = args.domain_pack
    preflight["selected_domain_pack"] = args.domain_pack
    preflight["domain_pack_version"] = domain_version
    preflight["selection_reason"] = selection_reason
    preflight["domain_specific_assumptions"] = domain_assumptions
    preflight["workflow_tier"] = args.tier
    preflight["requested_omics_track"] = omics_track
    preflight["domain_specific_failure_modes_loaded"] = (domain_pack_root / "failure-modes.md").exists()
    preflight["domain_assumptions_skipped"] = []
    preflight["workflow_dag_id"] = workflow_dag["workflow_id"]
    preflight["results_integration_required"] = True

    run_state["domain_pack"] = args.domain_pack
    run_state["selected_domain_pack"] = args.domain_pack
    run_state["domain_pack_version"] = domain_version
    run_state["domain_pack_selection_reason"] = selection_reason
    run_state["domain_specific_assumptions"] = domain_assumptions
    run_state["workflow_tier"] = args.tier
    run_state["omics_track"] = omics_track
    run_state["workflow_dag_id"] = workflow_dag["workflow_id"]
    run_state["results_integration_required"] = True
    run_state["tool_calls_used"] = []
    run_state["external_tools_used"] = []
    run_state["tool_backed_claim_ids"] = []
    run_state["result_backed_claim_ids"] = []
    run_state["stages"] = [
        {
            "id": node["id"],
            "required": bool(node.get("blocking", False)),
            "status": "block" if node.get("blocking", False) else "not-applicable",
            "evidence": "workflow DAG scaffold node; complete during execution",
            "depends_on": node.get("requires", []),
            "block_condition": "scaffold node not executed yet",
        }
        for node in workflow_dag["nodes"]
    ]

    lead_decision["workflow_run_id"] = run_id
    lead_decision["plugin_version"] = version
    lead_decision["created_at"] = created_at
    lead_decision["selected_domain_pack"] = args.domain_pack
    lead_decision["domain_pack_version"] = domain_version
    lead_decision["domain_pack_selection_reason"] = selection_reason
    lead_decision["domain_specific_assumptions"] = domain_assumptions
    lead_decision["requested_alias"] = args.alias
    lead_decision["selected_mode"] = args.mode
    lead_decision["workflow_tier"] = args.tier
    lead_decision["omics_subtrack"] = omics_track
    lead_decision["execution_strategy"] = run_state["execution_strategy"]
    lead_decision["spawned_review_plan"] = preflight["spawned_review_plan"]
    lead_decision["team_spawn_plan"] = preflight["team_spawn_plan"]
    lead_decision["post_team_audit_plan"] = preflight["post_team_audit_plan"]

    workflow_dag.update(
        {
            "schema_version": "2.0",
            "workflow_run_id": run_id,
            "plugin_version": version,
            "created_at": created_at,
        }
    )
    for filename, artifact_id_field in (
        ("run_state.json", "run_id"),
        ("runtime_capability_preflight.json", "runtime_capability_preflight_id"),
        ("lead_decision.json", "decision_id"),
        ("source_corpus.json", "corpus_id"),
        ("claim_ledger.json", "claim_ledger_id"),
        ("stage_evaluation.json", "evaluation_id"),
        ("post_write_validation.json", "validation_id"),
    ):
        artifact = payloads.get(filename)
        if not isinstance(artifact, dict):
            continue
        artifact["schema_version"] = "2.0"
        artifact["plugin_version"] = version
        if filename == "run_state.json":
            artifact["created_at"] = created_at
        else:
            artifact["workflow_run_id"] = run_id
            artifact["checked_at" if filename == "post_write_validation.json" else "created_at"] = created_at
        artifact.setdefault(artifact_id_field, f"{Path(filename).stem}-{run_id}")
    payloads["workflow_dag.json"] = workflow_dag
    payloads["results_integration.json"] = default_results_integration(run_id, version)
    payloads["tool_call_ledger.json"] = default_tool_call_ledger(run_id, version)
    declared_outputs = workflow_declared_outputs(workflow_dag)
    if "source_verification" in declared_outputs:
        payloads["source_verification.json"] = default_source_verification(run_id, version)
    if "claim_support_matrix" in declared_outputs:
        payloads["claim_support_matrix.json"] = default_claim_support_matrix(run_id, version)
    if "experiment_design" in declared_outputs:
        payloads["experiment_design.json"] = default_experiment_design(run_id, version, args.question)
    if "review_artifact_manifest" in declared_outputs:
        payloads["review_artifact_manifest.json"] = default_review_artifact_manifest(run_id, version)
    if "omics_metadata_check" in declared_outputs:
        payloads["omics_metadata_check.json"] = default_omics_metadata_check(run_id, version, omics_track)
    if omics_track_locked:
        payloads["omics_run_manifest.json"] = default_omics_manifest(run_id, version, omics_track)
    final_text = str(payloads.get("final.md", "")).rstrip()
    final_text = "\n".join(
        line
        for line in final_text.splitlines()
        if not line.lower().lstrip().startswith(("final workflow label:", "workflow label:"))
    ).rstrip()
    payloads["final.md"] = f"{final_text}\n\nFinal workflow label: {run_state['final_label']}\n"


def write_payloads(payloads: dict[str, dict[str, Any] | str], out: Path, force: bool) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for filename, payload in payloads.items():
        path = out / filename
        if isinstance(payload, str):
            write_text(path, payload, force)
        else:
            write_json(path, payload, force)


def markdown_from_json(title: str, path: Path) -> str:
    if not path.exists():
        return f"# {title}\n\nMissing: `{path.name}`\n"
    return f"# {title}\n\n```json\n{path.read_text(encoding='utf-8')}\n```\n"


def export_markdown_workbench(bundle: Path, force: bool) -> Path:
    run_state = json.loads((bundle / "run_state.json").read_text(encoding="utf-8"))
    run_id = str(run_state.get("run_id", "bmat-run"))
    reports = bundle / "reports" / run_id
    reports.mkdir(parents=True, exist_ok=True)
    files = {
        "index.md": (
            "# BMAT Research Workbench\n\n"
            f"- run_id: `{run_id}`\n"
            f"- workflow_alias: `{run_state.get('alias', '')}`\n"
            f"- final_label: `{run_state.get('final_label', '')}`\n"
            f"- domain_pack: `{run_state.get('domain_pack', '')}`\n\n"
            "Review the linked artifacts before upgrading final wording.\n"
        ),
        "protocol-lock.md": markdown_from_json("Protocol Lock", bundle / "run_state.json"),
        "runtime-capability-preflight.md": markdown_from_json("Runtime Capability Preflight", bundle / "runtime_capability_preflight.json"),
        "source-corpus.md": markdown_from_json("Source Corpus", bundle / "source_corpus.json"),
        "claim-ledger.md": markdown_from_json("Claim Ledger", bundle / "claim_ledger.json"),
        "results-integration.md": markdown_from_json("Results Integration", bundle / "results_integration.json"),
        "reviewer-objections.md": "# Reviewer Objections\n\nNo reviewer objections have been integrated in this scaffold.\n",
        "allowed-final-wording.md": "# Allowed Final Wording\n\nUse only claim-ledger `allowed_final_wording` entries after validation.\n",
        "downgrade-reasons.md": markdown_from_json("Downgrade Reasons", bundle / "run_state.json"),
        "next-experiment-gates.md": "# Next Experiment Gates\n\nFill from experiment-design or omics-stage evaluation outputs.\n"
    }
    for filename, text in files.items():
        path = reports / filename
        if path.exists() and not force:
            raise FileExistsError(f"{path} exists; use --force to overwrite")
        write_text(path, text, force=True)
    return reports


def run_check(command: list[str]) -> int:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(command, text=True, check=False, env=env)
    return result.returncode


def main() -> int:
    args = parse_args()
    payloads = bmat_init_bundle.build_payloads(args.alias, args.mode, args.question, args.out)
    enrich_payloads(payloads, args)
    write_payloads(payloads, args.out, args.force)

    print(f"BMAT workflow bundle created: {args.out.resolve()}")
    if args.export == "markdown":
        reports = export_markdown_workbench(args.out, args.force)
        print(f"BMAT markdown workbench exported: {reports.resolve()}")

    manifest_status = run_check([sys.executable, str(BUNDLE_MANIFEST), "--bundle", str(args.out)])
    if manifest_status:
        return manifest_status

    status = 0
    if args.validate:
        status = run_check([sys.executable, str(VALIDATOR), "--bundle", str(args.out), "--check-tool-ledger"])
        status = status or run_check([sys.executable, str(TOOL_LEDGER_CHECK), "--bundle", str(args.out)])
    if args.dry_run:
        print("Dry run complete: scaffold artifacts only; no external tools or models were called.")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
