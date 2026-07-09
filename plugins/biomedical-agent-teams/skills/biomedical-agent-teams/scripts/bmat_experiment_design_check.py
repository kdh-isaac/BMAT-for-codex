#!/usr/bin/env python3
"""Validate BMAT experiment_design.json contracts locally."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Finding:
    level: str
    code: str
    message: str
    path: str = ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check BMAT experiment design contract completeness.")
    parser.add_argument("--experiment-design", type=Path, required=True)
    parser.add_argument("--source-verification", type=Path)
    parser.add_argument("--out", type=Path, help="Optional path for machine-readable experiment design check output.")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def plugin_version() -> str:
    version_file = Path(__file__).resolve().parents[1] / "VERSION"
    try:
        return version_file.read_text(encoding="utf-8-sig").strip()
    except FileNotFoundError:
        return "unknown"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def has_items(value: Any) -> bool:
    return isinstance(value, list) and any(str(item).strip() for item in value)


def main() -> int:
    args = parse_args()
    design = read_json(args.experiment_design)
    findings: list[Finding] = []
    for field in ("positive_controls", "negative_controls", "vehicle_or_mock_controls"):
        if not has_items(design.get(field)):
            findings.append(Finding("ERROR", "EXPERIMENT_DESIGN_CONTROL_MISSING", f"{field} must be non-empty", str(args.experiment_design)))
    biological = design.get("biological_replicates", {})
    if not isinstance(biological, dict) or not biological.get("planned_n") or not biological.get("rationale"):
        findings.append(Finding("ERROR", "EXPERIMENT_DESIGN_REPLICATE_RATIONALE_MISSING", "biological_replicates requires planned_n and rationale", str(args.experiment_design)))
    stats = design.get("statistical_plan", {})
    if not isinstance(stats, dict) or not stats.get("model") or not stats.get("multiplicity") or not stats.get("effect_size_or_decision_threshold"):
        findings.append(Finding("ERROR", "EXPERIMENT_DESIGN_STATS_PLAN_MISSING", "statistical_plan requires model, multiplicity, and effect_size_or_decision_threshold", str(args.experiment_design)))
    if not str(design.get("safety_ethics_privacy_boundary", "")).strip():
        findings.append(Finding("ERROR", "EXPERIMENT_DESIGN_SAFETY_BOUNDARY_MISSING", "safety_ethics_privacy_boundary is required", str(args.experiment_design)))
    if design.get("reagent_specific_claims") and args.source_verification is None:
        findings.append(Finding("ERROR", "EXPERIMENT_DESIGN_REAGENT_VERIFICATION_MISSING", "reagent-specific claims require --source-verification or unknown marking", str(args.experiment_design)))

    payload = {
        "schema_version": "1.0",
        "check_id": f"experiment-design-check-{design.get('design_id', 'unknown')}",
        "plugin_version": plugin_version(),
        "workflow_run_id": str(design.get("workflow_run_id", "unknown")),
        "checked_at": utc_now(),
        "status": "pass" if not any(finding.level == "ERROR" for finding in findings) else "block",
        "findings": [asdict(finding) for finding in findings],
    }
    if args.out:
        args.out.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for finding in findings:
            print(f"{finding.level} {finding.code}: {finding.message}")
        if not findings:
            print("Experiment design check passed.")
    return 1 if any(finding.level == "ERROR" for finding in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
