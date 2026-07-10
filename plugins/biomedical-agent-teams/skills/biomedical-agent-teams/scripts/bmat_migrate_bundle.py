#!/usr/bin/env python3
"""Conservatively migrate legacy BMAT bundles to canonical v2 artifact shapes.

Migration is deliberately not verification. Legacy success, review, and source
verification assertions that lack v2 hash-bound receipts are downgraded and
listed in ``reverification_required.json``. The source tree is never modified,
and the destination must not already exist.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


SKILL_ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = SKILL_ROOT / "VERSION"
MIGRATION_REPORT = "migration_report.json"
REVERIFICATION_REPORT = "reverification_required.json"
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?$")
SCOPE_AXES = (
    "species",
    "cell_type",
    "assay",
    "endpoint",
    "population_or_model",
    "intervention_or_exposure",
    "biological_context",
)
SCOPE_VERDICTS = {"match", "partial", "mismatch", "not-applicable", "not-assessed"}
SOURCE_TYPES = {
    "PMID",
    "DOI",
    "accession",
    "NCT",
    "database-record",
    "local-file",
    "analysis-artifact",
    "software",
    "other",
}
DOMAIN_PACKS = {"generic-biomedical", "cell-therapy", "immuno-oncology"}


class MigrationError(RuntimeError):
    """A safe, user-facing migration failure."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def plugin_version() -> str:
    try:
        value = VERSION_FILE.read_text(encoding="utf-8-sig").strip()
    except OSError:
        value = ""
    return value if SEMVER_RE.fullmatch(value) else "1.2.0"


def nonempty(value: Any, fallback: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return fallback


def string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def valid_datetime(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    candidate = value.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", candidate):
        return f"{candidate}T00:00:00Z"
    try:
        datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    except ValueError:
        return None
    return candidate


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def is_link_or_reparse(path: Path) -> bool:
    if path.is_symlink():
        return True
    try:
        attributes = path.lstat().st_file_attributes
    except (AttributeError, OSError):
        return False
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def inspect_source_tree(source: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    file_count = 0
    for path in sorted(source.rglob("*"), key=lambda item: item.relative_to(source).as_posix()):
        relative = path.relative_to(source).as_posix()
        if is_link_or_reparse(path):
            raise MigrationError(f"source bundle contains a symbolic link or reparse point: {relative}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise MigrationError(f"source bundle contains an unsupported filesystem entry: {relative}")
        file_count += 1
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(bytes.fromhex(sha256_file(path)))
    return digest.hexdigest(), file_count


def load_json_objects(source: Path) -> dict[str, Any]:
    loaded: dict[str, Any] = {}
    for path in sorted(source.rglob("*.json")):
        relative = path.relative_to(source).as_posix()
        try:
            loaded[relative] = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise MigrationError(f"cannot parse JSON artifact {relative}: {exc}") from exc
    return loaded


def append_limitation(value: Any, note: str) -> str:
    existing = value.strip() if isinstance(value, str) else ""
    return f"{existing}; {note}" if existing else note


def source_type(value: Any) -> str:
    if value in SOURCE_TYPES:
        return str(value)
    normalized = str(value or "").strip().lower()
    aliases = {"pmid": "PMID", "doi": "DOI", "nct": "NCT", "dataset": "accession"}
    return aliases.get(normalized, "other")


def scope_match(value: Any) -> dict[str, str]:
    source = value if isinstance(value, dict) else {}
    return {
        axis: source.get(axis) if source.get(axis) in SCOPE_VERDICTS else "not-assessed"
        for axis in SCOPE_AXES
    }


def fixture_signal(row: dict[str, Any]) -> bool:
    if row.get("fixture_only") is True or row.get("verification_mode") == "fixture":
        return True
    surfaces = (
        row.get("retrieval_surface"),
        row.get("verification_limitations"),
        row.get("spawn_tool"),
    )
    return any(isinstance(value, str) and "fixture" in value.lower() for value in surfaces)


def safe_bundle_ref(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    path = Path(value)
    return not path.is_absolute() and ".." not in path.parts


def complete_v2_span(span: Any) -> bool:
    if not isinstance(span, dict):
        return False
    required = {
        "span_id",
        "source_id",
        "source_snapshot_ref",
        "source_snapshot_sha256",
        "locator",
        "section",
        "paragraph_or_table",
        "sentence_or_cell",
        "evidence_text_sha256",
        "short_evidence_excerpt",
        "retrieved_at",
        "extraction_actor",
        "limitations",
    }
    if not required <= span.keys():
        return False
    return (
        safe_bundle_ref(span.get("source_snapshot_ref"))
        and bool(SHA256_RE.fullmatch(str(span.get("source_snapshot_sha256", ""))))
        and bool(SHA256_RE.fullmatch(str(span.get("evidence_text_sha256", ""))))
        and valid_datetime(span.get("retrieved_at")) is not None
    )


@dataclass
class MigrationContext:
    workflow_run_id: str
    target_plugin_version: str
    migrated_at: str
    migrated_files: list[str] = field(default_factory=list)
    unchanged_files: list[str] = field(default_factory=list)
    legacy_unconverted_files: list[str] = field(default_factory=list)
    warnings: list[dict[str, str]] = field(default_factory=list)
    reverification: list[dict[str, str]] = field(default_factory=list)

    def require(self, artifact: str, path: str, reason_code: str, reason: str) -> None:
        row = {
            "artifact": artifact,
            "path": path,
            "reason_code": reason_code,
            "reason": reason,
        }
        if row not in self.reverification:
            self.reverification.append(row)


Converter = Callable[[dict[str, Any], str, MigrationContext], dict[str, Any]]


def convert_source_verification(data: dict[str, Any], relative: str, ctx: MigrationContext) -> dict[str, Any]:
    checked_at = valid_datetime(data.get("checked_at")) or ctx.migrated_at
    rows: list[dict[str, Any]] = []
    for index, legacy in enumerate(data.get("rows", [])):
        if not isinstance(legacy, dict):
            ctx.require(relative, f"rows[{index}]", "MALFORMED_LEGACY_ROW", "Non-object row was omitted.")
            continue
        fixture = fixture_signal(legacy)
        source_id = nonempty(legacy.get("source_id"), f"legacy-source-{index + 1}")
        identifier = nonempty(legacy.get("identifier"), "unknown")
        old_integrity = legacy.get("integrity_status")
        integrity = old_integrity if old_integrity in {
            "current", "corrected", "expression-of-concern", "retracted", "withdrawn", "unknown", "not-applicable"
        } else "unknown"
        old_version = legacy.get("version_status")
        version_status = old_version if old_version in {
            "version-of-record", "corrected-version", "preprint", "dataset-record", "registry-record",
            "software-release", "local-snapshot", "unknown", "not-applicable"
        } else "unknown"
        row: dict[str, Any] = {
            "source_id": source_id,
            "source_type": source_type(legacy.get("source_type")),
            "identifier": identifier,
            "canonical_identifier": nonempty(legacy.get("canonical_identifier"), "unknown"),
            "identifier_status": "not-checked",
            "metadata_match": "not-checked",
            "verification_mode": "fixture" if fixture else "not-checked",
            "release_eligible": False,
            "fixture_only": fixture,
            "checked_at": valid_datetime(legacy.get("checked_at")) or checked_at,
            "retrieval_surface": nonempty(
                legacy.get("retrieval_surface"), "offline-fixture" if fixture else "migration-not-checked"
            ),
            "claim_ids_checked": string_list(legacy.get("claim_ids_checked")),
            "verification_limitations": append_limitation(
                legacy.get("verification_limitations"),
                "Migrated from v1 without a v2 hash-bound verification receipt; re-verification required.",
            ),
            "integrity_status": integrity,
            "version_status": version_status,
        }
        for optional in ("canonical_title", "canonical_name", "canonical_date", "version"):
            if isinstance(legacy.get(optional), str) and legacy[optional].strip():
                row[optional] = legacy[optional].strip()
        rows.append(row)
        ctx.require(
            relative,
            f"rows[{index}]",
            "V2_SOURCE_REVERIFICATION_REQUIRED",
            f"Source {source_id} lacks portable v2 verification evidence; no verified or release-eligible state was carried forward.",
        )
    return {
        "schema_version": "2.0",
        "verification_id": nonempty(data.get("verification_id"), f"sv-{ctx.workflow_run_id}"),
        "plugin_version": ctx.target_plugin_version,
        "workflow_run_id": nonempty(data.get("workflow_run_id"), ctx.workflow_run_id),
        "checked_at": checked_at,
        "rows": rows,
    }


def convert_source_corpus(data: dict[str, Any], relative: str, ctx: MigrationContext) -> dict[str, Any]:
    sources: list[dict[str, Any]] = []
    for index, legacy in enumerate(data.get("sources", [])):
        if not isinstance(legacy, dict):
            ctx.require(relative, f"sources[{index}]", "MALFORMED_LEGACY_SOURCE", "Non-object source was omitted.")
            continue
        source_id = nonempty(legacy.get("source_id"), f"legacy-source-{index + 1}")
        spans = legacy.get("evidence_spans") if isinstance(legacy.get("evidence_spans"), list) else []
        portable_spans = [
            {key: span[key] for key in (
                "span_id", "source_id", "source_snapshot_ref", "source_snapshot_sha256", "locator",
                "section", "paragraph_or_table", "sentence_or_cell", "evidence_text_sha256",
                "short_evidence_excerpt", "retrieved_at", "extraction_actor", "limitations"
            )}
            for span in spans
            if complete_v2_span(span)
        ]
        old_status = legacy.get("inclusion_status")
        if old_status in {"excluded", "blocked", "not-checked"}:
            inclusion_status = old_status
        elif old_status == "included" and portable_spans:
            inclusion_status = "included"
        else:
            inclusion_status = "not-checked"
        source: dict[str, Any] = {
            "source_id": source_id,
            "source_type": source_type(legacy.get("source_type")),
            "identifier": nonempty(legacy.get("identifier"), "unknown"),
            "version_or_retrieval_date": nonempty(legacy.get("version_or_retrieval_date"), "unknown"),
            "inclusion_status": inclusion_status,
            "claim_use": nonempty(legacy.get("claim_use"), "not-checked"),
            "checked_by": nonempty(legacy.get("checked_by"), "migration-not-checked"),
            "limitations": append_limitation(
                legacy.get("limitations"), "Legacy source inclusion is not release eligible until v2 verification is completed."
            ),
        }
        for optional in ("title_or_name", "database_version", "query_or_origin"):
            if isinstance(legacy.get(optional), str) and legacy[optional].strip():
                source[optional] = legacy[optional].strip()
        retrieved_at = valid_datetime(legacy.get("retrieved_at"))
        if retrieved_at:
            source["retrieved_at"] = retrieved_at
        if inclusion_status == "included":
            source["evidence_spans"] = portable_spans
        elif old_status == "included":
            ctx.require(
                relative,
                f"sources[{index}].evidence_spans",
                "V2_EVIDENCE_SPAN_REQUIRED",
                f"Source {source_id} was downgraded to not-checked because its v1 spans lack snapshot and excerpt hashes.",
            )
        sources.append(source)
    return {
        "schema_version": "2.0",
        "corpus_id": nonempty(data.get("corpus_id"), f"corpus-{ctx.workflow_run_id}"),
        "plugin_version": ctx.target_plugin_version,
        "workflow_run_id": nonempty(data.get("workflow_run_id"), ctx.workflow_run_id),
        "created_at": valid_datetime(data.get("created_at")) or ctx.migrated_at,
        "query_or_origin": nonempty(data.get("query_or_origin"), "legacy bundle; original query unknown"),
        "sources": sources,
    }


CLAIM_FIELDS = {
    "claim_id", "atomic_claim", "claim_type", "claim_profile", "context", "source_backed", "source_id",
    "source_ids", "evidence_items", "evidence_relation", "uncertainty", "audit_status",
    "allowed_final_wording", "claim_strength", "tool_backed", "tool_id", "tool_ids", "result_id",
    "result_ids", "analysis_backed", "block_reason", "entity_ids", "evidence_edges", "scope_match",
    "entailment_verdict",
}


def convert_claim_ledger(data: dict[str, Any], relative: str, ctx: MigrationContext) -> dict[str, Any]:
    legacy_claims = data.get("claims")
    if not isinstance(legacy_claims, list):
        legacy_claims = data.get("claim_ledger") if isinstance(data.get("claim_ledger"), list) else data.get("rows", [])
    claims: list[dict[str, Any]] = []
    for index, legacy in enumerate(legacy_claims if isinstance(legacy_claims, list) else []):
        if not isinstance(legacy, dict):
            continue
        claim = {key: value for key, value in legacy.items() if key in CLAIM_FIELDS}
        claim["claim_id"] = nonempty(legacy.get("claim_id"), f"legacy-claim-{index + 1}")
        claim["atomic_claim"] = nonempty(legacy.get("atomic_claim"), "Legacy claim text unavailable.")
        claim["claim_profile"] = "blocked"
        claim["audit_status"] = "not-checked"
        claim["claim_strength"] = "not-checked"
        claim["entailment_verdict"] = "not-checked"
        claim["scope_match"] = scope_match(legacy.get("scope_match"))
        claim["block_reason"] = append_limitation(
            legacy.get("block_reason"), "Migrated claim requires v2 source and support re-verification."
        )
        claims.append(claim)
        ctx.require(
            relative,
            f"claims[{index}]",
            "V2_CLAIM_SUPPORT_RECHECK_REQUIRED",
            f"Claim {claim['claim_id']} was blocked pending v2 claim-support verification.",
        )
    return {
        "schema_version": "2.0",
        "claim_ledger_id": nonempty(data.get("claim_ledger_id"), f"ledger-{ctx.workflow_run_id}"),
        "plugin_version": ctx.target_plugin_version,
        "workflow_run_id": nonempty(data.get("workflow_run_id"), ctx.workflow_run_id),
        "created_at": valid_datetime(data.get("created_at")) or ctx.migrated_at,
        "claims": claims,
    }


def convert_claim_support(data: dict[str, Any], relative: str, ctx: MigrationContext) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for index, legacy in enumerate(data.get("rows", [])):
        if not isinstance(legacy, dict):
            continue
        claim_id = nonempty(legacy.get("claim_id"), f"legacy-claim-{index + 1}")
        row = {
            "claim_id": claim_id,
            "source_id": nonempty(legacy.get("source_id"), "unknown"),
            "evidence_span_ref": nonempty(legacy.get("evidence_span_ref"), "not-checked"),
            "support_verdict": "not-checked",
            "scope_match": scope_match(legacy.get("scope_match")),
            "overclaim_risk": "not-assessed",
            "allowed_in_final": False,
            "allowed_final_wording": nonempty(
                legacy.get("allowed_final_wording"), "Not eligible for final use until re-verification."
            ),
            "review_surface": "migration-not-checked",
            "review_actor_id": "not-applicable",
            "review_instance_id": "not-applicable",
            "review_artifact_ref": "not-applicable",
            "review_artifact_sha256": "not-applicable",
            "independent_review_required": False,
            "release_eligible": False,
            "limitations": append_limitation(
                legacy.get("limitations"), "v1 support and review assertions were not promoted during migration."
            ),
        }
        rows.append(row)
        ctx.require(
            relative,
            f"rows[{index}]",
            "V2_SUPPORT_AND_REVIEW_REQUIRED",
            f"Claim {claim_id} requires a v2 evidence span and hash-bound review receipt.",
        )
    return {
        "schema_version": "2.0",
        "support_matrix_id": nonempty(data.get("support_matrix_id"), f"support-{ctx.workflow_run_id}"),
        "plugin_version": ctx.target_plugin_version,
        "workflow_run_id": nonempty(data.get("workflow_run_id"), ctx.workflow_run_id),
        "created_at": valid_datetime(data.get("created_at")) or ctx.migrated_at,
        "rows": rows,
    }


def convert_review_manifest(data: dict[str, Any], relative: str, ctx: MigrationContext) -> dict[str, Any]:
    legacy_instances = data.get("review_instances") if isinstance(data.get("review_instances"), list) else []
    for index, instance in enumerate(legacy_instances):
        instance_id = instance.get("instance_id") if isinstance(instance, dict) else f"row-{index + 1}"
        ctx.require(
            relative,
            f"review_instances[{index}]",
            "V2_REVIEW_RECEIPT_REQUIRED",
            f"Legacy review {instance_id} was not carried forward as independent review without v2 runtime and artifact receipts.",
        )
    return {
        "schema_version": "2.0",
        "review_manifest_id": nonempty(data.get("review_manifest_id"), f"review-{ctx.workflow_run_id}"),
        "plugin_version": ctx.target_plugin_version,
        "workflow_run_id": nonempty(data.get("workflow_run_id"), ctx.workflow_run_id),
        "created_at": valid_datetime(data.get("created_at")) or ctx.migrated_at,
        "review_instances": [],
    }


def convert_tool_ledger(data: dict[str, Any], relative: str, ctx: MigrationContext) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for index, legacy in enumerate(data.get("calls", [])):
        if not isinstance(legacy, dict):
            continue
        call_id = nonempty(legacy.get("call_id"), f"legacy-call-{index + 1}")
        affected_sources = string_list(legacy.get("affected_source_ids"))
        provenance = legacy.get("provenance")
        if isinstance(provenance, dict) and isinstance(provenance.get("source_id"), str):
            if provenance["source_id"].strip() and provenance["source_id"].strip() not in affected_sources:
                affected_sources.append(provenance["source_id"].strip())
        row: dict[str, Any] = {
            "call_id": call_id,
            "tool_id": nonempty(legacy.get("tool_id"), "unknown"),
            "status": "unavailable",
            "inputs_digest": nonempty(legacy.get("inputs_digest"), "legacy inputs digest unavailable"),
            "affected_claim_ids": string_list(legacy.get("affected_claim_ids")),
            "downgrade_reason": "Legacy tool call lacks a v2 hash-bound output receipt; execution result requires re-verification.",
        }
        query_identifiers = string_list(legacy.get("query_identifiers"))
        if query_identifiers:
            row["query_identifiers"] = query_identifiers
        if affected_sources:
            row["affected_source_ids"] = affected_sources
        result_ids = string_list(legacy.get("result_ids"))
        if result_ids:
            row["result_ids"] = result_ids
        rows.append(row)
        ctx.require(
            relative,
            f"calls[{index}]",
            "V2_TOOL_RECEIPT_REQUIRED",
            f"Tool call {call_id} requires exact query, output artifact, and SHA-256 receipt verification.",
        )
    return {
        "schema_version": "2.0",
        "ledger_id": nonempty(data.get("ledger_id"), f"tools-{ctx.workflow_run_id}"),
        "plugin_version": ctx.target_plugin_version,
        "workflow_run_id": nonempty(data.get("workflow_run_id"), ctx.workflow_run_id),
        "created_at": valid_datetime(data.get("created_at")) or ctx.migrated_at,
        "calls": rows,
    }


RESULT_TYPES = {
    "literature", "omics", "clinical", "experiment-design", "translational", "tool-output",
    "reviewer-output", "statistic", "figure", "other",
}


def convert_results_integration(data: dict[str, Any], relative: str, ctx: MigrationContext) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for index, legacy in enumerate(data.get("rows", [])):
        if not isinstance(legacy, dict):
            continue
        row: dict[str, Any] = {
            "result_id": nonempty(legacy.get("result_id"), f"legacy-result-{index + 1}"),
            "result_type": legacy.get("result_type") if legacy.get("result_type") in RESULT_TYPES else "other",
            "source_ref": nonempty(legacy.get("source_ref"), "not-applicable"),
            "claim_ids": string_list(legacy.get("claim_ids")),
            "status": "not-reviewed",
            "evidence_direction": "not-applicable",
            "confidence": "not-assessed",
            "interpretation": nonempty(legacy.get("interpretation"), "Legacy result pending v2 review."),
            "limitations": append_limitation(legacy.get("limitations"), "Result is blocked pending v2 provenance review."),
            "ledger_action": "block",
        }
        for optional in ("effect_or_observation", "sample_or_model_scope", "statistical_support", "reviewer_or_human_gate"):
            if isinstance(legacy.get(optional), str) and legacy[optional].strip():
                row[optional] = legacy[optional].strip()
        rows.append(row)
        ctx.require(
            relative,
            f"rows[{index}]",
            "V2_RESULT_REVIEW_REQUIRED",
            f"Result {row['result_id']} requires v2 provenance and claim integration review.",
        )
    tool_log: list[dict[str, Any]] = []
    for legacy in data.get("tool_use_log", []):
        if not isinstance(legacy, dict):
            continue
        tool_log.append({
            "tool_id": nonempty(legacy.get("tool_id"), "unknown"),
            "invocation_surface": nonempty(legacy.get("invocation_surface"), "legacy-unknown"),
            "status": "unavailable",
            "used": False,
            "retrieval_date": nonempty(legacy.get("retrieval_date"), "unknown"),
            "source_corpus_rows": string_list(legacy.get("source_corpus_rows")),
            "result_rows": string_list(legacy.get("result_rows")),
            "downgrade_reason": "Legacy tool-use evidence is not portable without a v2 receipt.",
        })
    release_notes = string_list(data.get("release_notes"))
    release_notes.append("Migrated bundle is not release eligible until listed re-verification is complete.")
    return {
        "schema_version": "2.0",
        "integration_id": nonempty(data.get("integration_id"), f"integration-{ctx.workflow_run_id}"),
        "plugin_version": ctx.target_plugin_version,
        "workflow_run_id": nonempty(data.get("workflow_run_id"), ctx.workflow_run_id),
        "created_at": valid_datetime(data.get("created_at")) or ctx.migrated_at,
        "source_corpus_lock": "not-checked-after-v1-migration",
        "input_artifacts": string_list(data.get("input_artifacts")),
        "tool_use_log": tool_log,
        "rows": rows,
        "final_claim_policy": "blocked",
        "human_review_status": "pending",
        "release_notes": release_notes,
    }


def convert_stage_evaluation(data: dict[str, Any], relative: str, ctx: MigrationContext) -> dict[str, Any]:
    stages: list[dict[str, Any]] = []
    for index, legacy in enumerate(data.get("stages", [])):
        if not isinstance(legacy, dict):
            continue
        stage_id = legacy.get("stage_id")
        stages.append({
            "stage_id": stage_id if stage_id in {"S1", "S2", "S3", "S4", "S5", "other"} else "other",
            "stage_name": nonempty(legacy.get("stage_name"), f"Legacy stage {index + 1}"),
            "status": "block",
            "score": 0.0,
            "evidence": append_limitation(legacy.get("evidence"), "v2 gate evidence not re-verified"),
            "blocking_issues": string_list(legacy.get("blocking_issues")) + ["V2_REVERIFICATION_REQUIRED"],
        })
    ctx.require(relative, "stages", "V2_STAGE_GATES_REQUIRED", "Legacy stage pass states were blocked pending v2 gate checks.")
    return {
        "schema_version": "2.0",
        "evaluation_id": nonempty(data.get("evaluation_id"), f"stages-{ctx.workflow_run_id}"),
        "plugin_version": ctx.target_plugin_version,
        "workflow_run_id": nonempty(data.get("workflow_run_id"), ctx.workflow_run_id),
        "created_at": valid_datetime(data.get("created_at")) or ctx.migrated_at,
        "workflow_alias": nonempty(data.get("workflow_alias"), "biomedical-research-council"),
        "stages": stages,
        "overall_verdict": "block",
        "downgrade_rule_applied": "v1 artifacts require v2 re-verification",
    }


def convert_post_write(data: dict[str, Any], relative: str, ctx: MigrationContext) -> dict[str, Any]:
    checklist = [row for row in data.get("failure_mode_checklist", []) if isinstance(row, dict)]
    normalized_checklist = []
    for row in checklist:
        normalized_checklist.append({
            "failure_mode": nonempty(row.get("failure_mode"), "legacy failure mode"),
            "status": row.get("status") if row.get("status") in {"pass", "warn", "suspected", "not-applicable"} else "warn",
            "reason": nonempty(row.get("reason"), "legacy record"),
        })
    normalized_checklist.append({
        "failure_mode": "v1-to-v2 verification boundary",
        "status": "warn",
        "reason": "Migration does not establish source, tool, or independent-review verification.",
    })
    ctx.require(relative, "final_validator_verdict", "V2_POST_WRITE_VALIDATION_REQUIRED", "Post-write validation must be rerun on v2 artifacts.")
    return {
        "schema_version": "2.0",
        "validation_id": nonempty(data.get("validation_id"), f"post-write-{ctx.workflow_run_id}"),
        "plugin_version": ctx.target_plugin_version,
        "workflow_run_id": nonempty(data.get("workflow_run_id"), ctx.workflow_run_id),
        "checked_at": valid_datetime(data.get("checked_at")) or ctx.migrated_at,
        "final_validator_verdict": "block",
        "unsupported_final_claims": string_list(data.get("unsupported_final_claims")),
        "citation_or_provenance_mismatches": string_list(data.get("citation_or_provenance_mismatches")),
        "missing_uncertainty_or_limitations": string_list(data.get("missing_uncertainty_or_limitations")),
        "safety_ethics_privacy_issues": string_list(data.get("safety_ethics_privacy_issues")),
        "failure_mode_checklist": normalized_checklist,
        "excluded_claim_handling": nonempty(data.get("excluded_claim_handling"), "pending v2 review"),
        "independent_review_status": "not-checked-after-v1-migration",
        "minimal_required_corrections": string_list(data.get("minimal_required_corrections"))
        + ["Complete all entries in reverification_required.json."],
        "release_ready_claim_strength": "blocked-pending-v2-reverification",
    }


def normalized_domain(data: dict[str, Any]) -> str:
    value = data.get("selected_domain_pack", data.get("domain_pack"))
    return value if value in DOMAIN_PACKS else "generic-biomedical"


def convert_run_state(data: dict[str, Any], relative: str, ctx: MigrationContext) -> dict[str, Any]:
    review_lanes = []
    for row in data.get("spawned_review_lanes", []):
        if not isinstance(row, dict):
            continue
        review_lanes.append({
            "role": nonempty(row.get("role"), "unknown-reviewer"),
            "status": row.get("status") if row.get("status") in {"planned", "running", "complete", "skipped", "blocked"} else "blocked",
            "rationale": append_limitation(row.get("rationale"), "legacy review is not independently verified"),
            "ledger_handoff": nonempty(row.get("ledger_handoff"), "v2 re-review required"),
        })
    team_lanes = []
    for row in data.get("team_spawn_lanes", []):
        if not isinstance(row, dict):
            continue
        team_lanes.append({
            "team": nonempty(row.get("team"), "unknown-team"),
            "phase": nonempty(row.get("phase"), "legacy"),
            "depends_on": string_list(row.get("depends_on")),
            "status": row.get("status") if row.get("status") in {"planned", "running", "complete", "skipped", "blocked"} else "blocked",
            "nested_spawn_used": bool(row.get("nested_spawn_used", False)),
            "ledger_handoff": nonempty(row.get("ledger_handoff"), "v2 re-review required"),
        })
    instances = []
    for row in data.get("spawned_agent_instances", []):
        if not isinstance(row, dict):
            continue
        surface = row.get("execution_surface")
        if surface not in {"spawned_subagent", "tool_backed_validator", "external_verifier", "human_reviewer"}:
            surface = "tool_backed_validator"
        instance = {
            "instance_id": nonempty(row.get("instance_id"), f"legacy-instance-{len(instances) + 1}"),
            "agent_id": nonempty(row.get("agent_id"), "unknown-reviewer"),
            "execution_surface": surface,
            "status": row.get("status") if row.get("status") in {"planned", "running", "complete", "skipped", "blocked", "failed"} else "blocked",
            "input_scope": nonempty(row.get("input_scope"), "legacy scope unavailable"),
            "output_artifact": nonempty(row.get("output_artifact"), "not-applicable"),
            "checks_run": string_list(row.get("checks_run")),
            "ledger_handoff": nonempty(row.get("ledger_handoff"), "v2 re-review required"),
            "independent_review_eligible": False,
            "fixture_only": fixture_signal(row),
        }
        for optional in ("spawn_tool", "thread_or_task_id", "parent_run_id", "parent_instance_id"):
            if isinstance(row.get(optional), str) and row[optional].strip():
                instance[optional] = row[optional].strip()
        for optional in ("started_at", "completed_at"):
            converted = valid_datetime(row.get(optional))
            if converted:
                instance[optional] = converted
        instances.append(instance)
    stages = []
    for row in data.get("stages", []):
        if not isinstance(row, dict):
            continue
        old_status = row.get("status")
        status = "pass-with-caveats" if old_status == "pass" else old_status
        if status not in {"pass", "pass-with-caveats", "skipped", "block", "not-applicable"}:
            status = "block"
        stages.append({
            "id": nonempty(row.get("id"), f"legacy-stage-{len(stages) + 1}"),
            "required": bool(row.get("required", True)),
            "status": status,
            "evidence": append_limitation(row.get("evidence"), "v2 re-verification pending"),
        })
    domain = normalized_domain(data)
    downgrade_reasons = string_list(data.get("downgrade_reasons"))
    downgrade_reasons.append("Migrated from v1; verification and independent-review receipts require renewal.")
    ctx.require(relative, "final_label", "V2_RELEASE_GATES_REQUIRED", "Legacy final label was downgraded until v2 gates pass.")
    return {
        "schema_version": "2.0",
        "run_id": nonempty(data.get("run_id"), ctx.workflow_run_id),
        "created_at": valid_datetime(data.get("created_at")) or ctx.migrated_at,
        "alias": nonempty(data.get("alias"), "biomedical-research-council"),
        "mode": data.get("mode") if data.get("mode") in {"quick", "standard", "deep", "audit", "plan", "run"} else "audit",
        "plugin_version": ctx.target_plugin_version,
        "selected_domain_pack": domain,
        "domain_pack_version": nonempty(data.get("domain_pack_version"), ctx.target_plugin_version),
        "domain_pack_selection_reason": nonempty(
            data.get("domain_pack_selection_reason"), "Legacy bundle lacked a v2 domain-pack receipt; generic default used."
        ),
        "domain_specific_assumptions": string_list(data.get("domain_specific_assumptions")),
        "execution_strategy": data.get("execution_strategy")
        if data.get("execution_strategy") in {
            "inline_only", "inline_first_selective_review", "team_level_selective_dag", "user_requested_full_spawn", "blocked"
        } else "blocked",
        "nested_spawn_allowed": bool(data.get("nested_spawn_allowed", False)),
        "spawned_review_lanes": review_lanes,
        "team_spawn_lanes": team_lanes,
        "spawned_agent_instances": instances,
        "stages": stages,
        "final_label": "Partial workflow; formal gates skipped",
        "downgrade_reasons": downgrade_reasons,
    }


PLAYBOOKS = {
    "idea-discovery-team": "hypothesis-ranking",
    "omics-analysis-team": "omics-analysis",
    "evidence-audit-team": "evidence-audit",
    "experiment-design-team": "wet-lab-validation",
    "translational-scout-team": "clinical-translation",
}


def convert_lead_decision(data: dict[str, Any], relative: str, ctx: MigrationContext) -> dict[str, Any]:
    alias = nonempty(data.get("requested_alias"), "biomedical-research-council")
    domain = normalized_domain(data)
    skipped = []
    for row in data.get("skipped_lanes", []):
        if isinstance(row, dict):
            skipped.append({
                "lane": nonempty(row.get("lane"), "unknown-lane"),
                "reason": nonempty(row.get("reason"), "legacy reason unavailable"),
            })
        elif isinstance(row, str) and row.strip():
            skipped.append({"lane": row.strip(), "reason": "legacy reason unavailable"})
    ctx.require(relative, "domain_pack_selection_reason", "V2_DOMAIN_SELECTION_REVIEW_REQUIRED", "Confirm domain-pack selection after migration.")
    return {
        "schema_version": "2.0",
        "decision_id": nonempty(data.get("decision_id"), f"lead-{ctx.workflow_run_id}"),
        "workflow_run_id": nonempty(data.get("workflow_run_id"), ctx.workflow_run_id),
        "plugin_version": ctx.target_plugin_version,
        "created_at": valid_datetime(data.get("created_at")) or ctx.migrated_at,
        "selected_domain_pack": domain,
        "domain_pack_version": nonempty(data.get("domain_pack_version"), ctx.target_plugin_version),
        "domain_pack_selection_reason": nonempty(
            data.get("domain_pack_selection_reason"), "Legacy bundle did not record a v2 domain-pack selection receipt."
        ),
        "domain_specific_assumptions": string_list(data.get("domain_specific_assumptions")),
        "lead_scientist_agent_id": "life-science-lead-scientist",
        "requested_alias": alias,
        "selected_mode": data.get("selected_mode") if data.get("selected_mode") in {"quick", "standard", "deep", "audit", "plan", "run"} else "audit",
        "workflow_tier": data.get("workflow_tier") if data.get("workflow_tier") in {"compact", "full"} else "compact",
        "selected_playbook": data.get("selected_playbook") if data.get("selected_playbook") in set(PLAYBOOKS.values()) | {"mechanism-review", "public-omics-feasibility", "manuscript-or-grant"} else PLAYBOOKS.get(alias, "mechanism-review"),
        "omics_subtrack": data.get("omics_subtrack") if data.get("omics_subtrack") in {
            "bulk-rnaseq", "tenx-gex", "tenx-cellplex", "tenx-citeseq", "tenx-vdj", "tenx-multiome",
            "single-cell-other", "survival", "multi-omics", "other", "not-applicable", "track_ambiguous"
        } else "not-applicable",
        "execution_strategy": data.get("execution_strategy") if data.get("execution_strategy") in {
            "inline_only", "inline_first_selective_review", "team_level_selective_dag", "user_requested_full_spawn", "blocked"
        } else "blocked",
        "lead_route_required": bool(data.get("lead_route_required", True)),
        "mode_rule": nonempty(data.get("mode_rule"), "Legacy mode rule requires v2 review."),
        "decision_rationale": nonempty(data.get("decision_rationale"), "Migrated legacy decision; re-approval required."),
        "selected_lanes": string_list(data.get("selected_lanes")),
        "skipped_lanes": skipped,
        "spawned_review_plan": data.get("spawned_review_plan") if isinstance(data.get("spawned_review_plan"), dict) else {
            "allowed": False, "budget": 0, "selected_roles": [], "rationale": "migration does not spawn reviewers"
        },
        "team_spawn_plan": data.get("team_spawn_plan") if isinstance(data.get("team_spawn_plan"), dict) else {
            "allowed": False, "budget": 0, "selected_teams": [], "dependency_graph": [],
            "nested_spawn_allowed": False, "rationale": "migration does not spawn teams"
        },
        "post_team_audit_plan": nonempty(data.get("post_team_audit_plan"), "rerun v2 audit after migration"),
    }


def convert_preflight(data: dict[str, Any], relative: str, ctx: MigrationContext) -> dict[str, Any]:
    domain = normalized_domain(data)
    alias = nonempty(data.get("requested_alias"), "biomedical-research-council")
    mode = data.get("selected_mode") if data.get("selected_mode") in {"quick", "standard", "deep", "audit", "plan", "run"} else "audit"
    skipped = []
    for row in data.get("skipped_role_outputs_with_reason", []):
        if isinstance(row, dict) and {
            "reason_code", "reason_detail", "affected_roles", "downgrade_label", "approved_by", "recorded_at"
        } <= row.keys():
            skipped.append(row)
    payload: dict[str, Any] = {
        "schema_version": "2.0",
        "runtime_capability_preflight_id": nonempty(
            data.get("runtime_capability_preflight_id"), f"preflight-{ctx.workflow_run_id}"
        ),
        "plugin_version": ctx.target_plugin_version,
        "workflow_run_id": nonempty(data.get("workflow_run_id"), ctx.workflow_run_id),
        "created_at": valid_datetime(data.get("created_at")) or ctx.migrated_at,
        "requested_alias": alias,
        "selected_mode": mode,
        "deliverable_type": nonempty(data.get("deliverable_type"), "migrated legacy bundle"),
        "evidence_scope": data.get("evidence_scope") if isinstance(data.get("evidence_scope"), dict) else {
            "source_types": [], "species_or_model": "unknown", "date_or_version_needs": "unknown"
        },
        "risk_class": data.get("risk_class") if data.get("risk_class") in {"low", "moderate", "high"} else "moderate",
        "selected_domain_pack": domain,
        "domain_pack_version": nonempty(data.get("domain_pack_version"), ctx.target_plugin_version),
        "selection_reason": nonempty(data.get("selection_reason"), "Legacy bundle lacked a v2 domain-pack receipt."),
        "domain_specific_assumptions": string_list(data.get("domain_specific_assumptions")),
        "required_role_outputs": string_list(data.get("required_role_outputs")),
        "skipped_role_outputs_with_reason": skipped,
        "external_tools_allowed": data.get("external_tools_allowed") if isinstance(data.get("external_tools_allowed"), dict) else {
            "allowed": False, "limits": "migration performs no external verification"
        },
        "file_write_plan": data.get("file_write_plan") if isinstance(data.get("file_write_plan"), dict) else {
            "will_write_files": True, "allowed_paths": ["new migration output directory only"]
        },
        "stop_criteria": string_list(data.get("stop_criteria")) or ["v2 re-verification remains incomplete"],
        "checkpoint_plan": data.get("checkpoint_plan") if isinstance(data.get("checkpoint_plan"), list) else [],
        "execution_strategy": data.get("execution_strategy") if data.get("execution_strategy") in {
            "inline_only", "inline_first_selective_review", "team_level_selective_dag", "user_requested_full_spawn", "blocked"
        } else "blocked",
        "spawned_review_plan": data.get("spawned_review_plan") if isinstance(data.get("spawned_review_plan"), dict) else {
            "allowed": False, "budget": 0, "selected_roles": [], "rationale": "migration does not review"
        },
        "team_spawn_plan": data.get("team_spawn_plan") if isinstance(data.get("team_spawn_plan"), dict) else {
            "allowed": False, "budget": 0, "selected_teams": [], "dependency_graph": [],
            "nested_spawn_allowed": False, "rationale": "migration does not execute teams"
        },
        "all_role_spawn_avoidance_reason": nonempty(
            data.get("all_role_spawn_avoidance_reason"), "migration is a file transformation, not workflow execution"
        ),
        "nested_spawn_policy": data.get("nested_spawn_policy") if isinstance(data.get("nested_spawn_policy"), dict) else {
            "allowed": False, "authorization": "not requested", "limits": "migration only"
        },
        "post_team_audit_plan": nonempty(data.get("post_team_audit_plan"), "run the v2 validator and re-verification workflow"),
    }
    for optional in ("source_corpus_id", "workflow_dag_id"):
        if isinstance(data.get(optional), str) and data[optional].strip():
            payload[optional] = data[optional].strip()
    ctx.require(relative, "runtime", "V2_PREFLIGHT_REQUIRED", "Re-run runtime capability preflight before release validation.")
    return payload


CONVERTERS: dict[str, Converter] = {
    "run_state.json": convert_run_state,
    "runtime_capability_preflight.json": convert_preflight,
    "preflight.json": convert_preflight,
    "lead_decision.json": convert_lead_decision,
    "source_corpus.json": convert_source_corpus,
    "source_verification.json": convert_source_verification,
    "claim_ledger.json": convert_claim_ledger,
    "claim_support_matrix.json": convert_claim_support,
    "review_artifact_manifest.json": convert_review_manifest,
    "results_integration.json": convert_results_integration,
    "stage_evaluation.json": convert_stage_evaluation,
    "post_write_validation.json": convert_post_write,
    "tool_call_ledger.json": convert_tool_ledger,
}


def discover_workflow_run_id(objects: dict[str, Any], source_hash: str) -> tuple[str, bool]:
    preferred = objects.get("run_state.json")
    if isinstance(preferred, dict):
        value = preferred.get("run_id")
        if isinstance(value, str) and value.strip():
            return value.strip(), False
    for relative in sorted(objects):
        data = objects[relative]
        if not isinstance(data, dict):
            continue
        value = data.get("workflow_run_id")
        if isinstance(value, str) and value.strip():
            return value.strip(), False
    return f"migrated-{source_hash[:12]}", True


def migrate(source: Path, destination: Path, target_version: str) -> dict[str, Any]:
    source = source.resolve(strict=True)
    destination = destination.resolve(strict=False)
    if not source.is_dir():
        raise MigrationError(f"source bundle is not a directory: {source}")
    if source == destination:
        raise MigrationError("in-place migration is forbidden; choose a new output directory")
    if is_relative_to(destination, source):
        raise MigrationError("output directory must not be inside the source bundle")
    if destination.exists():
        raise MigrationError(f"output directory already exists; refusing to overwrite: {destination}")
    if not SEMVER_RE.fullmatch(target_version):
        raise MigrationError(f"invalid target plugin version: {target_version}")

    source_hash_before, source_file_count = inspect_source_tree(source)
    objects = load_json_objects(source)
    workflow_run_id, generated_run_id = discover_workflow_run_id(objects, source_hash_before)
    started_at = utc_now()
    context = MigrationContext(workflow_run_id, target_version, started_at)
    if generated_run_id:
        context.warnings.append({
            "code": "WORKFLOW_RUN_ID_GENERATED",
            "path": "bundle",
            "message": "No legacy workflow_run_id was present; a deterministic migration identity was assigned.",
        })

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.parent / f".{destination.name}.migration-{uuid.uuid4().hex}.tmp"
    try:
        shutil.copytree(source, temporary, copy_function=shutil.copy2, symlinks=True)
        for relative, data in sorted(objects.items()):
            if relative in {MIGRATION_REPORT, REVERIFICATION_REPORT}:
                continue
            if not isinstance(data, dict):
                context.unchanged_files.append(relative)
                continue
            schema_version = str(data.get("schema_version", "")).strip()
            converter = CONVERTERS.get(Path(relative).name)
            if schema_version == "2.0":
                context.unchanged_files.append(relative)
                continue
            if converter is None:
                context.unchanged_files.append(relative)
                if schema_version.startswith("1"):
                    context.legacy_unconverted_files.append(relative)
                    context.warnings.append({
                        "code": "LEGACY_ARTIFACT_CONVERTER_UNAVAILABLE",
                        "path": relative,
                        "message": "Artifact was copied unchanged and remains non-release-eligible until manually migrated.",
                    })
                    context.require(
                        relative,
                        "$",
                        "MANUAL_V2_MIGRATION_REQUIRED",
                        "No automatic converter exists for this legacy artifact.",
                    )
                continue
            converted = converter(data, relative, context)
            atomic_write_json(temporary / Path(relative), converted)
            context.migrated_files.append(relative)

        completed_at = utc_now()
        reverification_payload = {
            "schema_version": "2.0",
            "workflow_run_id": workflow_run_id,
            "plugin_version": target_version,
            "generated_at": completed_at,
            "release_eligible": False,
            "items": context.reverification,
        }
        atomic_write_json(temporary / REVERIFICATION_REPORT, reverification_payload)
        report = {
            "schema_version": "2.0",
            "migration_id": f"migration-{uuid.uuid4().hex}",
            "workflow_run_id": workflow_run_id,
            "source_bundle": str(source),
            "output_bundle": str(destination),
            "source_tree_sha256": source_hash_before,
            "source_file_count": source_file_count,
            "target_plugin_version": target_version,
            "started_at": started_at,
            "completed_at": completed_at,
            "source_unchanged": True,
            "release_eligible": False,
            "migrated_files": sorted(context.migrated_files),
            "unchanged_files": sorted(context.unchanged_files),
            "legacy_unconverted_files": sorted(context.legacy_unconverted_files),
            "warnings": context.warnings,
            "reverification_required_count": len(context.reverification),
            "reverification_list": REVERIFICATION_REPORT,
        }
        atomic_write_json(temporary / MIGRATION_REPORT, report)

        source_hash_after, file_count_after = inspect_source_tree(source)
        if source_hash_after != source_hash_before or file_count_after != source_file_count:
            raise MigrationError("source bundle changed during migration; output was not published")
        os.replace(temporary, destination)
        return report
    except Exception:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migrate a legacy BMAT bundle into conservative v2 artifact shapes without overwriting the source."
    )
    parser.add_argument(
        "--source", "--input", "--bundle", dest="source", required=True, type=Path,
        help="legacy bundle directory",
    )
    parser.add_argument(
        "--out", "--output", dest="out", type=Path,
        help="new output directory (default: <source-name>-v2 beside source)",
    )
    parser.add_argument(
        "--target-plugin-version", default=plugin_version(),
        help="target plugin semantic version (default: VERSION file)",
    )
    parser.add_argument("--json", action="store_true", help="print the migration report as JSON")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    source = args.source.resolve(strict=False)
    destination = args.out if args.out is not None else source.with_name(f"{source.name}-v2")
    try:
        report = migrate(source, destination, args.target_plugin_version)
    except (MigrationError, OSError) as exc:
        print(f"BMAT migration error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"BMAT v2 bundle written: {report['output_bundle']}")
        print(f"Migrated artifacts: {len(report['migrated_files'])}")
        print(f"Re-verification items: {report['reverification_required_count']}")
        print("Release eligible: false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
