#!/usr/bin/env python3
"""Validate BMAT claim/source/span/review receipt consistency.

This checker validates provenance and release-policy invariants.  It does not
certify scientific truth or infer entailment from prose.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = SKILL_ROOT / "contracts"
STRICT_SCOPE_VALUES = {"match", "not-applicable"}
INDEPENDENT_REVIEW_CLASSES = {"separate-model", "external-tool", "human"}


@dataclass(frozen=True)
class Finding:
    level: str
    code: str
    message: str
    path: str = ""
    fix_hint: str = ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate claim support provenance; this is not a scientific-truth certifier."
    )
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--claim-ledger", type=Path)
    parser.add_argument("--source-corpus", type=Path)
    parser.add_argument("--source-verification", type=Path)
    parser.add_argument("--claim-support-matrix", type=Path)
    parser.add_argument("--review-artifact-manifest", type=Path)
    parser.add_argument("--run-state", type=Path)
    parser.add_argument(
        "--release",
        action="store_true",
        help="Require canonical v2 artifacts and release-grade receipts.",
    )
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def read_json(path: Path, findings: list[Finding], code_prefix: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        findings.append(
            Finding(
                "ERROR",
                f"{code_prefix}_FILE_MISSING",
                "required JSON artifact is missing",
                str(path),
                "Generate the required artifact for this workflow run.",
            )
        )
    except json.JSONDecodeError as exc:
        findings.append(
            Finding(
                "ERROR",
                f"{code_prefix}_INVALID_JSON",
                f"invalid JSON: {exc}",
                str(path),
                "Write valid UTF-8 JSON and rerun the checker.",
            )
        )
    return None


def validate_schema(
    payload: Any,
    schema_name: str,
    artifact_path: Path,
    code: str,
    findings: list[Finding],
) -> None:
    try:
        from jsonschema import Draft202012Validator, FormatChecker
    except ImportError:
        findings.append(
            Finding(
                "ERROR",
                "JSONSCHEMA_REQUIRED",
                "jsonschema is required for release claim-support validation",
                str(artifact_path),
                "Install the project validation dependencies and rerun.",
            )
        )
        return
    schema = read_json(CONTRACTS / schema_name, findings, "CONTRACT")
    if not isinstance(schema, dict):
        return
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(
        validator.iter_errors(payload),
        key=lambda item: "/".join(str(part) for part in item.absolute_path),
    )
    for error in errors:
        pointer = "/".join(str(part) for part in error.absolute_path)
        findings.append(
            Finding(
                "ERROR",
                code,
                error.message,
                f"{artifact_path}#{pointer}" if pointer else str(artifact_path),
                "Conform the artifact to the canonical schema_version 2.0 contract.",
            )
        )


def value_as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [part.strip() for part in value.replace(";", ",").split(",") if part.strip()]
    return []


def iter_claims(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        for key in ("claims", "claim_ledger", "rows"):
            if isinstance(payload.get(key), list):
                return [row for row in payload[key] if isinstance(row, dict)]
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    return []


def claim_source_ids(claim: dict[str, Any]) -> set[str]:
    values = value_as_list(claim.get("source_ids")) + value_as_list(claim.get("source_id"))
    evidence_items = claim.get("evidence_items", claim.get("evidence", []))
    if isinstance(evidence_items, list):
        for item in evidence_items:
            if isinstance(item, str):
                values.append(item)
            elif isinstance(item, dict):
                values.extend(value_as_list(item.get("source_id")))
    return set(values)


def iter_rows(payload: Any, key: str = "rows") -> list[dict[str, Any]]:
    if isinstance(payload, dict) and isinstance(payload.get(key), list):
        return [row for row in payload[key] if isinstance(row, dict)]
    return []


def safe_bundle_file(bundle_root: Path, reference: Any) -> tuple[Path | None, str | None]:
    text = str(reference or "").strip()
    if not text or text == "not-applicable" or "\x00" in text:
        return None, "path is empty, not-applicable, or contains a NUL byte"
    windows = PureWindowsPath(text)
    posix = PurePosixPath(text.replace("\\", "/"))
    if windows.is_absolute() or windows.drive or posix.is_absolute():
        return None, "absolute paths are not allowed"
    if ".." in windows.parts or ".." in posix.parts:
        return None, "path traversal is not allowed"
    root = bundle_root.resolve()
    candidate = (root / Path(*posix.parts)).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None, "path resolves outside the bundle root"
    return candidate, None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_file(
    *,
    bundle_root: Path,
    reference: Any,
    expected_sha256: Any,
    code_prefix: str,
    label: str,
    finding_path: str,
    findings: list[Finding],
) -> bool:
    resolved, error = safe_bundle_file(bundle_root, reference)
    if error:
        findings.append(
            Finding(
                "ERROR",
                f"{code_prefix}_PATH_INVALID",
                f"{label}: {error}",
                finding_path,
                "Use a bundle-relative artifact path without traversal segments.",
            )
        )
        return False
    assert resolved is not None
    if not resolved.is_file():
        findings.append(
            Finding(
                "ERROR",
                f"{code_prefix}_MISSING",
                f"{label} does not exist inside the bundle",
                str(resolved),
                "Add the exact reviewed or snapshotted artifact to the bundle.",
            )
        )
        return False
    if sha256_file(resolved).lower() != str(expected_sha256 or "").lower():
        findings.append(
            Finding(
                "ERROR",
                f"{code_prefix}_HASH_MISMATCH",
                f"{label} SHA-256 does not match its receipt",
                str(resolved),
                "Recompute the hash from the exact bundled file; do not reuse a stale receipt.",
            )
        )
        return False
    return True


def is_high_confidence(claim: dict[str, Any]) -> bool:
    profile = str(claim.get("claim_profile", "")).strip().replace("_", "-")
    strength = str(claim.get("claim_strength", "")).strip().replace("_", "-")
    return profile == "high-confidence" or strength == "high-confidence"


def scope_is_strict(scope: Any) -> bool:
    required = {
        "species",
        "cell_type",
        "assay",
        "endpoint",
        "population_or_model",
        "intervention_or_exposure",
        "biological_context",
    }
    return isinstance(scope, dict) and set(scope) == required and all(
        value in STRICT_SCOPE_VALUES for value in scope.values()
    )


def identity_value(payload: Any, key: str) -> str:
    return str(payload.get(key, "")).strip() if isinstance(payload, dict) else ""


def check_identity(
    *,
    artifacts: list[tuple[str, Any, Path]],
    run_state: Any,
    release: bool,
    findings: list[Finding],
) -> None:
    authoritative_run_id = identity_value(run_state, "run_id")
    authoritative_plugin = identity_value(run_state, "plugin_version")
    if release and (not authoritative_run_id or not authoritative_plugin):
        findings.append(
            Finding(
                "ERROR",
                "RUN_STATE_IDENTITY_REQUIRED",
                "release validation requires run_state run_id and plugin_version",
                "run_state.json",
                "Use the active run_state as the authoritative bundle identity.",
            )
        )
    artifact_ids: set[tuple[str, str]] = set()
    for artifact_type, payload, path in artifacts:
        if not isinstance(payload, dict):
            continue
        run_id = identity_value(payload, "workflow_run_id")
        plugin = identity_value(payload, "plugin_version")
        if run_id and authoritative_run_id and run_id != authoritative_run_id:
            findings.append(
                Finding(
                    "ERROR",
                    "STALE_WORKFLOW_RUN_ID",
                    f"{artifact_type} workflow_run_id differs from run_state.run_id",
                    str(path),
                    "Regenerate the artifact for the active workflow run.",
                )
            )
        if plugin and authoritative_plugin and plugin != authoritative_plugin:
            findings.append(
                Finding(
                    "ERROR",
                    "ARTIFACT_PLUGIN_VERSION_MISMATCH",
                    f"{artifact_type} plugin_version differs from run_state.plugin_version",
                    str(path),
                    "Regenerate all release artifacts with one plugin version.",
                )
            )
        id_keys = {
            "source_corpus": "corpus_id",
            "source_verification": "verification_id",
            "claim_support_matrix": "support_matrix_id",
        }
        artifact_id = identity_value(payload, id_keys.get(artifact_type, ""))
        if artifact_id:
            identity = (artifact_type, artifact_id)
            if identity in artifact_ids:
                findings.append(Finding("ERROR", "DUPLICATE_ARTIFACT_ID", f"duplicate {artifact_type} artifact ID {artifact_id}", str(path), "Use one immutable artifact ID per workflow artifact."))
            artifact_ids.add(identity)


def main() -> int:
    args = parse_args()
    bundle = args.bundle.resolve()
    paths = {
        "claim_ledger": args.claim_ledger or bundle / "claim_ledger.json",
        "source_corpus": args.source_corpus or bundle / "source_corpus.json",
        "source_verification": args.source_verification or bundle / "source_verification.json",
        "claim_support_matrix": args.claim_support_matrix or bundle / "claim_support_matrix.json",
        "review_artifact_manifest": args.review_artifact_manifest or bundle / "review_artifact_manifest.json",
        "run_state": args.run_state or bundle / "run_state.json",
    }
    findings: list[Finding] = []
    artifacts = {
        key: read_json(path, findings, key.upper())
        for key, path in paths.items()
    }

    schema_contracts = {
        "claim_ledger": "claim-ledger.schema.json",
        "source_corpus": "source-corpus.schema.json",
        "source_verification": "source-verification.schema.json",
        "claim_support_matrix": "claim-support-matrix.schema.json",
        "review_artifact_manifest": "review-artifact-manifest.schema.json",
    }
    for key, schema_name in schema_contracts.items():
        payload = artifacts[key]
        version = identity_value(payload, "schema_version")
        if version != "2.0":
            level = "ERROR" if args.release else "WARNING"
            findings.append(
                Finding(
                    level,
                    "LEGACY_SCHEMA_V1_NOT_RELEASE_ELIGIBLE",
                    f"{key} schema_version {version or 'missing'} is not release eligible",
                    str(paths[key]),
                    "Migrate to v2 without inventing missing verification or review evidence.",
                )
            )
        else:
            validate_schema(payload, schema_name, paths[key], f"{key.upper()}_SCHEMA_INVALID", findings)

    check_identity(
        artifacts=[
            (key, artifacts[key], paths[key])
            for key in ("claim_ledger", "source_corpus", "source_verification", "claim_support_matrix", "review_artifact_manifest")
        ],
        run_state=artifacts["run_state"],
        release=args.release,
        findings=findings,
    )

    claims = iter_claims(artifacts["claim_ledger"])
    sources = iter_rows(artifacts["source_corpus"], "sources")
    verification_rows = iter_rows(artifacts["source_verification"])
    support_rows = iter_rows(artifacts["claim_support_matrix"])
    review_instances = iter_rows(artifacts["review_artifact_manifest"], "review_instances")
    claims_by_id = {str(row.get("claim_id", "")).strip(): row for row in claims}
    sources_by_id = {str(row.get("source_id", "")).strip(): row for row in sources}
    verification_by_source = {str(row.get("source_id", "")).strip(): row for row in verification_rows}
    reviews_by_id = {str(row.get("instance_id", "")).strip(): row for row in review_instances}

    for label, rows, key, code in (
        ("claim", claims, "claim_id", "DUPLICATE_CLAIM_ID"),
        ("source", sources, "source_id", "DUPLICATE_SOURCE_ID"),
        ("source verification", verification_rows, "source_id", "SOURCE_VERIFICATION_DUPLICATE_SOURCE_ROW"),
        ("review instance", review_instances, "instance_id", "DUPLICATE_REVIEW_INSTANCE_ID"),
    ):
        seen: set[str] = set()
        for row in rows:
            identifier = str(row.get(key, "")).strip()
            if identifier in seen:
                findings.append(Finding("ERROR", code, f"duplicate {label} identifier {identifier}", str(paths["claim_support_matrix"]), f"Use one canonical row for each {key}."))
            seen.add(identifier)

    spans_by_id: dict[str, tuple[str, dict[str, Any]]] = {}
    valid_span_receipts: set[str] = set()
    for source in sources:
        source_id = str(source.get("source_id", "")).strip()
        evidence_spans = source.get("evidence_spans", [])
        if not isinstance(evidence_spans, list):
            continue
        for span_index, span in enumerate(evidence_spans):
            if not isinstance(span, dict):
                continue
            span_id = str(span.get("span_id", "")).strip()
            span_path = f"{paths['source_corpus']}#sources/{source_id}/evidence_spans/{span_index}"
            if span_id in spans_by_id:
                findings.append(Finding("ERROR", "DUPLICATE_EVIDENCE_SPAN_ID", f"duplicate evidence span ID {span_id}", span_path, "Use a globally unique span_id that has one source owner."))
            else:
                spans_by_id[span_id] = (source_id, span)
            if str(span.get("source_id", "")).strip() != source_id:
                findings.append(Finding("ERROR", "EVIDENCE_SPAN_SOURCE_OWNERSHIP_MISMATCH", f"{span_id} declares a different source owner", span_path, "Set evidence span source_id to its containing source row."))
            excerpt = str(span.get("short_evidence_excerpt", ""))
            excerpt_sha = hashlib.sha256(excerpt.encode("utf-8")).hexdigest()
            excerpt_ok = excerpt_sha.lower() == str(span.get("evidence_text_sha256", "")).lower()
            if not excerpt_ok:
                findings.append(Finding("ERROR", "EVIDENCE_TEXT_SHA256_MISMATCH", f"{span_id} evidence_text_sha256 does not match the exact short excerpt", span_path, "Hash the exact UTF-8 short_evidence_excerpt."))
            snapshot_ok = verify_file(
                bundle_root=bundle,
                reference=span.get("source_snapshot_ref"),
                expected_sha256=span.get("source_snapshot_sha256"),
                code_prefix="EVIDENCE_SNAPSHOT",
                label=f"evidence snapshot for {span_id}",
                finding_path=span_path,
                findings=findings,
            )
            if excerpt_ok and snapshot_ok and str(span.get("source_id", "")).strip() == source_id:
                valid_span_receipts.add(span_id)

    support_key_rows: dict[tuple[str, str, str], dict[str, Any]] = {}
    rows_by_claim: dict[str, list[dict[str, Any]]] = {}
    valid_review_rows: set[int] = set()
    for index, row in enumerate(support_rows):
        row_path = f"{paths['claim_support_matrix']}#rows/{index}"
        claim_id = str(row.get("claim_id", "")).strip()
        source_id = str(row.get("source_id", "")).strip()
        span_ref = str(row.get("evidence_span_ref", "")).strip()
        key = (claim_id, source_id, span_ref)
        previous = support_key_rows.get(key)
        if previous is not None:
            code = "CONFLICTING_SUPPORT_ROW" if previous != row else "DUPLICATE_SUPPORT_ROW"
            findings.append(Finding("ERROR", code, f"duplicate claim/source/span support key {key}", row_path, "Keep one adjudicated support row for each claim/source/span edge."))
        else:
            support_key_rows[key] = row
        rows_by_claim.setdefault(claim_id, []).append(row)

        claim = claims_by_id.get(claim_id)
        source = sources_by_id.get(source_id)
        verification = verification_by_source.get(source_id)
        if claim is None:
            findings.append(Finding("ERROR", "CLAIM_SUPPORT_UNKNOWN_CLAIM_ID", f"support row references unknown claim_id {claim_id}", row_path, "Use a claim_id present in claim_ledger.json."))
        if source is None:
            findings.append(Finding("ERROR", "CLAIM_SUPPORT_UNKNOWN_SOURCE_ID", f"support row references unknown source_id {source_id}", row_path, "Use a source_id present in source_corpus.json."))
        elif source.get("inclusion_status") != "included":
            findings.append(Finding("ERROR", "CLAIM_SUPPORT_SOURCE_NOT_INCLUDED", f"{source_id} inclusion_status is not included", row_path, "Include the source explicitly or do not use it as claim support."))
        if claim is not None and source_id not in claim_source_ids(claim):
            findings.append(Finding("ERROR", "CLAIM_SUPPORT_SOURCE_NOT_LINKED_TO_CLAIM", f"{source_id} is absent from {claim_id} source links", row_path, "Add the source to claim.source_ids/evidence_items or remove this support row."))
        span_entry = spans_by_id.get(span_ref)
        if span_entry is None:
            findings.append(Finding("ERROR", "EVIDENCE_SPAN_REF_UNRESOLVED", f"evidence_span_ref {span_ref} does not resolve", row_path, "Reference a source_corpus evidence span ID."))
        elif span_entry[0] != source_id:
            findings.append(Finding("ERROR", "EVIDENCE_SPAN_WRONG_SOURCE", f"evidence span {span_ref} belongs to {span_entry[0]}, not {source_id}", row_path, "Reference only an evidence span owned by this support row's source."))
        if verification is None:
            findings.append(Finding("ERROR", "CLAIM_SUPPORT_SOURCE_VERIFICATION_MISSING", f"{source_id} has no source verification row", row_path, "Add an explicit source verification receipt."))
        elif (row.get("release_eligible") is True or row.get("allowed_in_final") is True or (claim is not None and is_high_confidence(claim))) and verification.get("release_eligible") is not True:
            findings.append(Finding("ERROR", "CLAIM_SUPPORT_SOURCE_NOT_RELEASE_ELIGIBLE", f"{source_id} verification is not release eligible", row_path, "Provide a real live-tool, human, or local-file receipt or downgrade the claim."))
        if verification is not None and verification.get("integrity_status") in {"retracted", "withdrawn"} and (row.get("allowed_in_final") is True or row.get("release_eligible") is True):
            findings.append(Finding("ERROR", "RETRACTED_SOURCE_CANNOT_SUPPORT_FINAL_CLAIM", f"{source_id} is {verification.get('integrity_status')}", row_path, "Exclude the source from supportive final evidence."))
        if claim is not None and str(row.get("allowed_final_wording", "")) != str(claim.get("allowed_final_wording", "")):
            findings.append(Finding("ERROR", "CLAIM_SUPPORT_WORDING_CONFLICT", f"{claim_id} allowed_final_wording differs from claim_ledger", row_path, "Use the exact ledger-approved wording."))
        if row.get("support_verdict") in {"contradicts", "irrelevant", "not-checked"} and row.get("allowed_in_final") is True:
            findings.append(Finding("ERROR", "CLAIM_SUPPORT_BLOCKING_VERDICT_ALLOWED_IN_FINAL", f"{claim_id} blocking verdict cannot be allowed in final", row_path, "Set allowed_in_final=false and release_eligible=false."))

        review_ref = str(row.get("review_artifact_ref", "")).strip()
        independent_required = row.get("independent_review_required") is True
        if review_ref != "not-applicable" or independent_required:
            artifact_ok = verify_file(
                bundle_root=bundle,
                reference=review_ref,
                expected_sha256=row.get("review_artifact_sha256"),
                code_prefix="CLAIM_SUPPORT_REVIEW_ARTIFACT",
                label=f"review artifact for {claim_id}",
                finding_path=row_path,
                findings=findings,
            )
            instance_id = str(row.get("review_instance_id", "")).strip()
            instance = reviews_by_id.get(instance_id)
            instance_ok = instance is not None
            if instance is None:
                findings.append(Finding("ERROR", "CLAIM_SUPPORT_REVIEW_INSTANCE_MISSING", f"review_instance_id {instance_id} is absent from review_artifact_manifest", row_path, "Reference the exact review execution receipt."))
            else:
                if str(instance.get("output_artifact", "")).strip() != review_ref:
                    findings.append(Finding("ERROR", "CLAIM_SUPPORT_REVIEW_ARTIFACT_REF_MISMATCH", f"{instance_id} output_artifact differs from support row", row_path, "Use the review instance output_artifact path."))
                    instance_ok = False
                if str(instance.get("output_sha256", "")).lower() != str(row.get("review_artifact_sha256", "")).lower():
                    findings.append(Finding("ERROR", "CLAIM_SUPPORT_REVIEW_ARTIFACT_SHA256_MISMATCH", f"{instance_id} output_sha256 differs from support row", row_path, "Use the exact review output hash from the review receipt."))
                    instance_ok = False
                actor = str(instance.get("actor_id", instance.get("agent_id", ""))).strip()
                row_actor = str(row.get("review_actor_id", "")).strip()
                if actor and actor != row_actor:
                    findings.append(Finding("ERROR", "CLAIM_SUPPORT_REVIEW_ACTOR_MISMATCH", f"{instance_id} actor differs from support row", row_path, "Use the actor recorded by the review execution receipt."))
                    instance_ok = False
                independence = str(instance.get("independence_class", "")).strip()
                if independent_required:
                    separate_model_identity_ok = True
                    if independence == "separate-model":
                        reviewer_identity = (
                            str(instance.get("provider", "")),
                            str(instance.get("model", "")),
                            str(instance.get("model_version", "")),
                        )
                        authoring_identity = (
                            str(instance.get("authoring_provider", "")),
                            str(instance.get("authoring_model", "")),
                            str(instance.get("authoring_model_version", "")),
                        )
                        separate_model_identity_ok = (
                            instance.get("authoring_identity_available") is True
                            and reviewer_identity != authoring_identity
                            and str(instance.get("execution_session_id", ""))
                            != str(instance.get("authoring_execution_session_id", ""))
                        )
                    if (
                        independence not in INDEPENDENT_REVIEW_CLASSES
                        or instance.get("independent_review_eligible") is not True
                        or instance.get("fixture_only") is not False
                        or instance.get("authoring_context_shared") is not False
                        or not separate_model_identity_ok
                    ):
                        findings.append(Finding("ERROR", "INDEPENDENT_REVIEW_RECEIPT_INELIGIBLE", f"{instance_id} does not carry an eligible non-fixture independent review receipt", row_path, "Use a separate-model, external-tool, or human receipt with independent_review_eligible=true, or downgrade the label."))
                        instance_ok = False
                    input_hashes = instance.get("input_artifact_sha256", {})
                    input_ok = True
                    for input_ref in value_as_list(instance.get("input_artifact_refs")):
                        expected_input_hash = input_hashes.get(input_ref) if isinstance(input_hashes, dict) else None
                        input_ok = verify_file(
                            bundle_root=bundle,
                            reference=input_ref,
                            expected_sha256=expected_input_hash,
                            code_prefix="INDEPENDENT_REVIEW_INPUT_ARTIFACT",
                            label=f"review input {input_ref} for {instance_id}",
                            finding_path=row_path,
                            findings=findings,
                        ) and input_ok
                    prompt_ok = verify_file(
                        bundle_root=bundle,
                        reference=instance.get("prompt_template_ref"),
                        expected_sha256=instance.get("prompt_template_sha256"),
                        code_prefix="INDEPENDENT_REVIEW_PROMPT_TEMPLATE",
                        label=f"prompt template for {instance_id}",
                        finding_path=row_path,
                        findings=findings,
                    )
                    runtime_ok = verify_file(
                        bundle_root=bundle,
                        reference=instance.get("runtime_receipt_ref"),
                        expected_sha256=instance.get("runtime_receipt_sha256"),
                        code_prefix="INDEPENDENT_REVIEW_RUNTIME_RECEIPT",
                        label=f"runtime receipt for {instance_id}",
                        finding_path=row_path,
                        findings=findings,
                    )
                    instance_ok = instance_ok and input_ok and prompt_ok and runtime_ok
            if artifact_ok and instance_ok:
                valid_review_rows.add(index)

    for claim_id, claim in claims_by_id.items():
        if not is_high_confidence(claim):
            continue
        rows = rows_by_claim.get(claim_id, [])
        qualifying: list[dict[str, Any]] = []
        qualifying_source_versions: list[str] = []
        for index, row in enumerate(support_rows):
            if str(row.get("claim_id", "")).strip() != claim_id:
                continue
            source_id = str(row.get("source_id", "")).strip()
            span_ref = str(row.get("evidence_span_ref", "")).strip()
            verification = verification_by_source.get(source_id, {})
            review_ok = row.get("independent_review_required") is not True or index in valid_review_rows
            if (
                row.get("support_verdict") == "supports"
                and scope_is_strict(row.get("scope_match"))
                and row.get("overclaim_risk") == "low"
                and row.get("allowed_in_final") is True
                and row.get("release_eligible") is True
                and verification.get("release_eligible") is True
                and verification.get("integrity_status") not in {"retracted", "withdrawn", "expression-of-concern"}
                and span_ref in valid_span_receipts
                and review_ok
            ):
                qualifying.append(row)
                qualifying_source_versions.append(str(verification.get("version_status", "")))
        if not qualifying:
            weak_only = rows and all(row.get("support_verdict") == "weakly-supports" for row in rows)
            code = "WEAK_SUPPORT_CANNOT_BE_HIGH_CONFIDENCE" if weak_only else "HIGH_CONFIDENCE_REQUIRES_STRICT_SUPPORT"
            findings.append(
                Finding(
                    "ERROR",
                    code,
                    f"{claim_id} lacks a supports row with strict seven-axis scope and valid source/span/review receipts",
                    str(paths["claim_support_matrix"]),
                    "Downgrade the claim or supply release-eligible support with all scope axes match/not-applicable.",
                )
            )
        elif qualifying_source_versions and all(value == "preprint" for value in qualifying_source_versions):
            findings.append(
                Finding(
                    "ERROR",
                    "PREPRINT_ONLY_CANNOT_BE_HIGH_CONFIDENCE",
                    f"{claim_id} is supported only by preprint-version sources",
                    str(paths["claim_support_matrix"]),
                    "Downgrade confidence or add version-of-record support.",
                )
            )

    if args.json:
        print(json.dumps({"findings": [asdict(finding) for finding in findings]}, indent=2))
    else:
        for finding in findings:
            print(f"{finding.level} {finding.code}: {finding.message}")
            if finding.path:
                print(f"  path: {finding.path}")
            if finding.fix_hint:
                print(f"  fix: {finding.fix_hint}")
        error_count = sum(finding.level == "ERROR" for finding in findings)
        warning_count = sum(finding.level == "WARNING" for finding in findings)
        print(f"claim support check: errors={error_count} warnings={warning_count}")
    return 1 if any(finding.level == "ERROR" for finding in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
