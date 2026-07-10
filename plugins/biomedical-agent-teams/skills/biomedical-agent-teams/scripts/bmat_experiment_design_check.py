#!/usr/bin/env python3
"""Validate BMAT experiment-design contracts and referenced local artifacts.

This checker verifies contract completeness, provenance links, and deterministic
file integrity. It does not approve an experiment, replace scientific review,
or substitute for IRB, IACUC, biosafety, clinician, or institutional review.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SUPPORTED_SCHEMA_VERSION = "2.0"
RISKY_DESIGN_SCOPES = {
    "wet-lab",
    "animal",
    "human-material",
    "human-participant",
    "mixed",
}
PLACEHOLDER_VALUES = {
    "tbd",
    "todo",
    "unknown",
    "n/a",
    "na",
    "not determined",
    "not yet determined",
    "placeholder",
    "define later",
    "pending",
}
WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:[\\/]")


@dataclass(frozen=True)
class Finding:
    level: str
    code: str
    message: str
    path: str = ""
    fix_hint: str = ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check BMAT experiment-design v2 contract and artifact integrity."
    )
    parser.add_argument("--experiment-design", type=Path, required=True)
    parser.add_argument("--source-verification", type=Path)
    parser.add_argument(
        "--bundle-root",
        type=Path,
        help="Bundle root for sample-size artifact references (default: design file directory).",
    )
    parser.add_argument(
        "--release",
        action="store_true",
        help="Require the v2 release contract; legacy v1 is warning-only without this flag.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        help="Optional path for machine-readable experiment-design check output.",
    )
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
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2, sort_keys=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def has_items(value: Any) -> bool:
    return isinstance(value, list) and any(
        isinstance(item, str) and item.strip() and not is_placeholder(item) for item in value
    )


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def is_placeholder(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    normalized = " ".join(value.strip().casefold().split())
    return (
        not normalized
        or normalized in PLACEHOLDER_VALUES
        or (normalized.startswith("<") and normalized.endswith(">"))
        or normalized == "..."
    )


def has_substantive_text(value: Any) -> bool:
    return isinstance(value, str) and not is_placeholder(value)


def add_finding(
    findings: list[Finding],
    level: str,
    code: str,
    message: str,
    path: str,
    fix_hint: str,
) -> None:
    finding = Finding(level, code, message, path, fix_hint)
    if finding not in findings:
        findings.append(finding)


def json_path(parts: Any) -> str:
    path = "$"
    for part in parts:
        if isinstance(part, int):
            path += f"[{part}]"
        else:
            path += f".{part}"
    return path


def validate_v2_schema(design: dict[str, Any], findings: list[Finding]) -> None:
    schema_path = (
        Path(__file__).resolve().parents[1]
        / "contracts"
        / "experiment-design.schema.json"
    )
    try:
        from jsonschema import Draft202012Validator, FormatChecker
    except ImportError:
        add_finding(
            findings,
            "ERROR",
            "EXPERIMENT_DESIGN_SCHEMA_VALIDATOR_UNAVAILABLE",
            "jsonschema is required to validate the experiment-design v2 contract.",
            str(schema_path),
            "Install the repository validation dependencies and rerun the checker.",
        )
        return

    try:
        schema = read_json(schema_path)
        Draft202012Validator.check_schema(schema)
    except Exception as exc:
        # jsonschema raises several version-specific schema exceptions. Preserve
        # a stable BMAT finding instead of leaking implementation details.
        add_finding(
            findings,
            "ERROR",
            "EXPERIMENT_DESIGN_SCHEMA_UNUSABLE",
            f"experiment-design schema could not be loaded: {exc}",
            str(schema_path),
            "Repair the draft 2020-12 schema before validating artifacts.",
        )
        return

    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    for error in sorted(validator.iter_errors(design), key=lambda item: json_path(item.path)):
        pointer = json_path(error.absolute_path)
        add_finding(
            findings,
            "ERROR",
            "EXPERIMENT_DESIGN_SCHEMA_INVALID",
            error.message,
            pointer,
            "Make this field conform to contracts/experiment-design.schema.json v2.0.",
        )


def validate_controls(design: dict[str, Any], findings: list[Finding]) -> None:
    for field in (
        "positive_controls",
        "negative_controls",
        "vehicle_or_mock_controls",
    ):
        if not has_items(design.get(field)):
            add_finding(
                findings,
                "ERROR",
                "EXPERIMENT_DESIGN_CONTROL_MISSING",
                f"{field} must contain at least one explicit control.",
                f"$.{field}",
                "Add a non-placeholder control or document a scientifically valid control category.",
            )


def validate_legacy_design(
    design: dict[str, Any], findings: list[Finding], release: bool
) -> None:
    add_finding(
        findings,
        "WARN",
        "LEGACY_SCHEMA_V1_NOT_RELEASE_ELIGIBLE",
        "Legacy experiment-design input may be inspected but is not release eligible.",
        "$.schema_version",
        "Migrate the artifact to experiment-design schema_version 2.0 without inventing missing assumptions.",
    )
    if release:
        add_finding(
            findings,
            "ERROR",
            "EXPERIMENT_DESIGN_SCHEMA_VERSION_UNSUPPORTED",
            "Release validation requires experiment-design schema_version 2.0.",
            "$.schema_version",
            "Create a v2 artifact and mark unknown or unassessed information explicitly.",
        )

    validate_controls(design, findings)
    biological = design.get("biological_replicates", {})
    if (
        not isinstance(biological, dict)
        or not biological.get("planned_n")
        or not biological.get("rationale")
    ):
        add_finding(
            findings,
            "ERROR",
            "EXPERIMENT_DESIGN_REPLICATE_RATIONALE_MISSING",
            "biological_replicates requires planned_n and rationale.",
            "$.biological_replicates",
            "Record the biological-unit count and its rationale.",
        )
    stats = design.get("statistical_plan", {})
    if (
        not isinstance(stats, dict)
        or not stats.get("model")
        or not stats.get("multiplicity")
        or not stats.get("effect_size_or_decision_threshold")
    ):
        add_finding(
            findings,
            "ERROR",
            "EXPERIMENT_DESIGN_STATS_PLAN_MISSING",
            "statistical_plan requires model, multiplicity, and an effect-size or decision threshold.",
            "$.statistical_plan",
            "Define the model, multiplicity handling, and effect-size or decision threshold.",
        )
    if not str(design.get("safety_ethics_privacy_boundary", "")).strip():
        add_finding(
            findings,
            "ERROR",
            "EXPERIMENT_DESIGN_SAFETY_BOUNDARY_MISSING",
            "safety_ethics_privacy_boundary is required.",
            "$.safety_ethics_privacy_boundary",
            "Record the applicable safety, ethics, privacy, and disclosure boundary.",
        )


def quantitative_assumptions_present(design: dict[str, Any]) -> bool:
    effect = design.get("expected_effect_size")
    variance = design.get("variance_or_event_rate_assumption")
    return all(
        (
            isinstance(effect, dict) and is_number(effect.get("value")),
            isinstance(variance, dict) and is_number(variance.get("value")),
            is_number(design.get("alpha")),
            is_number(design.get("power")),
            isinstance(design.get("planned_n"), int)
            and not isinstance(design.get("planned_n"), bool)
            and design["planned_n"] > 0,
            is_number(design.get("dropout_or_failure_allowance")),
        )
    )


def validate_quantitative_design(
    design: dict[str, Any], findings: list[Finding], release: bool
) -> None:
    planned_n = design.get("planned_n")
    if is_placeholder(planned_n) or not (
        isinstance(planned_n, int) and not isinstance(planned_n, bool) and planned_n > 0
    ):
        add_finding(
            findings,
            "ERROR",
            "EXPERIMENT_DESIGN_PLANNED_N_PLACEHOLDER",
            "planned_n must be a positive integer; TBD or another placeholder is not a release-ready sample size.",
            "$.planned_n",
            "Provide a positive integer derived from the documented sample-size assumptions.",
        )

    quantitative_ok = quantitative_assumptions_present(design)
    if release and not quantitative_ok:
        add_finding(
            findings,
            "ERROR",
            "EXPERIMENT_DESIGN_QUANTITATIVE_ASSUMPTION_MISSING",
            "Release design requires numeric effect-size, variance/event-rate, alpha, power, planned_n, and dropout/failure assumptions.",
            "$",
            "Replace rationale-only or placeholder entries with explicit numeric assumptions.",
        )
    if design.get("recommendation_confidence") == "high" and not quantitative_ok:
        add_finding(
            findings,
            "ERROR",
            "EXPERIMENT_DESIGN_HIGH_CONFIDENCE_WITHOUT_QUANTITATIVE_ASSUMPTIONS",
            "A high-confidence design recommendation cannot rely on rationale alone.",
            "$.recommendation_confidence",
            "Add quantitative assumptions or lower the recommendation confidence.",
        )

    biological = design.get("biological_replicates")
    if isinstance(biological, dict):
        replicate_n = biological.get("planned_n")
        if (
            isinstance(planned_n, int)
            and not isinstance(planned_n, bool)
            and isinstance(replicate_n, int)
            and not isinstance(replicate_n, bool)
            and planned_n != replicate_n
        ):
            add_finding(
                findings,
                "ERROR",
                "EXPERIMENT_DESIGN_PLANNED_N_INCONSISTENT",
                "planned_n must equal biological_replicates.planned_n in the v2 compatibility field.",
                "$.biological_replicates.planned_n",
                "Use the total randomized biological-unit count in both fields.",
            )


def normalize_unit(value: Any) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def validate_unit_alignment(design: dict[str, Any], findings: list[Finding]) -> None:
    units = {
        "randomization": normalize_unit(design.get("randomization_unit")),
        "analysis": normalize_unit(design.get("analysis_unit")),
        "biological": normalize_unit(design.get("biological_unit")),
    }
    mismatch = len({unit for unit in units.values() if unit}) > 1
    handling = design.get("unit_mismatch_handling")
    if mismatch:
        valid_handling = (
            isinstance(handling, dict)
            and has_substantive_text(handling.get("justification"))
            and has_substantive_text(handling.get("analysis_adjustment"))
        )
        if not valid_handling:
            add_finding(
                findings,
                "ERROR",
                "EXPERIMENT_DESIGN_UNIT_MISMATCH_UNEXPLAINED",
                "Randomization, analysis, and biological units differ without a structured explanation and analysis adjustment.",
                "$.unit_mismatch_handling",
                "Explain the unit relationship and how clustering or pseudoreplication is handled.",
            )
        elif handling.get("effective_sample_size_considered") is not True:
            add_finding(
                findings,
                "ERROR",
                "EXPERIMENT_DESIGN_UNIT_MISMATCH_NOT_ACCOUNTED",
                "Unit mismatch handling must account for effective sample size.",
                "$.unit_mismatch_handling.effective_sample_size_considered",
                "Set true only after the sample-size and analysis plan account for the mismatch.",
            )
    elif handling is not None:
        add_finding(
            findings,
            "WARN",
            "EXPERIMENT_DESIGN_REDUNDANT_UNIT_MISMATCH_HANDLING",
            "unit_mismatch_handling is present although the three declared units are identical.",
            "$.unit_mismatch_handling",
            "Use null when the three units are aligned.",
        )


def validate_multiplicity(design: dict[str, Any], findings: list[Finding]) -> None:
    statistical_plan = design.get("statistical_plan")
    statistical_required = (
        "model",
        "clustering_or_repeated_measures",
        "effect_size_reporting",
    )
    if not isinstance(statistical_plan, dict) or any(
        not has_substantive_text(statistical_plan.get(field))
        for field in statistical_required
    ):
        add_finding(
            findings,
            "ERROR",
            "EXPERIMENT_DESIGN_STATS_PLAN_MISSING",
            "The statistical plan requires a model, clustering/repeated-measures handling, and effect-size reporting.",
            "$.statistical_plan",
            "Define the analysis model, dependence structure, and effect-size/uncertainty reporting.",
        )
    plan = design.get("multiplicity_plan")
    required = ("method", "family_definition", "alpha_allocation", "rationale")
    if (
        not isinstance(plan, dict)
        or plan.get("method") == "not-assessed"
        or any(not has_substantive_text(plan.get(field)) for field in required)
    ):
        add_finding(
            findings,
            "ERROR",
            "EXPERIMENT_DESIGN_MULTIPLICITY_PLAN_MISSING",
            "A statistical model without a complete multiplicity plan is not release ready.",
            "$.multiplicity_plan",
            "Define the endpoint family, method, alpha allocation, and rationale; use none-prespecified only with an explicit reason.",
        )
    interim = design.get("interim_analysis")
    if not isinstance(interim, dict) or any(
        not has_substantive_text(interim.get(field))
        for field in ("timing_or_reason", "alpha_spending_or_reason")
    ):
        add_finding(
            findings,
            "ERROR",
            "EXPERIMENT_DESIGN_INTERIM_PLAN_MISSING",
            "Interim-analysis timing and alpha handling must be explicit, including when no interim analysis is planned.",
            "$.interim_analysis",
            "Record the planned analysis or a substantive reason and alpha-spending boundary.",
        )
    stopping = design.get("stopping_rule")
    if (
        not isinstance(stopping, dict)
        or stopping.get("rule_type") == "not-assessed"
        or not has_substantive_text(stopping.get("criteria"))
        or not has_substantive_text(stopping.get("decision_authority"))
    ):
        add_finding(
            findings,
            "ERROR",
            "EXPERIMENT_DESIGN_STOPPING_RULE_MISSING",
            "A prespecified stopping rule and human decision authority are required.",
            "$.stopping_rule",
            "Define fixed-sample, efficacy, futility, safety, feasibility, or combined stopping criteria.",
        )


def validate_safety_boundary(design: dict[str, Any], findings: list[Finding]) -> None:
    boundary = design.get("safety_ethics_privacy_boundary")
    if not isinstance(boundary, dict):
        add_finding(
            findings,
            "ERROR",
            "EXPERIMENT_DESIGN_SAFETY_BOUNDARY_MISSING",
            "The v2 safety, ethics, privacy, and dual-use boundary must be structured.",
            "$.safety_ethics_privacy_boundary",
            "Add the structured boundary from the v2 experiment-design template.",
        )
        return

    triggers = boundary.get("risk_triggers")
    trigger_set = set(triggers) if isinstance(triggers, list) else set()
    risky = (
        design.get("design_scope") in RISKY_DESIGN_SCOPES
        or boundary.get("operational_details_included") is True
        or bool(trigger_set - {"none"})
    )
    if "none" in trigger_set and len(trigger_set) > 1:
        add_finding(
            findings,
            "ERROR",
            "EXPERIMENT_DESIGN_SAFETY_TRIGGER_CONFLICT",
            "risk_triggers cannot combine none with an active safety trigger.",
            "$.safety_ethics_privacy_boundary.risk_triggers",
            "Remove none or remove the active trigger after review.",
        )

    required_text_fields = (
        "privacy_boundary",
        "dual_use_boundary",
        "patent_sensitive_boundary",
        "limitations",
    )
    missing_text = [
        field
        for field in required_text_fields
        if not has_substantive_text(boundary.get(field))
    ]
    oversight = boundary.get("required_oversight")
    if risky and (missing_text or not has_items(oversight) or trigger_set in (set(), {"none"})):
        add_finding(
            findings,
            "ERROR",
            "EXPERIMENT_DESIGN_OPERATIONAL_SAFETY_BOUNDARY_INCOMPLETE",
            "Operational wet-lab, animal, human, private, patent-sensitive, or dual-use detail requires explicit triggers, oversight, and boundary text.",
            "$.safety_ethics_privacy_boundary",
            "Record the applicable oversight and disclosure limits before retaining operational detail.",
        )
    if boundary.get("bmat_role") != "research-assistance-only" or design.get(
        "decision_authority"
    ) != "research-assistance-only":
        add_finding(
            findings,
            "ERROR",
            "EXPERIMENT_DESIGN_AUTHORITY_OVERREACH",
            "BMAT must remain a research-assistance tool and cannot grant experimental or clinical approval.",
            "$.decision_authority",
            "Set both authority fields to research-assistance-only and obtain required human/institutional review.",
        )


def source_rows(source_verification: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(source_verification, dict):
        return {}
    rows = source_verification.get("rows")
    if not isinstance(rows, list):
        return {}
    return {
        str(row.get("source_id")): row
        for row in rows
        if isinstance(row, dict) and str(row.get("source_id", "")).strip()
    }


def source_row_release_eligible(row: dict[str, Any]) -> bool:
    return (
        row.get("identifier_status") == "verified"
        and row.get("release_eligible") is True
        and row.get("fixture_only") is False
        and row.get("verification_mode") in {"live-tool", "human", "local-file"}
        and row.get("integrity_status") not in {"retracted", "withdrawn"}
    )


def validate_reagents(
    design: dict[str, Any],
    source_verification: Any,
    source_verification_path: Path | None,
    findings: list[Finding],
) -> None:
    claims = design.get("reagent_specific_claims")
    if not isinstance(claims, list) or not claims:
        return
    rows = source_rows(source_verification)
    declared_source_ids = {
        str(source_id)
        for source_id in design.get("source_ids", [])
        if str(source_id).strip()
    }

    for index, claim in enumerate(claims):
        path = f"$.reagent_specific_claims[{index}]"
        if not isinstance(claim, dict):
            add_finding(
                findings,
                "ERROR",
                "EXPERIMENT_DESIGN_REAGENT_STATUS_INVALID",
                "Reagent-specific claims must be structured objects marked verified or unknown.",
                path,
                "Use the reagent claim object from the v2 template.",
            )
            continue
        status = claim.get("verification_status")
        ids = claim.get("source_ids") if isinstance(claim.get("source_ids"), list) else []
        if status == "unknown":
            if not has_substantive_text(claim.get("limitations")):
                add_finding(
                    findings,
                    "ERROR",
                    "EXPERIMENT_DESIGN_REAGENT_UNKNOWN_WITHOUT_LIMITATION",
                    "An unknown reagent-specific claim requires an explicit limitation.",
                    f"{path}.limitations",
                    "State that the manufacturer/catalog claim remains unverified and cannot support a high-confidence recommendation.",
                )
            continue
        if status != "verified":
            add_finding(
                findings,
                "ERROR",
                "EXPERIMENT_DESIGN_REAGENT_STATUS_INVALID",
                "Reagent-specific claims must be marked verified or unknown.",
                f"{path}.verification_status",
                "Use verified only with an eligible source receipt; otherwise use unknown with limitations.",
            )
            continue
        if not ids:
            add_finding(
                findings,
                "ERROR",
                "EXPERIMENT_DESIGN_REAGENT_VERIFICATION_MISSING",
                "A verified reagent-specific claim requires at least one source_id.",
                f"{path}.source_ids",
                "Link the claim to an eligible source-verification row.",
            )
            continue
        if source_verification_path is None:
            add_finding(
                findings,
                "ERROR",
                "EXPERIMENT_DESIGN_REAGENT_VERIFICATION_MISSING",
                "Verified reagent-specific claims require --source-verification.",
                path,
                "Provide source_verification.json or mark the reagent claim unknown with limitations.",
            )
        for source_id in ids:
            source_id = str(source_id)
            if source_id not in declared_source_ids:
                add_finding(
                    findings,
                    "ERROR",
                    "EXPERIMENT_DESIGN_REAGENT_SOURCE_NOT_DECLARED",
                    f"Reagent source {source_id!r} is not present in top-level source_ids.",
                    f"{path}.source_ids",
                    "Add the source to top-level source_ids or remove the unsupported reagent link.",
                )
            row = rows.get(source_id)
            if row is None or not source_row_release_eligible(row):
                add_finding(
                    findings,
                    "ERROR",
                    "EXPERIMENT_DESIGN_REAGENT_SOURCE_NOT_ELIGIBLE",
                    f"Reagent source {source_id!r} lacks an eligible live-tool, human, or local-file verification receipt.",
                    f"{path}.source_ids",
                    "Verify the source with a non-fixture receipt or mark the reagent claim unknown.",
                )


def bundle_artifact_path(
    bundle_root: Path,
    ref: Any,
    field_path: str,
    findings: list[Finding],
) -> Path | None:
    if not isinstance(ref, str) or is_placeholder(ref):
        add_finding(
            findings,
            "ERROR",
            "EXPERIMENT_DESIGN_SAMPLE_SIZE_ARTIFACT_MISSING",
            "Sample-size artifact reference is missing or is a placeholder.",
            field_path,
            "Use a bundle-relative path to an existing deterministic artifact.",
        )
        return None
    if WINDOWS_ABSOLUTE_RE.match(ref) or ref.startswith(("/", "\\")):
        add_finding(
            findings,
            "ERROR",
            "EXPERIMENT_DESIGN_SAMPLE_SIZE_PATH_INVALID",
            "Sample-size artifact paths must be bundle relative.",
            field_path,
            "Replace the absolute path with a path inside the bundle.",
        )
        return None
    parts = [part for part in re.split(r"[\\/]+", ref) if part not in ("", ".")]
    if not parts or ".." in parts:
        add_finding(
            findings,
            "ERROR",
            "EXPERIMENT_DESIGN_SAMPLE_SIZE_PATH_INVALID",
            "Sample-size artifact path traversal is not allowed.",
            field_path,
            "Use a normalized path within the bundle without .. segments.",
        )
        return None
    root = bundle_root.resolve()
    candidate = root.joinpath(*parts).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        add_finding(
            findings,
            "ERROR",
            "EXPERIMENT_DESIGN_SAMPLE_SIZE_PATH_INVALID",
            "Sample-size artifact resolves outside the bundle.",
            field_path,
            "Move the artifact into the bundle and update the reference.",
        )
        return None
    if not candidate.is_file():
        add_finding(
            findings,
            "ERROR",
            "EXPERIMENT_DESIGN_SAMPLE_SIZE_ARTIFACT_MISSING",
            f"Referenced sample-size artifact does not exist: {ref}",
            field_path,
            "Generate the artifact inside the bundle or mark sample_size_artifact_status not-produced.",
        )
        return None
    return candidate


def validate_sample_size_artifacts(
    design: dict[str, Any], bundle_root: Path, findings: list[Finding]
) -> None:
    status = design.get("sample_size_artifact_status")
    if status != "produced":
        return

    code_ref = design.get("sample_size_code_ref")
    if code_ref is not None:
        bundle_artifact_path(
            bundle_root,
            code_ref,
            "$.sample_size_code_ref",
            findings,
        )
    output = bundle_artifact_path(
        bundle_root,
        design.get("sample_size_output_ref"),
        "$.sample_size_output_ref",
        findings,
    )
    expected_hash = design.get("sample_size_output_sha256")
    if not isinstance(expected_hash, str) or not re.fullmatch(
        r"[0-9a-fA-F]{64}", expected_hash
    ):
        add_finding(
            findings,
            "ERROR",
            "EXPERIMENT_DESIGN_SAMPLE_SIZE_HASH_MISSING",
            "A produced sample-size artifact requires a 64-character SHA-256.",
            "$.sample_size_output_sha256",
            "Compute SHA-256 from the exact bundled output artifact.",
        )
    elif output is not None:
        actual_hash = sha256_file(output)
        if actual_hash.casefold() != expected_hash.casefold():
            add_finding(
                findings,
                "ERROR",
                "EXPERIMENT_DESIGN_SAMPLE_SIZE_HASH_MISMATCH",
                f"Sample-size output SHA-256 mismatch: expected {expected_hash}, computed {actual_hash}.",
                "$.sample_size_output_sha256",
                "Regenerate the artifact or update the hash after reviewing the changed output.",
            )


def load_optional_source_verification(
    path: Path | None, findings: list[Finding]
) -> Any:
    if path is None:
        return None
    try:
        return read_json(path)
    except (OSError, json.JSONDecodeError) as exc:
        add_finding(
            findings,
            "ERROR",
            "EXPERIMENT_DESIGN_SOURCE_VERIFICATION_UNREADABLE",
            f"Source-verification artifact could not be read: {exc}",
            str(path),
            "Provide a readable JSON source-verification artifact.",
        )
        return None


def build_payload(
    design: Any,
    design_path: Path,
    findings: list[Finding],
) -> dict[str, Any]:
    errors = any(finding.level == "ERROR" for finding in findings)
    workflow_run_id = (
        str(design.get("workflow_run_id", "unknown"))
        if isinstance(design, dict)
        else "unknown"
    )
    design_id = (
        str(design.get("design_id", "unknown"))
        if isinstance(design, dict)
        else "unknown"
    )
    artifact_hash = sha256_file(design_path) if design_path.is_file() else "unavailable"
    return {
        "schema_version": "2.0",
        "check_id": f"experiment-design-check-{design_id}",
        "plugin_version": plugin_version(),
        "workflow_run_id": workflow_run_id,
        "checked_at": utc_now(),
        "design_artifact_ref": design_path.name,
        "design_artifact_sha256": artifact_hash,
        "status": "block" if errors else "pass",
        "findings": [asdict(finding) for finding in findings],
    }


def main() -> int:
    args = parse_args()
    findings: list[Finding] = []
    design: Any = None
    try:
        design = read_json(args.experiment_design)
    except (OSError, json.JSONDecodeError) as exc:
        add_finding(
            findings,
            "ERROR",
            "EXPERIMENT_DESIGN_UNREADABLE",
            f"Experiment-design artifact could not be read: {exc}",
            str(args.experiment_design),
            "Provide a readable JSON object.",
        )

    if design is not None and not isinstance(design, dict):
        add_finding(
            findings,
            "ERROR",
            "EXPERIMENT_DESIGN_ROOT_INVALID",
            "Experiment-design artifact must be a JSON object.",
            "$",
            "Replace the root value with the v2 experiment-design object.",
        )
    elif isinstance(design, dict):
        if design.get("schema_version") != SUPPORTED_SCHEMA_VERSION:
            validate_legacy_design(design, findings, args.release)
        else:
            validate_v2_schema(design, findings)
            validate_controls(design, findings)
            validate_quantitative_design(design, findings, args.release)
            validate_unit_alignment(design, findings)
            validate_multiplicity(design, findings)
            validate_safety_boundary(design, findings)
            source_verification = load_optional_source_verification(
                args.source_verification, findings
            )
            validate_reagents(
                design,
                source_verification,
                args.source_verification,
                findings,
            )
            validate_sample_size_artifacts(
                design,
                args.bundle_root or args.experiment_design.parent,
                findings,
            )

    payload = build_payload(design, args.experiment_design, findings)
    if args.out:
        write_json_atomic(args.out, payload)

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for finding in findings:
            print(
                f"{finding.level} {finding.code}: {finding.message} "
                f"[{finding.path}] Fix: {finding.fix_hint}"
            )
        if not findings:
            print("Experiment design check passed.")
        elif not any(finding.level == "ERROR" for finding in findings):
            print("Experiment design check passed with warnings.")
    return 1 if any(finding.level == "ERROR" for finding in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
