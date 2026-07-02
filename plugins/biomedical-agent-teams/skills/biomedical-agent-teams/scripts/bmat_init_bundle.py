#!/usr/bin/env python3
"""Create a starter Biomedical Agent Teams artifact bundle.

The scaffold is intentionally conservative: it creates editable placeholders
that satisfy BMAT's artifact naming conventions without pretending that review
or validation has already happened.
"""

from __future__ import annotations

import argparse
import json
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
    "preflight.json",
    "run_state.json",
    "source_corpus.json",
    "claim_ledger.json",
    "stage_evaluation.json",
    "post_write_validation.json",
    "final.md",
    "README.md",
)
UTF8_BOM = "\ufeff"


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


def build_payloads(workflow: str, mode: str, topic: str) -> dict[str, dict[str, Any] | str]:
    timestamp, date = utc_now()
    version = plugin_version()
    run_id = f"bmat-{workflow}-{mode}-{timestamp.replace(':', '').replace('-', '')}"
    corpus_id = f"corpus-{run_id}"
    review_skip_reason = scaffold_review_skip_reason(workflow, mode)

    preflight = {
        "runtime_capability_preflight_id": f"rt-{run_id}",
        "requested_alias": workflow,
        "selected_mode": mode,
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
        "1. Complete `preflight.json` before external tools, file writes, code execution, or final wording.\n"
        "2. Fill `source_corpus.json` with stable PMID/DOI/accession/NCT/local artifact IDs.\n"
        "3. Add atomic claims to `claim_ledger.json`; final prose should use only allowed wording.\n"
        "4. Update `stage_evaluation.json` and `run_state.json` as gates pass or block.\n"
        "5. Run `scripts/bmat_validate.py --bundle <this-directory>` before using a high-confidence workflow label.\n"
    )

    return {
        "preflight.json": preflight,
        "run_state.json": run_state,
        "source_corpus.json": source_corpus,
        "claim_ledger.json": claim_ledger,
        "stage_evaluation.json": stage_evaluation,
        "post_write_validation.json": post_write_validation,
        "final.md": final_text,
        "README.md": readme,
    }


def main() -> int:
    args = parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    payloads = build_payloads(args.workflow, args.mode, args.topic)
    for filename in BUNDLE_FILES:
        path = args.out / filename
        payload = payloads[filename]
        if isinstance(payload, str):
            write_text(path, payload, args.force)
        else:
            write_json(path, payload, args.force)
    print(f"BMAT artifact scaffold created: {args.out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
