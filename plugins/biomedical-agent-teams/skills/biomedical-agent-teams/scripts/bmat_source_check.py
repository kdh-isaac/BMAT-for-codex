#!/usr/bin/env python3
"""Generate or validate BMAT source-verification receipts.

The utility is deterministic and offline.  Fixture generation proves only test
wiring: it never marks an identifier or metadata as verified.  Release-eligible
live-tool, human, and local-file rows must be supplied explicitly with
``--verification-input`` and are checked against their recorded receipts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Iterable


SKILL_ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = SKILL_ROOT / "contracts"
SHA256_LENGTH = 64


@dataclass(frozen=True)
class Finding:
    level: str
    code: str
    message: str
    path: str = ""
    fix_hint: str = ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate non-release source verification or check explicit v2 receipts."
    )
    parser.add_argument("--source-corpus", type=Path, required=True)
    parser.add_argument("--claim-ledger", type=Path, required=True)
    parser.add_argument("--tool-call-ledger", type=Path)
    parser.add_argument(
        "--verification-input",
        type=Path,
        help="Explicit source_verification.json to validate; never inferred from tool calls.",
    )
    parser.add_argument(
        "--bundle-root",
        type=Path,
        help="Root for receipt paths; defaults to verification input/output parent.",
    )
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--offline-fixture",
        action="store_true",
        help="Generate fixture-only, not-checked rows for deterministic tests.",
    )
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def read_json(path: Path, findings: list[Finding], code_prefix: str = "INPUT") -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        findings.append(
            Finding(
                "ERROR",
                f"{code_prefix}_FILE_MISSING",
                "input JSON file is missing",
                str(path),
                "Provide the required artifact path.",
            )
        )
    except json.JSONDecodeError as exc:
        findings.append(
            Finding(
                "ERROR",
                f"{code_prefix}_INVALID_JSON",
                f"invalid JSON: {exc}",
                str(path),
                "Write valid UTF-8 JSON before rerunning the checker.",
            )
        )
    return None


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, indent=2, sort_keys=False) + "\n"
    temporary_name = ""
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
            temporary_name = handle.name
        os.replace(temporary_name, path)
    finally:
        if temporary_name:
            Path(temporary_name).unlink(missing_ok=True)


def plugin_version() -> str:
    version_path = SKILL_ROOT / "VERSION"
    try:
        return version_path.read_text(encoding="utf-8-sig").strip()
    except FileNotFoundError:
        return "unknown"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def iter_claims(claim_ledger: Any) -> list[dict[str, Any]]:
    if isinstance(claim_ledger, dict):
        for key in ("claims", "claim_ledger", "rows"):
            value = claim_ledger.get(key)
            if isinstance(value, list):
                return [claim for claim in value if isinstance(claim, dict)]
    if isinstance(claim_ledger, list):
        return [claim for claim in claim_ledger if isinstance(claim, dict)]
    return []


def value_as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [part.strip() for part in value.replace(";", ",").split(",") if part.strip()]
    return []


def claim_source_ids(claim: dict[str, Any]) -> list[str]:
    ids = value_as_list(claim.get("source_ids")) + value_as_list(claim.get("source_id"))
    evidence_items = claim.get("evidence_items", claim.get("evidence", []))
    if isinstance(evidence_items, list):
        for item in evidence_items:
            if isinstance(item, str):
                ids.append(item)
            elif isinstance(item, dict):
                ids.extend(value_as_list(item.get("source_id")))
    return list(dict.fromkeys(ids))


def claim_id(claim: dict[str, Any]) -> str:
    return str(claim.get("claim_id", "unknown")).strip() or "unknown"


def iter_sources(source_corpus: Any) -> list[dict[str, Any]]:
    if not isinstance(source_corpus, dict) or not isinstance(source_corpus.get("sources"), list):
        return []
    return [source for source in source_corpus["sources"] if isinstance(source, dict)]


def included_sources(source_corpus: Any) -> list[dict[str, Any]]:
    return [source for source in iter_sources(source_corpus) if source.get("inclusion_status") == "included"]


def iter_calls(tool_call_ledger: Any) -> list[dict[str, Any]]:
    if not isinstance(tool_call_ledger, dict) or not isinstance(tool_call_ledger.get("calls"), list):
        return []
    return [call for call in tool_call_ledger["calls"] if isinstance(call, dict)]


def iter_verification_rows(source_verification: Any) -> list[dict[str, Any]]:
    if not isinstance(source_verification, dict) or not isinstance(source_verification.get("rows"), list):
        return []
    return [row for row in source_verification["rows"] if isinstance(row, dict)]


def build_source_claim_map(claims: list[dict[str, Any]]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for claim in claims:
        for source_id in claim_source_ids(claim):
            out.setdefault(source_id, []).append(claim_id(claim))
    return {key: list(dict.fromkeys(value)) for key, value in out.items()}


def schema_version(payload: Any) -> str:
    return str(payload.get("schema_version", "")) if isinstance(payload, dict) else ""


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
                "jsonschema is required to validate v2 source receipts",
                str(artifact_path),
                "Install the project validation dependencies and rerun.",
            )
        )
        return
    schema = read_json(CONTRACTS / schema_name, findings, "CONTRACT")
    if not isinstance(schema, dict):
        return
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    for error in sorted(
        validator.iter_errors(payload),
        key=lambda item: "/".join(str(part) for part in item.absolute_path),
    ):
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


def warn_legacy(payload: Any, artifact_path: Path, findings: list[Finding]) -> bool:
    version = schema_version(payload)
    if version != "2.0":
        findings.append(
            Finding(
                "WARNING",
                "LEGACY_SCHEMA_V1_NOT_RELEASE_ELIGIBLE",
                f"schema_version {version or 'missing'} can be read for non-release generation but is not release eligible",
                str(artifact_path),
                "Migrate the artifact to schema_version 2.0 without inventing verification evidence.",
            )
        )
        return True
    return False


def safe_bundle_file(bundle_root: Path, reference: Any) -> tuple[Path | None, str | None]:
    text = str(reference or "").strip()
    if not text or "\x00" in text:
        return None, "path is empty or contains a NUL byte"
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


def check_file_receipt(
    *,
    bundle_root: Path,
    reference: Any,
    expected_sha256: Any,
    expected_size: Any | None,
    path_label: str,
    code_prefix: str,
    findings: list[Finding],
) -> None:
    resolved, error = safe_bundle_file(bundle_root, reference)
    if error:
        findings.append(
            Finding(
                "ERROR",
                f"{code_prefix}_PATH_INVALID",
                f"{path_label}: {error}",
                str(reference or ""),
                "Use a bundle-relative path without traversal segments.",
            )
        )
        return
    assert resolved is not None
    if not resolved.is_file():
        findings.append(
            Finding(
                "ERROR",
                f"{code_prefix}_MISSING",
                f"{path_label} does not exist inside the bundle",
                str(resolved),
                "Add the recorded receipt artifact to the bundle.",
            )
        )
        return
    actual_sha256 = sha256_file(resolved)
    if actual_sha256.lower() != str(expected_sha256 or "").lower():
        findings.append(
            Finding(
                "ERROR",
                f"{code_prefix}_HASH_MISMATCH",
                f"{path_label} SHA-256 does not match the receipt",
                str(resolved),
                "Recompute the SHA-256 from the exact bundled file; do not reuse a stale receipt.",
            )
        )
    if expected_size is not None and (not isinstance(expected_size, int) or resolved.stat().st_size != expected_size):
        findings.append(
            Finding(
                "ERROR",
                f"{code_prefix}_SIZE_MISMATCH",
                f"{path_label} size does not match the receipt",
                str(resolved),
                "Record the exact byte size of the bundled file.",
            )
        )


def duplicate_index(rows: Iterable[dict[str, Any]], key: str) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for row in rows:
        value = str(row.get(key, "")).strip()
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def generated_payload(
    source_corpus: Any,
    claim_ledger: Any,
    tool_call_ledger: Any,
    offline_fixture: bool,
) -> dict[str, Any]:
    claims = iter_claims(claim_ledger)
    source_claims = build_source_claim_map(claims)
    now = utc_now()
    rows: list[dict[str, Any]] = []
    for source in included_sources(source_corpus):
        source_id = str(source.get("source_id", "")).strip()
        identifier = str(source.get("identifier", "")).strip() or "unknown"
        is_fixture = offline_fixture
        rows.append(
            {
                "source_id": source_id or "unknown",
                "source_type": source.get("source_type", "other"),
                "identifier": identifier,
                "canonical_identifier": "not-checked",
                "identifier_status": "not-checked",
                "metadata_match": "not-checked",
                "verification_mode": "fixture" if is_fixture else "not-checked",
                "release_eligible": False,
                "fixture_only": is_fixture,
                "checked_at": now,
                "retrieval_surface": "offline-fixture" if is_fixture else "not-checked",
                "claim_ids_checked": source_claims.get(source_id, []),
                "verification_limitations": (
                    "test fixture only; identifier and metadata were not externally checked"
                    if is_fixture
                    else "identifier and metadata were not externally checked"
                ),
                "integrity_status": "unknown",
                "version_status": "unknown",
            }
        )
    workflow_run_id = ""
    if isinstance(source_corpus, dict):
        workflow_run_id = str(source_corpus.get("workflow_run_id", "")).strip()
    if not workflow_run_id and isinstance(tool_call_ledger, dict):
        workflow_run_id = str(tool_call_ledger.get("workflow_run_id", "")).strip()
    workflow_run_id = workflow_run_id or "manual-non-release"
    version = ""
    if isinstance(source_corpus, dict):
        version = str(source_corpus.get("plugin_version", "")).strip()
    return {
        "schema_version": "2.0",
        "verification_id": f"sv-{workflow_run_id}",
        "plugin_version": version or plugin_version(),
        "workflow_run_id": workflow_run_id,
        "checked_at": now,
        "rows": rows,
    }


def validate_claim_source_links(
    source_corpus: Any,
    claim_ledger: Any,
    claim_ledger_path: Path,
    findings: list[Finding],
) -> dict[str, list[str]]:
    claims = iter_claims(claim_ledger)
    source_claims = build_source_claim_map(claims)
    corpus_ids = {
        str(source.get("source_id", "")).strip()
        for source in included_sources(source_corpus)
        if str(source.get("source_id", "")).strip()
    }
    for claim in claims:
        for source_id in claim_source_ids(claim):
            if source_id not in corpus_ids:
                findings.append(
                    Finding(
                        "ERROR",
                        "CLAIM_SOURCE_NOT_INCLUDED",
                        f"{claim_id(claim)} references {source_id}, which is absent or not included in source_corpus",
                        str(claim_ledger_path),
                        "Include the source explicitly or remove it from the claim evidence links.",
                    )
                )
    return source_claims


def validate_source_receipts(
    *,
    source_corpus: Any,
    claim_ledger: Any,
    tool_call_ledger: Any,
    source_verification: Any,
    bundle_root: Path,
    source_verification_path: Path,
    claim_ledger_path: Path,
    findings: list[Finding],
) -> None:
    sources = iter_sources(source_corpus)
    rows = iter_verification_rows(source_verification)
    calls = iter_calls(tool_call_ledger)
    source_claims = validate_claim_source_links(source_corpus, claim_ledger, claim_ledger_path, findings)

    for source_id in duplicate_index(sources, "source_id"):
        findings.append(
            Finding(
                "ERROR",
                "SOURCE_CORPUS_DUPLICATE_SOURCE_ID",
                f"source_corpus contains duplicate source_id {source_id}",
                str(source_verification_path),
                "Use one canonical source row per source_id.",
            )
        )
    for source_id in duplicate_index(rows, "source_id"):
        findings.append(
            Finding(
                "ERROR",
                "SOURCE_VERIFICATION_DUPLICATE_SOURCE_ROW",
                f"source_verification contains duplicate source_id {source_id}",
                str(source_verification_path),
                "Retain exactly one verification row per source_id.",
            )
        )
    for call_id_value in duplicate_index(calls, "call_id"):
        findings.append(
            Finding(
                "ERROR",
                "TOOL_CALL_LEDGER_DUPLICATE_CALL_ID",
                f"tool_call_ledger contains duplicate call_id {call_id_value}",
                str(source_verification_path),
                "Use a unique call_id for each tool execution receipt.",
            )
        )

    corpus_by_id = {str(source.get("source_id", "")).strip(): source for source in sources}
    calls_by_id = {str(call.get("call_id", "")).strip(): call for call in calls}
    rows_by_source = {str(row.get("source_id", "")).strip(): row for row in rows}

    for source_id, linked_claims in source_claims.items():
        if linked_claims and source_id not in rows_by_source:
            findings.append(
                Finding(
                    "ERROR",
                    "SOURCE_BACKED_CLAIM_MISSING_SOURCE_VERIFICATION",
                    f"{source_id} is linked to claims but has no source verification row",
                    str(source_verification_path),
                    "Provide one explicit verification row or downgrade/remove the source-backed claims.",
                )
            )

    corpus_run_id = str(source_corpus.get("workflow_run_id", "")).strip() if isinstance(source_corpus, dict) else ""
    verification_run_id = (
        str(source_verification.get("workflow_run_id", "")).strip()
        if isinstance(source_verification, dict)
        else ""
    )
    if corpus_run_id and verification_run_id != corpus_run_id:
        findings.append(
            Finding(
                "ERROR",
                "SOURCE_VERIFICATION_WORKFLOW_RUN_ID_MISMATCH",
                "source_verification workflow_run_id does not match source_corpus",
                str(source_verification_path),
                "Regenerate the receipt for the active workflow run.",
            )
        )
    corpus_plugin = str(source_corpus.get("plugin_version", "")).strip() if isinstance(source_corpus, dict) else ""
    verification_plugin = (
        str(source_verification.get("plugin_version", "")).strip()
        if isinstance(source_verification, dict)
        else ""
    )
    if corpus_plugin and verification_plugin != corpus_plugin:
        findings.append(
            Finding(
                "ERROR",
                "SOURCE_VERIFICATION_PLUGIN_VERSION_MISMATCH",
                "source_verification plugin_version does not match source_corpus",
                str(source_verification_path),
                "Regenerate all release artifacts with one plugin version.",
            )
        )
    tool_run_id = (
        str(tool_call_ledger.get("workflow_run_id", "")).strip()
        if isinstance(tool_call_ledger, dict)
        else ""
    )
    tool_plugin = (
        str(tool_call_ledger.get("plugin_version", "")).strip()
        if isinstance(tool_call_ledger, dict)
        else ""
    )
    has_live_receipt = any(
        str(row.get("verification_mode", "")).strip() == "live-tool"
        and (row.get("release_eligible") is True or row.get("identifier_status") == "verified")
        for row in rows
    )
    if has_live_receipt and tool_run_id and verification_run_id != tool_run_id:
        findings.append(
            Finding(
                "ERROR",
                "SOURCE_VERIFICATION_TOOL_LEDGER_RUN_ID_MISMATCH",
                "source_verification workflow_run_id does not match tool_call_ledger",
                str(source_verification_path),
                "Use tool receipts produced by the same workflow run.",
            )
        )
    if has_live_receipt and tool_plugin and verification_plugin != tool_plugin:
        findings.append(
            Finding(
                "ERROR",
                "SOURCE_VERIFICATION_TOOL_LEDGER_PLUGIN_VERSION_MISMATCH",
                "source_verification plugin_version does not match tool_call_ledger",
                str(source_verification_path),
                "Regenerate receipts with the active plugin version.",
            )
        )

    for index, row in enumerate(rows):
        row_path = f"{source_verification_path}#rows/{index}"
        source_id = str(row.get("source_id", "")).strip()
        source = corpus_by_id.get(source_id)
        if source is None:
            findings.append(
                Finding(
                    "ERROR",
                    "SOURCE_VERIFICATION_UNKNOWN_SOURCE_ID",
                    f"verification row references unknown source_id {source_id}",
                    row_path,
                    "Use a source_id present in source_corpus.json.",
                )
            )
            continue
        if row.get("source_type") != source.get("source_type"):
            findings.append(
                Finding(
                    "ERROR",
                    "SOURCE_VERIFICATION_SOURCE_TYPE_MISMATCH",
                    f"{source_id} source_type differs from source_corpus",
                    row_path,
                    "Copy the canonical source_type from source_corpus.json.",
                )
            )
        if str(row.get("identifier", "")).strip() != str(source.get("identifier", "")).strip():
            findings.append(
                Finding(
                    "ERROR",
                    "SOURCE_VERIFICATION_IDENTIFIER_MISMATCH",
                    f"{source_id} identifier differs from source_corpus",
                    row_path,
                    "Use the source_corpus identifier and record normalization in canonical_identifier.",
                )
            )
        expected_claim_ids = set(source_claims.get(source_id, []))
        actual_claim_ids = set(value_as_list(row.get("claim_ids_checked")))
        if actual_claim_ids != expected_claim_ids:
            findings.append(
                Finding(
                    "ERROR",
                    "SOURCE_VERIFICATION_CLAIM_IDS_MISMATCH",
                    f"{source_id} claim_ids_checked does not exactly match claims linked to the source",
                    row_path,
                    "Record every and only claim ledger claim linked to this source.",
                )
            )

        mode = str(row.get("verification_mode", "")).strip()
        identifier_status = str(row.get("identifier_status", "")).strip()
        metadata_match = str(row.get("metadata_match", "")).strip()
        release_eligible = row.get("release_eligible") is True
        fixture_only = row.get("fixture_only") is True
        limitation = str(row.get("verification_limitations", ""))
        retrieval_surface = str(row.get("retrieval_surface", "")).strip().lower()
        if mode == "fixture":
            if identifier_status == "verified":
                findings.append(Finding("ERROR", "FIXTURE_VERIFICATION_CANNOT_BE_VERIFIED", f"{source_id} fixture row cannot be verified", row_path, "Use identifier_status=not-checked."))
            if metadata_match in {"pass", "pass-with-caveats"}:
                findings.append(Finding("ERROR", "FIXTURE_METADATA_CANNOT_PASS", f"{source_id} fixture row cannot pass metadata matching", row_path, "Use metadata_match=not-checked."))
            if release_eligible or not fixture_only:
                findings.append(Finding("ERROR", "FIXTURE_NOT_RELEASE_ELIGIBLE", f"{source_id} fixture row must be fixture_only and non-release", row_path, "Set fixture_only=true and release_eligible=false."))
            if "fixture" not in limitation.lower():
                findings.append(Finding("ERROR", "FIXTURE_LIMITATION_REQUIRED", f"{source_id} limitations must identify fixture-only evidence", row_path, "State explicitly that the row is a test fixture and was not externally checked."))
        if release_eligible and (identifier_status != "verified" or metadata_match not in {"pass", "pass-with-caveats"}):
            findings.append(Finding("ERROR", "RELEASE_SOURCE_NOT_VERIFIED", f"{source_id} release eligibility requires verified identity and matched metadata", row_path, "Provide a valid live-tool, human, or local-file receipt."))
        if release_eligible and (fixture_only or mode in {"fixture", "not-checked"}):
            findings.append(Finding("ERROR", "NON_RELEASE_VERIFICATION_MODE", f"{source_id} uses a non-release verification mode", row_path, "Supply an explicit live-tool, human, or local-file receipt."))
        if release_eligible and retrieval_surface in {"offline-fixture", "test-fixture"}:
            findings.append(Finding("ERROR", "FIXTURE_RETRIEVAL_SURFACE_NOT_RELEASE_ELIGIBLE", f"{source_id} uses a fixture retrieval surface", row_path, "Use a real live-tool, human, or local-file receipt surface."))
        if row.get("integrity_status") in {"retracted", "withdrawn"} and release_eligible:
            findings.append(Finding("ERROR", "RETRACTED_OR_WITHDRAWN_SOURCE_NOT_RELEASE_ELIGIBLE", f"{source_id} is retracted or withdrawn", row_path, "Exclude or downgrade the source; do not use it as release-eligible support."))
        if release_eligible and (
            row.get("integrity_status") not in {"current", "corrected", "not-applicable"}
            or row.get("version_status") in {"preprint", "unknown"}
            or str(row.get("canonical_identifier", "")).strip() in {"not-checked", "unknown", "unavailable"}
        ):
            findings.append(Finding("ERROR", "SOURCE_RELEASE_ELIGIBILITY_INVALID", f"{source_id} has unresolved integrity/version/canonical identity state", row_path, "Keep unknown/preprint evidence non-release or supply a current authoritative version receipt."))

        if mode == "live-tool" and (identifier_status == "verified" or release_eligible):
            tool_call_id = str(row.get("tool_call_id", "")).strip()
            call = calls_by_id.get(tool_call_id)
            if call is None:
                findings.append(Finding("ERROR", "SOURCE_VERIFICATION_TOOL_CALL_MISSING", f"{source_id} references missing tool_call_id {tool_call_id or '<empty>'}", row_path, "Link the exact source lookup call in tool_call_ledger.json."))
                continue
            if call.get("status") != "success":
                findings.append(Finding("ERROR", "SOURCE_VERIFICATION_TOOL_CALL_NOT_SUCCESSFUL", f"{source_id} references tool call with status={call.get('status')}", row_path, "Use only the successful call that produced this receipt."))
            if str(row.get("tool_id", "")).strip() != str(call.get("tool_id", "")).strip():
                findings.append(Finding("ERROR", "SOURCE_VERIFICATION_TOOL_ID_MISMATCH", f"{source_id} tool_id does not match the linked call", row_path, "Record the exact tool_id from the tool call receipt."))
            if source_id not in value_as_list(call.get("affected_source_ids")):
                findings.append(Finding("ERROR", "SOURCE_VERIFICATION_SOURCE_NOT_AFFECTED_BY_CALL", f"{source_id} is absent from call.affected_source_ids", row_path, "Add the source only to the call that actually queried it."))
            query_identifiers = set(value_as_list(call.get("query_identifiers")))
            if not query_identifiers.intersection({str(row.get("identifier", "")).strip(), str(row.get("canonical_identifier", "")).strip()}):
                findings.append(Finding("ERROR", "SOURCE_VERIFICATION_QUERY_IDENTIFIER_MISMATCH", f"{source_id} identifier is absent from call.query_identifiers", row_path, "Record the exact public identifier queried by the tool."))
            if str(row.get("output_ref", "")).strip() != str(call.get("output_ref", "")).strip():
                findings.append(Finding("ERROR", "SOURCE_VERIFICATION_OUTPUT_REF_MISMATCH", f"{source_id} output_ref differs from the linked call", row_path, "Reference the exact output artifact produced by the linked call."))
            if str(row.get("output_sha256", "")).lower() != str(call.get("output_sha256", "")).lower():
                findings.append(Finding("ERROR", "SOURCE_VERIFICATION_OUTPUT_SHA256_MISMATCH", f"{source_id} output_sha256 differs from the linked call", row_path, "Copy the exact output SHA-256 from the linked call receipt."))
            required_call_fields = (
                "query_identifiers",
                "affected_source_ids",
                "affected_claim_ids",
                "result_ids",
                "output_ref",
                "output_sha256",
                "started_at",
                "completed_at",
                "runtime_surface",
                "network_boundary",
                "allowed_data_class",
                "actual_data_class",
                "approval_ref",
                "query_redaction_applied",
                "retention_policy",
            )
            for field in required_call_fields:
                if field not in call or call.get(field) in (None, ""):
                    findings.append(Finding("ERROR", "RELEASE_SOURCE_TOOL_CALL_RECEIPT_INCOMPLETE", f"{source_id} linked call is missing {field}", row_path, "Record the complete source lookup execution receipt."))
            check_file_receipt(
                bundle_root=bundle_root,
                reference=row.get("output_ref"),
                expected_sha256=row.get("output_sha256"),
                expected_size=None,
                path_label="live-tool output",
                code_prefix="SOURCE_VERIFICATION_TOOL_OUTPUT",
                findings=findings,
            )
        elif mode == "human":
            check_file_receipt(
                bundle_root=bundle_root,
                reference=row.get("review_artifact_ref"),
                expected_sha256=row.get("review_artifact_sha256"),
                expected_size=None,
                path_label="human review artifact",
                code_prefix="SOURCE_VERIFICATION_HUMAN_REVIEW",
                findings=findings,
            )
        elif mode == "local-file":
            check_file_receipt(
                bundle_root=bundle_root,
                reference=row.get("local_snapshot_ref"),
                expected_sha256=row.get("local_snapshot_sha256"),
                expected_size=row.get("local_snapshot_size_bytes"),
                path_label="local source snapshot",
                code_prefix="SOURCE_VERIFICATION_LOCAL_SNAPSHOT",
                findings=findings,
            )


def main() -> int:
    args = parse_args()
    findings: list[Finding] = []
    if args.offline_fixture and args.verification_input:
        findings.append(
            Finding(
                "ERROR",
                "FIXTURE_AND_EXPLICIT_RECEIPT_CONFLICT",
                "--offline-fixture cannot be combined with --verification-input",
                str(args.verification_input),
                "Choose fixture generation or explicit receipt validation, not both.",
            )
        )

    source_corpus = read_json(args.source_corpus, findings, "SOURCE_CORPUS")
    claim_ledger = read_json(args.claim_ledger, findings, "CLAIM_LEDGER")
    tool_call_ledger = (
        read_json(args.tool_call_ledger, findings, "TOOL_CALL_LEDGER")
        if args.tool_call_ledger
        else None
    )

    if isinstance(source_corpus, dict):
        if not warn_legacy(source_corpus, args.source_corpus, findings):
            validate_schema(source_corpus, "source-corpus.schema.json", args.source_corpus, "SOURCE_CORPUS_SCHEMA_INVALID", findings)
    if isinstance(tool_call_ledger, dict):
        if not warn_legacy(tool_call_ledger, args.tool_call_ledger or Path("tool_call_ledger.json"), findings):
            validate_schema(tool_call_ledger, "tool-call-ledger.schema.json", args.tool_call_ledger or Path("tool_call_ledger.json"), "TOOL_CALL_LEDGER_SCHEMA_INVALID", findings)

    if args.verification_input:
        payload = read_json(args.verification_input, findings, "SOURCE_VERIFICATION")
        if isinstance(payload, dict):
            if warn_legacy(payload, args.verification_input, findings):
                findings.append(
                    Finding(
                        "ERROR",
                        "EXPLICIT_SOURCE_RECEIPT_REQUIRES_SCHEMA_V2",
                        "explicit verification receipts must use schema_version 2.0",
                        str(args.verification_input),
                        "Migrate without upgrading unknown or fixture evidence to verified.",
                    )
                )
            else:
                validate_schema(payload, "source-verification.schema.json", args.verification_input, "SOURCE_VERIFICATION_SCHEMA_INVALID", findings)
    else:
        payload = generated_payload(source_corpus, claim_ledger, tool_call_ledger, args.offline_fixture)
        validate_schema(payload, "source-verification.schema.json", args.out, "SOURCE_VERIFICATION_SCHEMA_INVALID", findings)

    if isinstance(payload, dict):
        bundle_root = args.bundle_root
        if bundle_root is None:
            bundle_root = (args.verification_input or args.out).parent
        validate_source_receipts(
            source_corpus=source_corpus,
            claim_ledger=claim_ledger,
            tool_call_ledger=tool_call_ledger,
            source_verification=payload,
            bundle_root=bundle_root,
            source_verification_path=args.verification_input or args.out,
            claim_ledger_path=args.claim_ledger,
            findings=findings,
        )
        if not args.verification_input or args.out.resolve() != args.verification_input.resolve():
            write_json_atomic(args.out, payload)

    if args.json:
        print(json.dumps({"findings": [asdict(finding) for finding in findings], "out": str(args.out)}, indent=2))
    else:
        for finding in findings:
            print(f"{finding.level} {finding.code}: {finding.message}")
            if finding.path:
                print(f"  path: {finding.path}")
            if finding.fix_hint:
                print(f"  fix: {finding.fix_hint}")
        if isinstance(payload, dict):
            action = "validated" if args.verification_input else "written"
            print(f"source_verification {action}: {args.out}")
    return 1 if any(finding.level == "ERROR" for finding in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
