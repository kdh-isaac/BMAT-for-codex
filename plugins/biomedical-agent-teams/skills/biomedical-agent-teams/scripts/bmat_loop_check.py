#!/usr/bin/env python3
"""Validate BMAT loop-state policy before automated or recurring execution.

This local checker is intentionally deterministic. It does not call models,
browse the web, or transmit workspace context. It enforces the safety and
completion invariants that make a recurring BMAT loop releasable.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
from typing import Any

try:
    import jsonschema  # type: ignore
except ImportError:  # pragma: no cover - depends on local environment
    jsonschema = None


OPEN_ITEM_STATUSES = {"open", "triaged", "deferred"}
OPEN_OBJECTION_STATUSES = {"open", "deferred"}
RELEASING_ARTIFACT_STATUSES = {"reviewed", "released"}
REQUIRED_LOOP_STATE_FIELDS = {
    "loop_id",
    "loop_name",
    "loop_type",
    "plugin_version",
    "status",
    "public_only",
    "private_context_allowed",
    "external_tools_allowed",
    "connectors_allowed",
    "human_review_required",
    "human_gate_status",
    "state_path",
    "source_delta_status",
    "cycle_count",
    "cycle_budget",
    "open_items",
    "reviewer_objections",
    "stop_conditions",
    "stop_status",
    "output_artifacts",
    "privacy_boundary",
}
BOOLEAN_FIELDS = {
    "public_only",
    "private_context_allowed",
    "external_tools_allowed",
    "human_review_required",
}
INTEGER_FIELD_MINIMUMS = {"cycle_count": 0, "cycle_budget": 1}

CONNECTOR_ALLOWLIST = {
    "weekly_literature_watch": {
        "pubmed",
        "ncbi entrez",
        "pubmed ncbi entrez",
        "biorxiv",
        "medrxiv",
        "biorxiv medrxiv",
        "doi",
        "crossref",
        "doi crossref",
        "europe pmc",
    },
    "public_omics_dataset_watch": {
        "geo",
        "sra",
        "geo sra",
        "ncbi datasets",
        "arrayexpress",
        "biostudies",
        "arrayexpress biostudies",
        "cellxgene",
        "tcga",
        "gdc",
        "tcga gdc",
        "hpa",
    },
    "claim_audit_inbox": {
        "pubmed",
        "ncbi entrez",
        "pubmed ncbi entrez",
        "doi",
        "crossref",
        "doi crossref",
        "clinicaltrials.gov",
        "clinicaltrials",
        "geo",
        "sra",
        "geo sra",
        "ncbi datasets",
        "arrayexpress",
        "biostudies",
        "arrayexpress biostudies",
        "cellxgene",
        "tcga",
        "gdc",
        "tcga gdc",
        "hpa",
        "uniprot",
        "reactome",
        "chembl",
        "pubchem",
    },
    "hypothesis_triage": {
        "pubmed",
        "ncbi entrez",
        "pubmed ncbi entrez",
        "geo",
        "sra",
        "geo sra",
        "ncbi datasets",
        "arrayexpress",
        "biostudies",
        "arrayexpress biostudies",
        "cellxgene",
        "tcga",
        "gdc",
        "tcga gdc",
        "reactome",
        "uniprot",
        "reactome uniprot",
        "open targets",
        "chembl",
        "pubchem",
        "chembl pubchem",
        "public omics repositories",
        "pathway databases",
    },
}

LOOP_RELEASE_ARTIFACT_RULES = {
    "weekly_literature_watch": {
        "allowed": {"source_delta", "claim_ledger_delta", "review_packet"},
        "required_any": {"source_delta", "claim_ledger_delta"},
    },
    "public_omics_dataset_watch": {
        "allowed": {"source_delta", "triage_report", "review_packet"},
        "required_any": {"triage_report", "source_delta"},
    },
    "claim_audit_inbox": {
        "allowed": {"audit_report", "claim_ledger_delta", "review_packet"},
        "required_any": {"audit_report", "claim_ledger_delta"},
    },
    "hypothesis_triage": {
        "allowed": {"triage_report", "claim_ledger_delta", "review_packet"},
        "required_any": {"triage_report", "claim_ledger_delta"},
    },
}


@dataclass(frozen=True)
class Finding:
    level: str
    code: str
    message: str
    path: str = ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate BMAT loop-state policy.")
    parser.add_argument("--loop-state", type=Path, required=True)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON findings.")
    return parser.parse_args()


def read_json(path: Path, findings: list[Finding]) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        findings.append(Finding("ERROR", "LOOP_STATE_MISSING", "loop-state artifact not found", str(path)))
    except json.JSONDecodeError as exc:
        findings.append(Finding("ERROR", "INVALID_JSON", f"loop-state is not valid JSON: {exc}", str(path)))
    return None


def validate_schema(loop_state: Any, findings: list[Finding]) -> None:
    if loop_state is None:
        return
    if jsonschema is None:
        findings.append(
            Finding("WARN", "SCHEMA_VALIDATION_SKIPPED", "install jsonschema to validate loop-state schema shape")
        )
        return
    schema_path = Path(__file__).resolve().parents[1] / "contracts" / "loop-state.schema.json"
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        jsonschema.validate(loop_state, schema)
    except FileNotFoundError:
        findings.append(Finding("ERROR", "SCHEMA_FILE_MISSING", "loop-state schema file missing", str(schema_path)))
    except jsonschema.ValidationError as exc:  # type: ignore[union-attr]
        findings.append(Finding("ERROR", "SCHEMA_VALIDATION_FAILED", f"loop-state: {exc.message}", str(schema_path)))


def validate_required_fields(loop_state: Any, findings: list[Finding]) -> None:
    if not isinstance(loop_state, dict):
        return
    for field in sorted(REQUIRED_LOOP_STATE_FIELDS - set(loop_state)):
        findings.append(
            Finding(
                "ERROR",
                "LOOP_STATE_REQUIRED_FIELD_MISSING",
                f"{field} is required in loop-state",
                field,
            )
        )


def safe_bool_field(loop_state: dict[str, Any], field: str, default: bool, findings: list[Finding]) -> bool:
    value = loop_state.get(field, default)
    if isinstance(value, bool):
        return value
    findings.append(
        Finding(
            "ERROR",
            "INVALID_BOOLEAN_FIELD",
            f"{field} must be a boolean, got {type(value).__name__}",
            field,
        )
    )
    return default


def safe_int_field(loop_state: dict[str, Any], field: str, default: int, findings: list[Finding]) -> int:
    value = loop_state.get(field, default)
    minimum = INTEGER_FIELD_MINIMUMS[field]
    if isinstance(value, int) and not isinstance(value, bool) and value >= minimum:
        return value
    findings.append(
        Finding(
            "ERROR",
            "INVALID_INTEGER_FIELD",
            f"{field} must be an integer >= {minimum}, got {value!r}",
            field,
        )
    )
    return default


def releasing_outputs(loop_state: dict[str, Any]) -> list[dict[str, Any]]:
    outputs = loop_state.get("output_artifacts", [])
    if not isinstance(outputs, list):
        return []
    return [
        output
        for output in outputs
        if isinstance(output, dict) and str(output.get("status", "")) in RELEASING_ARTIFACT_STATUSES
    ]


def normalize_token(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value).strip().lower()).strip()


def connector_names(loop_state: dict[str, Any]) -> list[str]:
    connectors = loop_state.get("connectors_allowed", [])
    if not isinstance(connectors, list):
        return []
    return [str(connector) for connector in connectors if str(connector).strip()]


def open_items(loop_state: dict[str, Any]) -> list[dict[str, Any]]:
    items = loop_state.get("open_items", [])
    if not isinstance(items, list):
        return []
    return [
        item
        for item in items
        if isinstance(item, dict) and str(item.get("status", "")) in OPEN_ITEM_STATUSES
    ]


def open_objections(loop_state: dict[str, Any]) -> list[dict[str, Any]]:
    objections = loop_state.get("reviewer_objections", [])
    if not isinstance(objections, list):
        return []
    return [
        objection
        for objection in objections
        if isinstance(objection, dict) and str(objection.get("status", "")) in OPEN_OBJECTION_STATUSES
    ]


def validate_loop_policy(loop_state: Any, findings: list[Finding]) -> None:
    if not isinstance(loop_state, dict):
        return

    status = str(loop_state.get("status", ""))
    loop_type = str(loop_state.get("loop_type", ""))
    stop_status = str(loop_state.get("stop_status", ""))
    human_gate_status = str(loop_state.get("human_gate_status", ""))
    private_context_allowed = safe_bool_field(loop_state, "private_context_allowed", False, findings)
    external_tools_allowed = safe_bool_field(loop_state, "external_tools_allowed", False, findings)
    human_review_required = safe_bool_field(loop_state, "human_review_required", False, findings)
    public_only = safe_bool_field(loop_state, "public_only", False, findings)
    source_delta_status = str(loop_state.get("source_delta_status", ""))
    cycle_count = safe_int_field(loop_state, "cycle_count", 0, findings)
    cycle_budget = safe_int_field(loop_state, "cycle_budget", 1, findings)
    blockers = []

    if external_tools_allowed and private_context_allowed and not public_only and human_gate_status != "approved":
        blockers.append(
            Finding(
                "ERROR",
                "PRIVATE_CONTEXT_REQUIRES_HUMAN_GATE",
                "external tools with private context require an approved human gate",
            )
        )

    if human_review_required and (
        status == "complete" or stop_status == "stop" or releasing_outputs(loop_state)
    ) and human_gate_status != "approved":
        blockers.append(
            Finding(
                "ERROR",
                "HUMAN_REVIEW_REQUIRED_BEFORE_TERMINAL_STATUS",
                "terminal loop status requires approved human review",
            )
        )

    if source_delta_status == "pending" and (status == "complete" or stop_status == "stop" or releasing_outputs(loop_state)):
        blockers.append(
            Finding(
                "ERROR",
                "SOURCE_DELTA_PENDING",
                "pending source delta must be processed or blocked before stopping or releasing outputs",
            )
        )

    if open_objections(loop_state) and (status == "complete" or stop_status == "stop" or releasing_outputs(loop_state)):
        blockers.append(
            Finding(
                "ERROR",
                "OPEN_REVIEWER_OBJECTION",
                "open or deferred reviewer objections must be accepted, rejected with rationale, or resolved",
            )
        )

    if open_items(loop_state) and status == "complete":
        blockers.append(
            Finding(
                "ERROR",
                "OPEN_ITEMS_BEFORE_COMPLETE",
                "open, triaged, or deferred loop items remain before complete status",
            )
        )

    if cycle_count > cycle_budget:
        blockers.append(
            Finding(
                "ERROR",
                "CYCLE_BUDGET_EXCEEDED",
                f"cycle_count {cycle_count} exceeds cycle_budget {cycle_budget}",
            )
        )

    validate_connector_policy(loop_state, blockers)
    validate_release_artifact_policy(loop_state, findings, blockers)

    if stop_status == "stop" and not releasing_outputs(loop_state):
        findings.append(
            Finding("WARN", "STOP_WITHOUT_REVIEWED_OUTPUT", "stop_status is stop but no reviewed or released output exists")
        )

    findings.extend(blockers)


def validate_connector_policy(loop_state: dict[str, Any], blockers: list[Finding]) -> None:
    loop_type = str(loop_state.get("loop_type", ""))
    if loop_type == "custom":
        return
    allowed = CONNECTOR_ALLOWLIST.get(loop_type)
    if not allowed:
        return
    allowed_normalized = {normalize_token(connector) for connector in allowed}
    for connector in connector_names(loop_state):
        normalized = normalize_token(connector)
        if normalized not in allowed_normalized:
            blockers.append(
                Finding(
                    "ERROR",
                    "CONNECTOR_NOT_ALLOWED_FOR_LOOP",
                    f"{connector} is not allowed for loop_type {loop_type}",
                )
            )


def validate_release_artifact_policy(
    loop_state: dict[str, Any],
    findings: list[Finding],
    blockers: list[Finding],
) -> None:
    loop_type = str(loop_state.get("loop_type", ""))
    rules = LOOP_RELEASE_ARTIFACT_RULES.get(loop_type)
    if not rules:
        return

    releasing = releasing_outputs(loop_state)
    releasing_types = {str(output.get("artifact_type", "")) for output in releasing}
    for artifact_type in sorted(releasing_types - rules["allowed"]):
        blockers.append(
            Finding(
                "ERROR",
                "LOOP_ARTIFACT_TYPE_NOT_ALLOWED",
                f"{artifact_type} is not a release artifact type for loop_type {loop_type}",
            )
        )

    is_release_state = loop_state.get("status") == "complete" or loop_state.get("stop_status") == "stop" or bool(releasing)
    if is_release_state and releasing and not (releasing_types & rules["required_any"]):
        blockers.append(
            Finding(
                "ERROR",
                "LOOP_RELEASE_ARTIFACT_REQUIRED",
                f"loop_type {loop_type} requires one of {sorted(rules['required_any'])} before release",
            )
        )


def emit(findings: list[Finding], as_json: bool) -> None:
    if not findings:
        findings = [Finding("INFO", "LOOP_CHECK_PASSED", "BMAT loop-state policy validation passed")]
    if as_json:
        print(json.dumps([asdict(finding) for finding in findings], indent=2, sort_keys=True))
        return
    for finding in findings:
        suffix = f" ({finding.path})" if finding.path else ""
        print(f"{finding.level} {finding.code}: {finding.message}{suffix}")


def main() -> int:
    args = parse_args()
    findings: list[Finding] = []
    loop_state = read_json(args.loop_state, findings)
    validate_required_fields(loop_state, findings)
    validate_schema(loop_state, findings)
    validate_loop_policy(loop_state, findings)
    emit(findings, args.json)
    return 1 if any(finding.level == "ERROR" for finding in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
