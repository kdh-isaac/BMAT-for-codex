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
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import bmat_init_bundle


SKILL_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS_ROOT = SKILL_ROOT / "workflows"
DOMAIN_PACKS_ROOT = SKILL_ROOT / "domain-packs"
VALIDATOR = SKILL_ROOT / "scripts" / "bmat_validate.py"
TOOL_LEDGER_CHECK = SKILL_ROOT / "scripts" / "bmat_tool_ledger_check.py"


def available_domain_packs() -> tuple[str, ...]:
    if not DOMAIN_PACKS_ROOT.exists():
        return ("generic-biomedical",)
    packs = tuple(sorted(path.name for path in DOMAIN_PACKS_ROOT.iterdir() if path.is_dir()))
    return packs or ("generic-biomedical",)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a local BMAT scaffold workflow.")
    parser.add_argument("--alias", choices=bmat_init_bundle.WORKFLOWS, required=True)
    parser.add_argument("--mode", choices=bmat_init_bundle.MODES, default="standard")
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
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str, force: bool) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"{path} exists; use --force to overwrite scaffold files")
    path.write_text(text, encoding="utf-8")


def default_results_integration(run_id: str, version: str) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "integration_id": f"ri-{run_id}",
        "plugin_version": version,
        "workflow_run_id": run_id,
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
        "schema_version": "1.0",
        "ledger_id": f"tcl-{run_id}",
        "plugin_version": version,
        "workflow_run_id": run_id,
        "calls": []
    }


def select_workflow_dag(alias: str) -> dict[str, Any]:
    path = WORKFLOWS_ROOT / f"{alias}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def workflow_dag_for_run(alias: str, mode: str) -> dict[str, Any]:
    workflow_dag = copy.deepcopy(select_workflow_dag(alias))
    workflow_dag["mode"] = mode
    workflow_dag["workflow_id"] = f"{alias}.{mode}"
    return workflow_dag


def enrich_payloads(payloads: dict[str, dict[str, Any] | str], args: argparse.Namespace) -> None:
    version = bmat_init_bundle.plugin_version()
    run_state = payloads["run_state.json"]
    preflight = payloads["runtime_capability_preflight.json"]
    assert isinstance(run_state, dict)
    assert isinstance(preflight, dict)
    run_id = str(run_state["run_id"])
    workflow_dag = workflow_dag_for_run(args.alias, args.mode)

    domain_pack_root = DOMAIN_PACKS_ROOT / args.domain_pack

    preflight["domain_pack"] = args.domain_pack
    preflight["domain_pack_version"] = "0.1.0"
    preflight["domain_specific_failure_modes_loaded"] = (domain_pack_root / "failure-modes.md").exists()
    preflight["domain_assumptions_skipped"] = []
    preflight["workflow_dag_id"] = workflow_dag["workflow_id"]
    preflight["results_integration_required"] = True

    run_state["domain_pack"] = args.domain_pack
    run_state["domain_pack_version"] = "0.1.0"
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

    payloads["workflow_dag.json"] = workflow_dag
    payloads["results_integration.json"] = default_results_integration(run_id, version)
    payloads["tool_call_ledger.json"] = default_tool_call_ledger(run_id, version)


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
        path.write_text(text, encoding="utf-8")
    return reports


def run_check(command: list[str]) -> int:
    result = subprocess.run(command, text=True, check=False)
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

    status = 0
    if args.validate:
        status = run_check([sys.executable, str(VALIDATOR), "--bundle", str(args.out), "--check-tool-ledger"])
        status = status or run_check([sys.executable, str(TOOL_LEDGER_CHECK), "--bundle", str(args.out)])
    if args.dry_run:
        print("Dry run complete: scaffold artifacts only; no external tools or models were called.")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
