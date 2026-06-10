#!/usr/bin/env python3
"""Validate Biomedical Agent Teams workflow artifact bundles.

The validator is intentionally local and deterministic. It checks BMAT artifact
shape when jsonschema is available, then enforces workflow-label, independence,
stage, source-corpus, final-wording, and post-write release policies.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

try:
    import jsonschema  # type: ignore
except ImportError:  # pragma: no cover - depends on local environment
    jsonschema = None


BUNDLE_FILES = {
    "run_state": "run_state.json",
    "preflight": "preflight.json",
    "source_corpus": "source_corpus.json",
    "claim_ledger": "claim_ledger.json",
    "stage_evaluation": "stage_evaluation.json",
    "post_write_validation": "post_write_validation.json",
    "final_text": "final.md",
}

SCHEMA_FILES = {
    "run_state": "workflow-run.schema.json",
    "preflight": "preflight-contract.schema.json",
    "source_corpus": "source-corpus.schema.json",
    "stage_evaluation": "stage-evaluation.schema.json",
    "post_write_validation": "post-write-validation.schema.json",
}

PASSING_STAGE_STATUS = {"pass", "pass-with-caveats", "not-applicable"}
FULL_LABEL = "Full protocol followed"
BLOCKED_LABEL = "Blocked"
PARTIAL_LABEL = "Partial workflow; formal gates skipped"
HIGH_CONFIDENCE_STRENGTH = {"validated", "high-confidence", "high_confidence", "high confidence"}
FULL_PROTOCOL_SURFACES = {
    "spawned_subagent",
    "spawned subagent",
    "separate_model",
    "separate model",
    "tool_backed_validator",
    "tool-backed validator",
    "tool backed validator",
    "external_verifier",
    "external verifier",
    "human_reviewer",
    "human reviewer",
    "tool_corroborated",
    "tool-corroborated",
    "tool corroborated",
    "external database/api",
    "external database",
}
SAME_MODEL_MARKERS = {"same-model", "same model", "same_model", "self-ratification", "same pass"}


@dataclass(frozen=True)
class Finding:
    level: str
    code: str
    message: str
    path: str = ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate BMAT workflow artifacts.")
    parser.add_argument("--bundle", type=Path, help="Directory containing BMAT artifact files.")
    parser.add_argument("--run-state", type=Path)
    parser.add_argument("--preflight", type=Path)
    parser.add_argument("--source-corpus", type=Path)
    parser.add_argument("--claim-ledger", type=Path)
    parser.add_argument("--stage-evaluation", type=Path)
    parser.add_argument("--post-write-validation", type=Path)
    parser.add_argument("--final-text", type=Path)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON findings.")
    return parser.parse_args()


def read_json(path: Path, key: str, findings: list[Finding]) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        findings.append(Finding("WARN", "ARTIFACT_MISSING", f"{key} artifact not found", str(path)))
    except json.JSONDecodeError as exc:
        findings.append(Finding("ERROR", "INVALID_JSON", f"{key} is not valid JSON: {exc}", str(path)))
    return None


def read_text(path: Path, key: str, findings: list[Finding]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        findings.append(Finding("WARN", "ARTIFACT_MISSING", f"{key} artifact not found", str(path)))
    return ""


def input_paths(args: argparse.Namespace) -> dict[str, Path | None]:
    paths: dict[str, Path | None] = {}
    if args.bundle:
        for key, filename in BUNDLE_FILES.items():
            paths[key] = args.bundle / filename
    for key in BUNDLE_FILES:
        explicit = getattr(args, key, None)
        if explicit is not None:
            paths[key] = explicit
    return paths


def load_artifacts(paths: dict[str, Path | None], findings: list[Finding]) -> dict[str, Any]:
    artifacts: dict[str, Any] = {}
    for key in BUNDLE_FILES:
        path = paths.get(key)
        if path is None:
            artifacts[key] = "" if key == "final_text" else None
            continue
        if key == "final_text":
            artifacts[key] = read_text(path, key, findings)
        else:
            artifacts[key] = read_json(path, key, findings)
    return artifacts


def validate_schemas(artifacts: dict[str, Any], findings: list[Finding]) -> None:
    if jsonschema is None:
        findings.append(
            Finding(
                "WARN",
                "SCHEMA_VALIDATION_SKIPPED",
                "install jsonschema to validate contract schema shape",
            )
        )
        return

    contracts_dir = Path(__file__).resolve().parents[1] / "contracts"
    for key, schema_name in SCHEMA_FILES.items():
        artifact = artifacts.get(key)
        if artifact is None:
            continue
        schema_path = contracts_dir / schema_name
        try:
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            jsonschema.validate(artifact, schema)
        except FileNotFoundError:
            findings.append(Finding("WARN", "SCHEMA_FILE_MISSING", f"schema missing for {key}", str(schema_path)))
        except jsonschema.ValidationError as exc:  # type: ignore[union-attr]
            findings.append(Finding("ERROR", "SCHEMA_VALIDATION_FAILED", f"{key}: {exc.message}", str(schema_path)))


def normalized_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).strip().lower())


def workflow_label(run_state: Any) -> str:
    if isinstance(run_state, dict):
        return str(run_state.get("final_label", ""))
    return ""


def run_mode(run_state: Any) -> str:
    if isinstance(run_state, dict):
        return str(run_state.get("mode", ""))
    return ""


def required_stage_failures(run_state: Any) -> list[dict[str, Any]]:
    if not isinstance(run_state, dict):
        return []
    failures: list[dict[str, Any]] = []
    for stage in run_state.get("stages", []):
        if not isinstance(stage, dict):
            continue
        if stage.get("required") is True and stage.get("status") not in PASSING_STAGE_STATUS:
            failures.append(stage)
    return failures


def s3_statuses(run_state: Any, stage_evaluation: Any) -> list[str]:
    statuses: list[str] = []
    if isinstance(run_state, dict):
        for stage in run_state.get("stages", []):
            if isinstance(stage, dict) and str(stage.get("id", "")).upper() == "S3":
                statuses.append(str(stage.get("status", "")))
    if isinstance(stage_evaluation, dict):
        for stage in stage_evaluation.get("stages", []):
            if isinstance(stage, dict) and str(stage.get("stage_id", "")).upper() == "S3":
                statuses.append(str(stage.get("status", "")))
    return statuses


def iter_claims(claim_ledger: Any) -> list[dict[str, Any]]:
    if isinstance(claim_ledger, list):
        return [claim for claim in claim_ledger if isinstance(claim, dict)]
    if isinstance(claim_ledger, dict):
        for key in ("claims", "claim_ledger", "rows"):
            value = claim_ledger.get(key)
            if isinstance(value, list):
                return [claim for claim in value if isinstance(claim, dict)]
        if "claim_id" in claim_ledger:
            return [claim_ledger]
    return []


def claim_strength(claim: dict[str, Any]) -> str:
    for key in ("claim_strength", "strength", "release_ready_claim_strength"):
        if key in claim:
            return normalized_text(claim.get(key))
    return ""


def is_high_confidence_claim(claim: dict[str, Any]) -> bool:
    return claim_strength(claim) in HIGH_CONFIDENCE_STRENGTH


def source_ids_from_claim(claim: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for key in ("source_id", "source_ids"):
        value = claim.get(key)
        if isinstance(value, str):
            ids.extend(part.strip() for part in re.split(r"[,;]", value) if part.strip())
        elif isinstance(value, list):
            ids.extend(str(item).strip() for item in value if str(item).strip())

    evidence_items = claim.get("evidence_items", claim.get("evidence", []))
    if isinstance(evidence_items, str):
        ids.extend(part.strip() for part in re.split(r"[,;]", evidence_items) if part.strip())
    elif isinstance(evidence_items, list):
        for item in evidence_items:
            if isinstance(item, str) and item.strip():
                ids.append(item.strip())
            elif isinstance(item, dict):
                for key in ("source_id", "id"):
                    if item.get(key):
                        ids.append(str(item[key]).strip())
    return list(dict.fromkeys(ids))


def is_source_backed(claim: dict[str, Any]) -> bool:
    source_backed = claim.get("source_backed")
    if source_backed is True or normalized_text(source_backed) == "true":
        return True
    return bool(source_ids_from_claim(claim))


def included_sources(source_corpus: Any) -> set[str]:
    if not isinstance(source_corpus, dict):
        return set()
    sources = source_corpus.get("sources", [])
    out: set[str] = set()
    for source in sources:
        if not isinstance(source, dict):
            continue
        if source.get("inclusion_status") == "included" and source.get("source_id"):
            out.add(str(source["source_id"]))
    return out


def review_surface_text(post_write_validation: Any, run_state: Any) -> str:
    parts: list[str] = []
    if isinstance(post_write_validation, dict):
        for key in ("independent_review_status", "validation_surface", "validator_surface"):
            if post_write_validation.get(key):
                parts.append(str(post_write_validation[key]))
    if isinstance(run_state, dict):
        for lane_key in ("spawned_review_lanes", "team_spawn_lanes"):
            for lane in run_state.get(lane_key, []):
                if isinstance(lane, dict):
                    parts.extend(str(lane.get(field, "")) for field in ("role", "status", "rationale", "ledger_handoff"))
    return normalized_text(" ".join(parts))


def has_independent_surface(surface_text: str) -> bool:
    return any(marker in surface_text for marker in FULL_PROTOCOL_SURFACES)


def has_same_model_marker(surface_text: str) -> bool:
    return any(marker in surface_text for marker in SAME_MODEL_MARKERS)


def validate_full_protocol(artifacts: dict[str, Any], findings: list[Finding]) -> None:
    run_state = artifacts.get("run_state")
    preflight = artifacts.get("preflight")
    post_write = artifacts.get("post_write_validation")
    if workflow_label(run_state) != FULL_LABEL:
        return

    if run_state is None:
        findings.append(Finding("ERROR", "FULL_PROTOCOL_REQUIRES_RUN_STATE", "Full protocol requires run_state.json"))
    if preflight is None:
        findings.append(Finding("ERROR", "FULL_PROTOCOL_REQUIRES_PREFLIGHT", "Full protocol requires preflight.json"))
    if post_write is None:
        findings.append(
            Finding("ERROR", "FULL_PROTOCOL_REQUIRES_POST_WRITE", "Full protocol requires post_write_validation.json")
        )

    if isinstance(post_write, dict):
        verdict = post_write.get("final_validator_verdict")
        if verdict not in {"pass", "pass-with-revisions"}:
            findings.append(
                Finding(
                    "ERROR",
                    "FULL_PROTOCOL_REQUIRES_POST_WRITE_PASS",
                    "Full protocol requires post-write verdict pass or pass-with-revisions",
                )
            )

    for stage in required_stage_failures(run_state):
        findings.append(
            Finding(
                "ERROR",
                "FULL_PROTOCOL_REQUIRED_STAGE_FAILED",
                f"required stage {stage.get('id', 'unknown')} has status {stage.get('status', 'unknown')}",
            )
        )

    surface = review_surface_text(post_write, run_state)
    if has_same_model_marker(surface):
        findings.append(
            Finding(
                "ERROR",
                "FULL_PROTOCOL_REQUIRES_INDEPENDENT_SURFACE",
                "same-model validation cannot satisfy Full protocol followed",
            )
        )
    elif not has_independent_surface(surface):
        findings.append(
            Finding(
                "ERROR",
                "FULL_PROTOCOL_REQUIRES_INDEPENDENT_SURFACE",
                "Full protocol requires spawned, separate-model, tool-backed, external, human, or tool-corroborated review",
            )
        )


def validate_s3_policy(artifacts: dict[str, Any], findings: list[Finding]) -> None:
    claims = iter_claims(artifacts.get("claim_ledger"))
    high_confidence = [claim for claim in claims if is_high_confidence_claim(claim)]
    if not high_confidence:
        return

    statuses = s3_statuses(artifacts.get("run_state"), artifacts.get("stage_evaluation"))
    if not statuses and run_mode(artifacts.get("run_state")) in {"deep", "audit", "run"}:
        findings.append(
            Finding(
                "ERROR",
                "S3_REQUIRED_FOR_HIGH_CONFIDENCE",
                "high-confidence claims in deep/audit/run mode require an S3 validation status",
            )
        )
        return

    if any(status not in {"pass", "pass-with-caveats"} for status in statuses):
        ids = ", ".join(str(claim.get("claim_id", "unknown")) for claim in high_confidence)
        findings.append(
            Finding(
                "ERROR",
                "S3_BLOCKS_HIGH_CONFIDENCE",
                f"S3 did not pass, so high-confidence or validated claims are blocked: {ids}",
            )
        )


def validate_source_policy(artifacts: dict[str, Any], findings: list[Finding]) -> None:
    claims = iter_claims(artifacts.get("claim_ledger"))
    source_corpus = artifacts.get("source_corpus")
    included = included_sources(source_corpus)
    for claim in claims:
        if not is_source_backed(claim):
            continue
        claim_id = str(claim.get("claim_id", "unknown"))
        ids = source_ids_from_claim(claim)
        if source_corpus is None:
            findings.append(
                Finding("ERROR", "SOURCE_BACKED_CLAIM_REQUIRES_CORPUS", f"{claim_id} is source-backed but no corpus exists")
            )
            continue
        if not ids:
            findings.append(
                Finding("ERROR", "SOURCE_BACKED_CLAIM_MISSING_SOURCE", f"{claim_id} has no source_id")
            )
            continue
        for source_id in ids:
            if source_id not in included:
                findings.append(
                    Finding(
                        "ERROR",
                        "SOURCE_BACKED_CLAIM_MISSING_SOURCE",
                        f"{claim_id} references missing or non-included source {source_id}",
                    )
                )


def validate_final_wording(artifacts: dict[str, Any], findings: list[Finding]) -> None:
    final_text = artifacts.get("final_text") or ""
    if not final_text:
        return
    final_norm = normalized_text(final_text)
    for claim in iter_claims(artifacts.get("claim_ledger")):
        claim_id = str(claim.get("claim_id", "unknown"))
        allowed = str(claim.get("allowed_final_wording", "")).strip()
        audit_status = normalized_text(claim.get("audit_status", ""))
        atomic_claim = str(claim.get("atomic_claim", "")).strip()
        if audit_status in {"block", "blocked", "fail", "failed", "excluded"} and atomic_claim:
            if normalized_text(atomic_claim) in final_norm:
                findings.append(
                    Finding("ERROR", "BLOCKED_CLAIM_IN_FINAL_TEXT", f"{claim_id} appears in final text despite blocked status")
                )
        if not allowed:
            continue
        if audit_status in {"pass", "pass-with-caveats"} and is_high_confidence_claim(claim):
            if normalized_text(allowed) not in final_norm:
                findings.append(
                    Finding(
                        "ERROR",
                        "FINAL_WORDING_DRIFT",
                        f"{claim_id} is high-confidence but final text does not use allowed_final_wording",
                    )
                )


def validate_post_write_release(artifacts: dict[str, Any], findings: list[Finding]) -> None:
    post_write = artifacts.get("post_write_validation")
    label = workflow_label(artifacts.get("run_state"))
    if not isinstance(post_write, dict):
        return
    if post_write.get("final_validator_verdict") == "block" and label not in {BLOCKED_LABEL, PARTIAL_LABEL}:
        findings.append(
            Finding(
                "ERROR",
                "POST_WRITE_BLOCKS_RELEASE",
                "post-write block verdict requires final label Blocked or Partial workflow; formal gates skipped",
            )
        )


def validate_policies(artifacts: dict[str, Any], findings: list[Finding]) -> None:
    validate_full_protocol(artifacts, findings)
    validate_s3_policy(artifacts, findings)
    validate_source_policy(artifacts, findings)
    validate_final_wording(artifacts, findings)
    validate_post_write_release(artifacts, findings)


def emit(findings: list[Finding], as_json: bool) -> None:
    if not findings:
        findings = [Finding("INFO", "VALIDATION_PASSED", "BMAT artifact policy validation passed")]
    if as_json:
        print(json.dumps([asdict(finding) for finding in findings], indent=2, sort_keys=True))
        return
    for finding in findings:
        suffix = f" ({finding.path})" if finding.path else ""
        print(f"{finding.level} {finding.code}: {finding.message}{suffix}")


def main() -> int:
    args = parse_args()
    if not args.bundle and not any(getattr(args, key, None) for key in BUNDLE_FILES):
        print("ERROR NO_INPUT: provide --bundle or at least one artifact path", file=sys.stderr)
        return 2

    findings: list[Finding] = []
    artifacts = load_artifacts(input_paths(args), findings)
    validate_schemas(artifacts, findings)
    validate_policies(artifacts, findings)
    emit(findings, args.json)
    return 1 if any(finding.level == "ERROR" for finding in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
