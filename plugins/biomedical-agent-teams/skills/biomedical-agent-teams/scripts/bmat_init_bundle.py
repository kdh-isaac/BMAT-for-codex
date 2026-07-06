#!/usr/bin/env python3
"""Create a starter Biomedical Agent Teams artifact bundle.

The scaffold is intentionally conservative: it creates editable placeholders
that satisfy BMAT's artifact naming conventions without pretending that review
or validation has already happened.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


WORKFLOWS = (
    "biomedical-research-council",
    "idea-discovery-team",
    "omics-analysis-team",
    "evidence-audit-team",
    "experiment-design-team",
    "translational-scout-team",
)
MODES = ("quick", "standard", "deep", "audit", "plan", "run")
BUNDLE_FILES = (
    "runtime_capability_preflight.json",
    "run_state.json",
    "lead_decision.json",
    "source_corpus.json",
    "claim_ledger.json",
    "stage_evaluation.json",
    "post_write_validation.json",
    "final.md",
    "README.md",
)
UTF8_BOM = "\ufeff"
PLAYBOOK_BY_WORKFLOW = {
    "biomedical-research-council": "mechanism-review",
    "idea-discovery-team": "hypothesis-ranking",
    "omics-analysis-team": "omics-analysis",
    "evidence-audit-team": "evidence-audit",
    "experiment-design-team": "wet-lab-validation",
    "translational-scout-team": "clinical-translation",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a BMAT artifact bundle scaffold.")
    parser.add_argument("--workflow", choices=WORKFLOWS, required=True)
    parser.add_argument("--mode", choices=MODES, required=True)
    parser.add_argument("--out", type=Path, required=True, help="Output bundle directory.")
    parser.add_argument("--topic", default="TODO: replace with the locked research question or audit object.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing scaffold files.")
    return parser.parse_args()


def strip_bom(text: str) -> str:
    if text.startswith(UTF8_BOM):
        return text[len(UTF8_BOM) :]
    return text


def read_text_file(path: Path) -> str:
    return strip_bom(path.read_text(encoding="utf-8-sig"))


def plugin_version() -> str:
    version_path = Path(__file__).resolve().parents[1] / "VERSION"
    try:
        return read_text_file(version_path).strip()
    except FileNotFoundError:
        return "unknown"


def shell_family() -> str:
    for value in (os.environ.get("SHELL"), os.environ.get("COMSPEC")):
        if not value:
            continue
        shell = value.replace("\\", "/").rstrip("/").split("/")[-1].lower()
        if shell in {"bash", "zsh", "sh", "fish", "dash"}:
            return "bash" if shell in {"sh", "dash"} else shell
        if shell in {"powershell", "powershell.exe", "pwsh", "pwsh.exe"}:
            return "powershell"
        if shell in {"cmd", "cmd.exe"}:
            return "cmd"
    return "unknown"


def availability(value: bool | None) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "unknown"


def is_omics_run_scaffold(workflow: str, mode: str) -> bool:
    return workflow == "omics-analysis-team" and mode == "run"


def scaffold_review_skip_reason(workflow: str, mode: str) -> str:
    if is_omics_run_scaffold(workflow, mode):
        return (
            "scaffold default: spawned-subagent support unavailable in the initial scaffold; "
            "compact inline-only downgrade recorded until a core omics reviewer is completed"
        )
    return "scaffold default; fill during workflow execution"


def utc_now() -> tuple[str, str]:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    return now.isoformat().replace("+00:00", "Z"), now.date().isoformat()


def write_json(path: Path, payload: dict[str, Any], force: bool) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"{path} exists; use --force to overwrite scaffold files")
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str, force: bool) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"{path} exists; use --force to overwrite scaffold files")
    path.write_text(text, encoding="utf-8")


def default_omics_manifest(run_id: str) -> dict[str, Any]:
    return {
        "schema_version": "2.0",
        "analysis_id": f"omics-{run_id}",
        "workflow_run_id": run_id,
        "track": "single-cell-other",
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


def quoted_path(path: Path) -> str:
    return f'"{path}"'


def build_payloads(
    workflow: str,
    mode: str,
    topic: str,
    output_path: Path | None = None,
) -> dict[str, dict[str, Any] | str]:
    timestamp, date = utc_now()
    version = plugin_version()
    run_id = f"bmat-{workflow}-{mode}-{timestamp.replace(':', '').replace('-', '')}"
    corpus_id = f"corpus-{run_id}"
    review_skip_reason = scaffold_review_skip_reason(workflow, mode)
    validator_path = Path(__file__).resolve().parent / "bmat_validate.py"
    skill_root = Path(__file__).resolve().parents[1]
    bundle_path = output_path.resolve() if output_path is not None else Path("<this-directory>")
    validator_command = f"python {quoted_path(validator_path)} --bundle {quoted_path(bundle_path)}"
    runtime_id = f"rt-{run_id}"

    preflight = {
        "runtime_capability_preflight_id": runtime_id,
        "runtime_id": runtime_id,
        "codex_client": "codex",
        "plugin_version": version,
        "workspace_root": str(bundle_path),
        "host_os": platform.system() or "unknown",
        "path_style": "windows" if os.name == "nt" else "posix",
        "python_invocation": sys.executable,
        "shell_family": shell_family(),
        "codex_runtime_capability_surface": [
            "local_file_read",
            "local_file_write",
            "local_shell",
            "validator_cli",
        ],
        "capabilities": {
            "web_search_available": "unknown",
            "shell_available": availability(True),
            "file_read_available": availability(True),
            "file_write_available": availability(True),
            "network_available": "unknown",
        },
        "external_bio_tools_available": {},
        "validator_cli_available": availability(validator_path.exists()),
        "pairwise_ranking_script_available": availability((skill_root / "scripts" / "bmat_elo.py").exists()),
        "tool_registry_available": availability((skill_root / "references" / "tool-registry.json").exists()),
        "results_integration_available": availability(True),
        "iteration_budget_available": availability(True),
        "compute_budget": {
            "mode": mode,
            "iteration_budget": 1,
            "max_candidates": 1,
            "max_pairwise_matches": 0,
            "max_spawned_reviewers": 0,
            "max_external_queries": 0,
        },
        "validator_unavailable_reason": "none" if validator_path.exists() else "validator_unavailable_due_to_runtime",
        "spawned_subagents_supported": "unknown",
        "sandbox_profile": "unknown",
        "label_ceiling_due_to_runtime": "Contract-shaped artifact bundle",
        "downgrade_rule": (
            "Do not claim `Full protocol followed` until independent review, "
            "tool/result integration, and post-write validation gates pass."
        ),
        "requested_alias": workflow,
        "selected_mode": mode,
        "workflow_tier": "compact",
        "requested_omics_track": "single-cell-other" if workflow == "omics-analysis-team" else "not-applicable",
        "deliverable_type": "TODO: compact final, audit bundle, report, notebook, or generated file",
        "evidence_scope": {
            "source_types": [],
            "species_or_model": "TODO",
            "date_or_version_needs": f"created {date}; update retrieval dates before source-backed claims",
        },
        "risk_class": "low",
        "required_role_outputs": [],
        "skipped_role_outputs_with_reason": [
            {
                "role": "omics-code-reviewer" if is_omics_run_scaffold(workflow, mode) else "TODO",
                "reason": review_skip_reason,
            }
        ],
        "external_tools_allowed": {
            "allowed": False,
            "limits": "scaffold default; update before browsing, downloads, connector use, or database calls",
        },
        "file_write_plan": {
            "will_write_files": True,
            "allowed_paths": ["."],
        },
        "stop_criteria": ["S3 validation block", "unsupported high-confidence claim", "privacy or human-gate block"],
        "checkpoint_plan": [
            {
                "checkpoint": "source lock",
                "required_before": "source-backed final wording",
            },
            {
                "checkpoint": "claim ledger",
                "required_before": "final writing",
            },
        ],
        "execution_strategy": "inline_only",
        "spawned_review_plan": {
            "allowed": False,
            "budget": 0,
            "selected_roles": [],
            "rationale": review_skip_reason,
        },
        "team_spawn_plan": {
            "allowed": False,
            "budget": 0,
            "selected_teams": [],
            "dependency_graph": [],
            "nested_spawn_allowed": False,
            "rationale": "scaffold default; use only for independent decision axes",
        },
        "all_role_spawn_avoidance_reason": review_skip_reason,
        "nested_spawn_policy": {
            "allowed": False,
            "authorization": "not requested",
            "limits": "nested spawning disabled by default",
        },
        "post_team_audit_plan": "TODO: claim/citation/post-write validation plan",
        "source_corpus_id": corpus_id,
        "workflow_run_id": run_id,
    }

    run_state = {
        "run_id": run_id,
        "alias": workflow,
        "mode": mode,
        "plugin_version": version,
        "workflow_tier": "compact",
        "omics_track": "single-cell-other" if workflow == "omics-analysis-team" else "not-applicable",
        "execution_strategy": "inline_only",
        "nested_spawn_allowed": False,
        "spawned_review_lanes": [],
        "team_spawn_lanes": [],
        "team_output_artifacts": [],
        "spawned_agent_instances": [],
        "stages": [
            {
                "id": "S0",
                "required": True,
                "status": "block",
                "evidence": "runtime capability preflight scaffold created",
            },
            {
                "id": "S1",
                "required": True,
                "status": "block",
                "evidence": "protocol/context/source locks not completed yet",
            },
        ],
        "final_label": "Partial workflow; formal gates skipped",
        "downgrade_reasons": [
            "scaffold created before evidence collection, review, and validation",
            review_skip_reason,
        ],
    }

    lead_decision = {
        "schema_version": "1.0",
        "decision_id": f"lead-{run_id}",
        "workflow_run_id": run_id,
        "lead_scientist_agent_id": "life-science-lead-scientist",
        "requested_alias": workflow,
        "selected_mode": mode,
        "workflow_tier": "compact",
        "selected_playbook": PLAYBOOK_BY_WORKFLOW.get(workflow, "mechanism-review"),
        "omics_subtrack": "single-cell-other" if workflow == "omics-analysis-team" else "not-applicable",
        "execution_strategy": "inline_only",
        "lead_route_required": mode in {"standard", "deep", "audit", "run"},
        "mode_rule": "scaffold default; update after the lead/router locks scope, evidence, and runtime capability",
        "decision_rationale": "Initial scaffold created before source expansion or reviewer execution.",
        "selected_lanes": [workflow],
        "skipped_lanes": [
            {
                "lane": "spawned-review",
                "reason": review_skip_reason,
            }
        ],
        "spawned_review_plan": preflight["spawned_review_plan"],
        "team_spawn_plan": preflight["team_spawn_plan"],
        "post_team_audit_plan": preflight["post_team_audit_plan"],
    }

    source_corpus = {
        "corpus_id": corpus_id,
        "created_at": date,
        "query_or_origin": topic,
        "sources": [],
    }

    claim_ledger = {
        "claims": [],
        "excluded_or_not_verified_claims": [
            {
                "claim_id": "EX-001",
                "claim": "TODO: move unverified useful statements here until source-backed and checked",
                "reason_excluded": "scaffold placeholder",
                "evidence_needed_to_upgrade": "stable source identifiers and claim-level verification",
            }
        ],
    }

    stage_evaluation = {
        "evaluation_id": f"stage-{run_id}",
        "workflow_alias": workflow,
        "stages": [
            {
                "stage_id": "S1",
                "stage_name": "Plan",
                "status": "block",
                "score": 0.0,
                "evidence": "scaffold only",
                "blocking_issues": ["fill question, biological unit, endpoint, inclusion/exclusion, and statistics plan"],
            }
        ],
        "overall_verdict": "block",
        "downgrade_rule_applied": "final claims blocked until validation stages pass",
    }

    post_write_validation = {
        "final_validator_verdict": "block",
        "unsupported_final_claims": [],
        "citation_or_provenance_mismatches": [],
        "missing_uncertainty_or_limitations": [],
        "safety_ethics_privacy_issues": [],
        "failure_mode_checklist": [],
        "excluded_claim_handling": "not assessed in scaffold",
        "independent_review_status": review_skip_reason if is_omics_run_scaffold(workflow, mode) else "not-run",
        "minimal_required_corrections": ["complete workflow artifacts before claiming Compact standard or Full protocol"],
        "release_ready_claim_strength": "not-release-ready",
    }

    final_text = (
        "Workflow label: Partial workflow; formal gates skipped\n\n"
        f"Scaffold for `{workflow}` in `{mode}` mode.\n\n"
        f"Topic: {topic}\n\n"
        "Do not replace this with source-backed final wording until the claim ledger, "
        "source corpus, and post-write validation are updated.\n"
    )

    readme = (
        f"# BMAT Artifact Bundle\n\n"
        f"- Workflow: `{workflow}`\n"
        f"- Mode: `{mode}`\n"
        f"- Plugin version at creation: `{version}`\n"
        f"- Created: `{timestamp}`\n"
        f"- Topic: {topic}\n\n"
        "## Next Steps\n\n"
        "1. Complete `runtime_capability_preflight.json` before external tools, file writes, code execution, or final wording.\n"
        "2. Fill `source_corpus.json` with stable PMID/DOI/accession/NCT/local artifact IDs.\n"
        "3. Add atomic claims to `claim_ledger.json`; final prose should use only allowed wording.\n"
        "4. Update `stage_evaluation.json` and `run_state.json` as gates pass or block.\n"
        "5. Run the BMAT validator with the plugin script path, not a bundle-local `scripts/` directory:\n"
        f"   `{validator_command}`\n"
        "   Re-run this command before using a high-confidence workflow label.\n"
    )

    payloads: dict[str, dict[str, Any] | str] = {
        "runtime_capability_preflight.json": preflight,
        "run_state.json": run_state,
        "lead_decision.json": lead_decision,
        "source_corpus.json": source_corpus,
        "claim_ledger.json": claim_ledger,
        "stage_evaluation.json": stage_evaluation,
        "post_write_validation.json": post_write_validation,
        "final.md": final_text,
        "README.md": readme,
    }
    if workflow == "omics-analysis-team":
        payloads["omics_run_manifest.json"] = default_omics_manifest(run_id)
    return payloads


def main() -> int:
    args = parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    payloads = build_payloads(args.workflow, args.mode, args.topic, args.out)
    for filename, payload in payloads.items():
        path = args.out / filename
        if isinstance(payload, str):
            write_text(path, payload, args.force)
        else:
            write_json(path, payload, args.force)
    print(f"BMAT artifact scaffold created: {args.out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
