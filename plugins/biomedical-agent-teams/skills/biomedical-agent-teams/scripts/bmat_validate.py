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
    "preflight": "runtime_capability_preflight.json",
    "source_corpus": "source_corpus.json",
    "claim_ledger": "claim_ledger.json",
    "stage_evaluation": "stage_evaluation.json",
    "post_write_validation": "post_write_validation.json",
    "final_text": "final.md",
}

BUNDLE_FILE_ALIASES = {
    "preflight": ("preflight.json",),
}

OPTIONAL_BUNDLE_FILES = {
    "lead_decision": "lead_decision.json",
    "results_integration": "results_integration.json",
    "tool_call_ledger": "tool_call_ledger.json",
    "workflow_dag": "workflow_dag.json",
    "omics_run_manifest": "omics_run_manifest.json",
}

INTERNAL_ARTIFACT_PATHS = "_artifact_paths"

SCHEMA_FILES = {
    "run_state": "workflow-run.schema.json",
    "preflight": "preflight-contract.schema.json",
    "lead_decision": "lead-decision.schema.json",
    "source_corpus": "source-corpus.schema.json",
    "claim_ledger": "claim-ledger.schema.json",
    "results_integration": "results-integration.schema.json",
    "tool_call_ledger": "tool-call-ledger.schema.json",
    "workflow_dag": "workflow-dag.schema.json",
    "omics_run_manifest": "omics-run-manifest.schema.json",
    "stage_evaluation": "stage-evaluation.schema.json",
    "post_write_validation": "post-write-validation.schema.json",
}

PASSING_STAGE_STATUS = {"pass", "pass-with-caveats", "not-applicable"}
FULL_LABEL = "Full protocol followed"
COMPACT_LABEL = "Compact standard workflow"
CONTRACT_LABEL = "Contract-shaped artifact bundle"
LIMITED_LABEL = "Limited capability-downgraded workflow"
NARRATIVE_LABEL = "Biomedical Agent Teams-informed narrative review"
BLOCKED_LABEL = "Blocked"
PARTIAL_LABEL = "Partial workflow; formal gates skipped"
WORKFLOW_LABELS = {
    FULL_LABEL,
    COMPACT_LABEL,
    CONTRACT_LABEL,
    LIMITED_LABEL,
    NARRATIVE_LABEL,
    PARTIAL_LABEL,
    BLOCKED_LABEL,
}
UTF8_BOM = "\ufeff"
NEGATED_LABEL_PREFIXES = (
    "not labeled ",
    "not label ",
    "not claiming ",
    "not claimed ",
    "not claim ",
    "not used ",
    "not using ",
    "not use ",
    "do not use ",
    "does not use ",
    "did not use ",
    "without ",
    "downgraded from ",
    "downgrade from ",
    "avoid claiming ",
    "not eligible for ",
)
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
INDEPENDENT_INSTANCE_SURFACES = {
    "spawned_subagent",
    "tool_backed_validator",
    "external_verifier",
    "human_reviewer",
}
TEAM_LEVEL_STRATEGY = "team_level_selective_dag"
REQUIRED_RUN_STATE_FIELDS = {
    "run_id",
    "alias",
    "mode",
    "plugin_version",
    "execution_strategy",
    "nested_spawn_allowed",
    "spawned_review_lanes",
    "team_spawn_lanes",
    "stages",
    "final_label",
    "downgrade_reasons",
}
OMICS_ALIASES = {"omics-analysis-team", "omics-team", "/omics-analysis-team", "/omics-team"}
OMICS_TRACKS = {
    "bulk-rnaseq",
    "tenx-gex",
    "tenx-cellplex",
    "tenx-citeseq",
    "tenx-vdj",
    "tenx-multiome",
    "single-cell-other",
    "survival",
    "multi-omics",
    "other",
}
TENX_TRACKS = {"tenx-gex", "tenx-cellplex", "tenx-citeseq", "tenx-vdj", "tenx-multiome"}
PRIVACY_SENSITIVE_DATA_CLASSES = {"local-private-approved", "deidentified-human", "controlled-access", "PHI"}
PUBLIC_ONLY_DATA_CLASSES = {"public-only", "not-applicable"}
OMICS_CORE_REVIEWERS = {"omics-code-reviewer", "omics-provenance-validator", "biostats-repro-auditor"}
OMICS_REVIEW_SKIP_EXCEPTION_MARKERS = {
    "spawned-subagent support unavailable",
    "spawned subagent support unavailable",
    "subagent support unavailable",
    "subagent unavailable",
    "runtime unavailable",
    "runtime does not support",
    "tool unavailable",
    "privacy-blocked",
    "privacy blocked",
    "blocked by privacy",
    "human gate blocked",
    "user requested compact",
    "user-requested compact",
    "compact inline-only",
    "explicitly out of scope",
    "budget-blocked",
    "budget blocked",
}
TOOL_USE_TERMS = (
    "queried",
    "checked",
    "ran",
    "used",
    "retrieved",
    "searched",
    "analyzed with",
    "analysed with",
    "tool-backed",
    "tool backed",
    "pubmed",
    "ncbi",
    "entrez",
    "geo",
    "clinicaltrials.gov",
    "uniprot",
    "reactome",
    "조회했다",
    "검증했다",
    "분석했다",
    "검색했다",
)
TOOL_SUCCESS_STATUS = {"success"}
TOOL_NON_SUCCESS_STATUS = {"skipped", "unavailable", "blocked", "failed"}


@dataclass(frozen=True)
class Finding:
    level: str
    code: str
    message: str
    path: str = ""
    fix_hint: str = ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate BMAT workflow artifacts.")
    parser.add_argument("--bundle", type=Path, help="Directory containing BMAT artifact files.")
    parser.add_argument("--run-state", type=Path)
    parser.add_argument("--preflight", type=Path)
    parser.add_argument("--source-corpus", type=Path)
    parser.add_argument("--claim-ledger", type=Path)
    parser.add_argument("--stage-evaluation", type=Path)
    parser.add_argument("--post-write-validation", type=Path)
    parser.add_argument("--lead-decision", type=Path)
    parser.add_argument("--results-integration", type=Path)
    parser.add_argument("--tool-call-ledger", type=Path)
    parser.add_argument("--workflow-dag", type=Path)
    parser.add_argument("--omics-run-manifest", type=Path)
    parser.add_argument("--final-text", type=Path)
    parser.add_argument(
        "--require-label",
        choices=sorted(WORKFLOW_LABELS),
        help=(
            "Require artifacts to satisfy this workflow label even when the "
            "label is not declared in run_state.json or final.md."
        ),
    )
    parser.add_argument(
        "--check-tool-ledger",
        action="store_true",
        help="Require deterministic tool-call ledger checks for tool-use wording and tool-backed claims.",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON findings.")
    return parser.parse_args()


def strip_bom(text: str) -> str:
    if text.startswith(UTF8_BOM):
        return text[len(UTF8_BOM) :]
    return text


def read_text_file(path: Path) -> str:
    return strip_bom(path.read_text(encoding="utf-8-sig"))


def read_json(path: Path, key: str, findings: list[Finding]) -> Any:
    try:
        return json.loads(read_text_file(path))
    except FileNotFoundError:
        findings.append(Finding("WARN", "ARTIFACT_MISSING", f"{key} artifact not found", str(path)))
    except json.JSONDecodeError as exc:
        findings.append(Finding("ERROR", "INVALID_JSON", f"{key} is not valid JSON: {exc}", str(path)))
    return None


def read_text(path: Path, key: str, findings: list[Finding]) -> str:
    try:
        return read_text_file(path)
    except FileNotFoundError:
        findings.append(Finding("WARN", "ARTIFACT_MISSING", f"{key} artifact not found", str(path)))
    return ""


def resolve_bundle_path(bundle: Path, key: str, filename: str) -> Path:
    canonical = bundle / filename
    if canonical.exists():
        return canonical
    for alias in BUNDLE_FILE_ALIASES.get(key, ()):
        candidate = bundle / alias
        if candidate.exists():
            return candidate
    return canonical


def input_paths(args: argparse.Namespace) -> dict[str, Path | None]:
    paths: dict[str, Path | None] = {}
    if args.bundle:
        for key, filename in BUNDLE_FILES.items():
            paths[key] = resolve_bundle_path(args.bundle, key, filename)
        for key, filename in OPTIONAL_BUNDLE_FILES.items():
            candidate = args.bundle / filename
            if candidate.exists():
                paths[key] = candidate
    for key in tuple(BUNDLE_FILES) + tuple(OPTIONAL_BUNDLE_FILES):
        explicit = getattr(args, key, None)
        if explicit is not None:
            paths[key] = explicit
    return paths


def load_artifacts(paths: dict[str, Path | None], findings: list[Finding]) -> dict[str, Any]:
    artifacts: dict[str, Any] = {}
    artifacts[INTERNAL_ARTIFACT_PATHS] = {
        key: str(path)
        for key, path in paths.items()
        if path is not None
    }
    for key in tuple(BUNDLE_FILES) + tuple(OPTIONAL_BUNDLE_FILES):
        path = paths.get(key)
        if path is None:
            artifacts[key] = "" if key == "final_text" else None
            continue
        if path.name in BUNDLE_FILE_ALIASES.get(key, ()):
            findings.append(
                Finding(
                    "WARN",
                    "LEGACY_BUNDLE_ARTIFACT_NAME",
                    (
                        f"{path.name} is accepted as a legacy alias; use "
                        f"{BUNDLE_FILES[key]} as the canonical artifact name"
                    ),
                    str(path),
                )
            )
        if key == "final_text":
            artifacts[key] = read_text(path, key, findings)
        else:
            artifacts[key] = read_json(path, key, findings)
    return artifacts


def artifact_base_dir(artifacts: dict[str, Any]) -> Path | None:
    paths = artifacts.get(INTERNAL_ARTIFACT_PATHS)
    if not isinstance(paths, dict):
        return None
    for key in ("run_state", "preflight", "final_text"):
        value = paths.get(key)
        if isinstance(value, str) and value:
            return Path(value).resolve().parent
    return None


def local_artifact_ref_path(artifacts: dict[str, Any], ref: str) -> Path | None:
    value = ref.strip()
    if not value or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", value):
        return None
    path_text = value.split("#", 1)[0].strip()
    if not path_text:
        return None
    path = Path(path_text)
    if path.is_absolute():
        return path.resolve()
    base_dir = artifact_base_dir(artifacts)
    if base_dir is None:
        return None
    return (base_dir / path).resolve()


def validate_local_artifact_ref_exists(
    artifacts: dict[str, Any],
    ref: str,
    *,
    code: str,
    message: str,
    path_label: str,
    findings: list[Finding],
) -> None:
    resolved = local_artifact_ref_path(artifacts, ref)
    if resolved is None:
        return
    base_dir = artifact_base_dir(artifacts)
    if base_dir is not None:
        try:
            resolved.relative_to(base_dir.resolve())
        except ValueError:
            findings.append(
                Finding(
                    "ERROR",
                    f"{code}_OUTSIDE_BUNDLE",
                    f"{message}; local artifact references must stay inside the bundle",
                    path_label,
                )
            )
            return
    if not resolved.exists():
        findings.append(Finding("ERROR", code, message, path_label))


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
            schema = json.loads(read_text_file(schema_path))
            jsonschema.validate(artifact, schema)
        except FileNotFoundError:
            findings.append(Finding("WARN", "SCHEMA_FILE_MISSING", f"schema missing for {key}", str(schema_path)))
        except jsonschema.ValidationError as exc:  # type: ignore[union-attr]
            findings.append(Finding("ERROR", "SCHEMA_VALIDATION_FAILED", f"{key}: {exc.message}", str(schema_path)))


def validate_required_artifact_fields(artifacts: dict[str, Any], findings: list[Finding]) -> None:
    run_state = artifacts.get("run_state")
    if run_state is None:
        return
    if not isinstance(run_state, dict):
        findings.append(Finding("ERROR", "RUN_STATE_INVALID_SHAPE", "run_state must be a JSON object"))
        return
    for field in sorted(REQUIRED_RUN_STATE_FIELDS - set(run_state)):
        findings.append(
            Finding(
                "ERROR",
                "RUN_STATE_REQUIRED_FIELD_MISSING",
                f"{field} is required in run_state",
                "run_state.json",
            )
        )


def normalized_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).strip().lower())


def workflow_label(run_state: Any) -> str:
    if isinstance(run_state, dict):
        return str(run_state.get("final_label", ""))
    return ""


def label_mention_is_negated(final_norm: str, start: int) -> bool:
    prefix = final_norm[max(0, start - 100) : start]
    return any(prefix.endswith(marker) for marker in NEGATED_LABEL_PREFIXES)


def has_affirmative_label_mention(final_norm: str, label_norm: str) -> bool:
    start = final_norm.find(label_norm)
    while start != -1:
        if not label_mention_is_negated(final_norm, start):
            return True
        start = final_norm.find(label_norm, start + len(label_norm))
    return False


def declared_workflow_labels(artifacts: dict[str, Any], required_label: str | None = None) -> set[str]:
    labels: set[str] = set()
    if required_label:
        labels.add(required_label)

    run_state_label = workflow_label(artifacts.get("run_state")).strip()
    if run_state_label:
        labels.add(run_state_label)

    final_text = artifacts.get("final_text") or ""
    final_norm = normalized_text(final_text)
    for label in WORKFLOW_LABELS:
        if has_affirmative_label_mention(final_norm, normalized_text(label)):
            labels.add(label)
    return labels


def validate_required_label(
    artifacts: dict[str, Any],
    findings: list[Finding],
    required_label: str | None,
) -> None:
    if not required_label:
        return
    run_state_label = workflow_label(artifacts.get("run_state")).strip()
    if run_state_label and run_state_label != required_label:
        findings.append(
            Finding(
                "ERROR",
                "REQUIRED_LABEL_MISMATCH",
                f"required label {required_label!r} conflicts with run_state final_label {run_state_label!r}",
                "run_state.json",
            )
        )


def run_mode(run_state: Any) -> str:
    if isinstance(run_state, dict):
        return str(run_state.get("mode", ""))
    return ""


def execution_strategy(run_state: Any) -> str:
    if isinstance(run_state, dict):
        return str(run_state.get("execution_strategy", ""))
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


def value_as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [part.strip() for part in re.split(r"[,;]", value) if part.strip()]
    return []


def value_is_truthy(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, str):
        return normalized_text(value) in {"true", "yes", "used", "required", "external", "tool-backed"}
    if isinstance(value, (list, dict)):
        return bool(value)
    return False


def claim_id(claim: dict[str, Any]) -> str:
    return str(claim.get("claim_id", "unknown")).strip() or "unknown"


def claim_tool_ids(claim: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for key in ("tool_id", "tool_ids"):
        ids.extend(value_as_list(claim.get(key)))
    return list(dict.fromkeys(ids))


def claim_result_ids(claim: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for key in ("result_id", "result_ids"):
        ids.extend(value_as_list(claim.get(key)))
    return list(dict.fromkeys(ids))


def is_tool_backed_claim(claim: dict[str, Any]) -> bool:
    return value_is_truthy(claim.get("tool_backed")) or bool(claim_tool_ids(claim) or claim_result_ids(claim))


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


def source_backed_bundle(artifacts: dict[str, Any]) -> bool:
    if included_sources(artifacts.get("source_corpus")):
        return True
    return any(is_source_backed(claim) for claim in iter_claims(artifacts.get("claim_ledger")))


def lead_decision_required_reasons(
    artifacts: dict[str, Any],
    required_label: str | None = None,
) -> list[tuple[str, str]]:
    run_state = artifacts.get("run_state")
    mode = normalized_text(run_mode(run_state))
    strategy = execution_strategy(run_state)
    labels = declared_workflow_labels(artifacts, required_label)
    reasons: list[tuple[str, str]] = []
    if FULL_LABEL in labels:
        reasons.append(("LEAD_DECISION_REQUIRED_FULL_PROTOCOL", "Full protocol requires lead_decision.json"))
    if mode == "deep":
        reasons.append(("LEAD_DECISION_REQUIRED_DEEP_MODE", "deep mode requires lead_decision.json"))
    if mode == "audit":
        reasons.append(("LEAD_DECISION_REQUIRED_AUDIT_MODE", "audit mode requires lead_decision.json"))
    if mode == "standard" and source_backed_bundle(artifacts):
        reasons.append(
            (
                "LEAD_DECISION_REQUIRED_STANDARD_SOURCE_BACKED",
                "standard source-backed output requires lead_decision.json",
            )
        )
    if strategy == TEAM_LEVEL_STRATEGY:
        reasons.append(("LEAD_DECISION_REQUIRED_TEAM_DAG", "team_level_selective_dag requires lead_decision.json"))
    return list(dict.fromkeys(reasons))


def validate_lead_decision_policy(
    artifacts: dict[str, Any],
    findings: list[Finding],
    required_label: str | None = None,
) -> None:
    lead_decision = artifacts.get("lead_decision")
    reasons = lead_decision_required_reasons(artifacts, required_label)
    if reasons and lead_decision is None:
        for code, message in reasons:
            findings.append(
                Finding(
                    "ERROR",
                    code,
                    message,
                    OPTIONAL_BUNDLE_FILES["lead_decision"],
                    "Create lead_decision.json from templates/lead-decision-template.md and align workflow_run_id, requested_alias, selected_mode, execution_strategy, selected lanes, and review plans with run_state/preflight.",
                )
            )
        return
    if lead_decision is None or not isinstance(lead_decision, dict):
        return

    run_state = artifacts.get("run_state")
    preflight = artifacts.get("preflight")
    if isinstance(run_state, dict):
        expected_pairs = {
            "workflow_run_id": run_state.get("run_id"),
            "requested_alias": run_state.get("alias"),
            "selected_mode": run_state.get("mode"),
            "execution_strategy": run_state.get("execution_strategy"),
        }
        for field, expected in expected_pairs.items():
            actual = lead_decision.get(field)
            if expected is not None and actual is not None and str(actual) != str(expected):
                findings.append(
                    Finding(
                        "ERROR",
                        "LEAD_DECISION_RUN_STATE_MISMATCH",
                        f"lead_decision.{field}={actual!r} does not match run_state value {expected!r}",
                        OPTIONAL_BUNDLE_FILES["lead_decision"],
                        "Update lead_decision.json after changing run_state.json; the lead decision is the auditable routing surface.",
                    )
                )
    if isinstance(preflight, dict):
        expected_alias = preflight.get("requested_alias")
        expected_mode = preflight.get("selected_mode")
        if expected_alias and lead_decision.get("requested_alias") and str(lead_decision["requested_alias"]) != str(expected_alias):
            findings.append(
                Finding(
                    "ERROR",
                    "LEAD_DECISION_PREFLIGHT_ALIAS_MISMATCH",
                    "lead_decision requested_alias must match preflight requested_alias",
                    OPTIONAL_BUNDLE_FILES["lead_decision"],
                    "Keep the lead decision, runtime preflight, and run state as one routing contract.",
                )
            )
        if expected_mode and lead_decision.get("selected_mode") and str(lead_decision["selected_mode"]) != str(expected_mode):
            findings.append(
                Finding(
                    "ERROR",
                    "LEAD_DECISION_PREFLIGHT_MODE_MISMATCH",
                    "lead_decision selected_mode must match preflight selected_mode",
                    OPTIONAL_BUNDLE_FILES["lead_decision"],
                    "Keep the lead decision, runtime preflight, and run state as one routing contract.",
                )
            )


def requested_omics_track(artifacts: dict[str, Any]) -> str:
    run_state = artifacts.get("run_state")
    preflight = artifacts.get("preflight")
    for owner, key in ((run_state, "omics_track"), (preflight, "requested_omics_track")):
        if isinstance(owner, dict):
            value = normalized_text(owner.get(key))
            if value and value != "not-applicable":
                return value
    return ""


def validate_omics_manifest_policy(artifacts: dict[str, Any], findings: list[Finding]) -> None:
    run_state = artifacts.get("run_state")
    alias = normalized_text(run_state.get("alias")) if isinstance(run_state, dict) else ""
    track = requested_omics_track(artifacts)
    manifest = artifacts.get("omics_run_manifest")
    manifest_required = alias in OMICS_ALIASES or track in OMICS_TRACKS
    if manifest_required and manifest is None:
        findings.append(
            Finding(
                "ERROR",
                "OMICS_RUN_MANIFEST_REQUIRED",
                "omics-analysis workflows and explicit omics tracks require omics_run_manifest.json",
                OPTIONAL_BUNDLE_FILES["omics_run_manifest"],
                "Create omics_run_manifest.json using contracts/omics-run-manifest.schema.json; include 10x Cell Ranger artifacts for tenx tracks or count/design provenance for bulk-rnaseq.",
            )
        )
        return
    if manifest is None or not isinstance(manifest, dict):
        return
    manifest_track = normalized_text(manifest.get("track"))
    if track and manifest_track and track != manifest_track:
        findings.append(
            Finding(
                "ERROR",
                "OMICS_RUN_MANIFEST_TRACK_MISMATCH",
                f"omics_run_manifest track {manifest_track!r} does not match requested track {track!r}",
                OPTIONAL_BUNDLE_FILES["omics_run_manifest"],
                "Keep run_state.omics_track, preflight.requested_omics_track, lead_decision.omics_subtrack, and omics_run_manifest.track aligned.",
            )
        )
    if manifest_track in TENX_TRACKS:
        bio_policy = manifest.get("biological_unit_policy", {})
        if isinstance(bio_policy, dict) and bio_policy.get("pseudobulk_required") is False:
            findings.append(
                Finding(
                    "WARN",
                    "TENX_PSEUDOBULK_NOT_REQUIRED",
                    "10x cross-sample analysis should justify why donor/sample-aware pseudobulk is not required",
                    OPTIONAL_BUNDLE_FILES["omics_run_manifest"],
                    "Set pseudobulk_required=true for cross-sample differential testing, or document a bounded cell-level descriptive use.",
                )
            )


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
        for instance in run_state.get("spawned_agent_instances", []):
            if isinstance(instance, dict):
                status = str(instance.get("status", ""))
                if status == "complete":
                    parts.extend(
                        str(instance.get(field, ""))
                        for field in ("agent_id", "execution_surface", "status", "spawn_tool", "ledger_handoff")
                    )
    return normalized_text(" ".join(parts))


def has_independent_surface(surface_text: str) -> bool:
    return any(marker in surface_text for marker in FULL_PROTOCOL_SURFACES)


def has_same_model_marker(surface_text: str) -> bool:
    return any(marker in surface_text for marker in SAME_MODEL_MARKERS)


def registry_agent_ids(findings: list[Finding]) -> set[str]:
    registry_path = Path(__file__).resolve().parents[1] / "agent-registry.json"
    try:
        registry = json.loads(read_text_file(registry_path))
    except FileNotFoundError:
        findings.append(Finding("ERROR", "AGENT_REGISTRY_MISSING", "agent-registry.json is missing", str(registry_path)))
        return set()
    except json.JSONDecodeError as exc:
        findings.append(Finding("ERROR", "AGENT_REGISTRY_INVALID_JSON", f"agent-registry.json is invalid: {exc}", str(registry_path)))
        return set()

    agents = registry.get("agents", []) if isinstance(registry, dict) else []
    return {
        str(agent.get("agent_id"))
        for agent in agents
        if isinstance(agent, dict) and str(agent.get("agent_id", "")).strip()
    }


def spawned_agent_instances(run_state: Any) -> list[dict[str, Any]]:
    if not isinstance(run_state, dict):
        return []
    instances = run_state.get("spawned_agent_instances", [])
    if not isinstance(instances, list):
        return []
    return [instance for instance in instances if isinstance(instance, dict)]


def complete_independent_instances(run_state: Any) -> list[dict[str, Any]]:
    return [
        instance
        for instance in spawned_agent_instances(run_state)
        if instance.get("status") == "complete" and instance.get("execution_surface") in INDEPENDENT_INSTANCE_SURFACES
    ]


def spawned_review_lanes(run_state: Any) -> list[dict[str, Any]]:
    if not isinstance(run_state, dict):
        return []
    lanes = run_state.get("spawned_review_lanes", [])
    if not isinstance(lanes, list):
        return []
    return [lane for lane in lanes if isinstance(lane, dict)]


def complete_spawned_review_roles(run_state: Any) -> list[str]:
    roles: list[str] = []
    for lane in spawned_review_lanes(run_state):
        if lane.get("status") == "complete" and str(lane.get("role", "")).strip():
            roles.append(str(lane["role"]))
    return roles


def is_omics_run(artifacts: dict[str, Any]) -> bool:
    run_state = artifacts.get("run_state")
    preflight = artifacts.get("preflight")

    aliases: set[str] = set()
    modes: set[str] = set()
    if isinstance(run_state, dict):
        aliases.add(normalized_text(run_state.get("alias")))
        modes.add(normalized_text(run_state.get("mode")))
    if isinstance(preflight, dict):
        aliases.add(normalized_text(preflight.get("requested_alias")))
        modes.add(normalized_text(preflight.get("selected_mode")))

    return bool(aliases & OMICS_ALIASES) and "run" in modes


def selected_review_roles(preflight: Any) -> list[str]:
    if not isinstance(preflight, dict):
        return []
    plan = preflight.get("spawned_review_plan")
    if not isinstance(plan, dict):
        return []
    roles = plan.get("selected_roles", [])
    if not isinstance(roles, list):
        return []
    return [str(role).strip() for role in roles if str(role).strip()]


def spawned_review_budget(preflight: Any) -> int:
    if not isinstance(preflight, dict):
        return 0
    plan = preflight.get("spawned_review_plan")
    if not isinstance(plan, dict):
        return 0
    try:
        return int(plan.get("budget", 0))
    except (TypeError, ValueError):
        return 0


def spawned_review_allowed(preflight: Any) -> bool:
    if not isinstance(preflight, dict):
        return False
    plan = preflight.get("spawned_review_plan")
    return isinstance(plan, dict) and plan.get("allowed") is True


def omics_review_skip_text(artifacts: dict[str, Any]) -> str:
    parts: list[str] = []
    preflight = artifacts.get("preflight")
    run_state = artifacts.get("run_state")
    post_write = artifacts.get("post_write_validation")

    if isinstance(preflight, dict):
        plan = preflight.get("spawned_review_plan")
        if isinstance(plan, dict):
            parts.append(str(plan.get("rationale", "")))
        for skipped in preflight.get("skipped_role_outputs_with_reason", []):
            if isinstance(skipped, dict):
                parts.append(str(skipped.get("role", "")))
                parts.append(str(skipped.get("reason", "")))
        parts.append(str(preflight.get("all_role_spawn_avoidance_reason", "")))
        parts.append(str(preflight.get("post_team_audit_plan", "")))

    if isinstance(run_state, dict):
        parts.extend(str(reason) for reason in run_state.get("downgrade_reasons", []))
        for lane in run_state.get("spawned_review_lanes", []):
            if isinstance(lane, dict):
                parts.append(str(lane.get("role", "")))
                parts.append(str(lane.get("status", "")))
                parts.append(str(lane.get("rationale", "")))

    if isinstance(post_write, dict):
        parts.append(str(post_write.get("independent_review_status", "")))
        for failure in post_write.get("failure_mode_checklist", []):
            if isinstance(failure, dict):
                parts.append(str(failure.get("failure_mode", "")))
                parts.append(str(failure.get("status", "")))
                parts.append(str(failure.get("reason", "")))

    return normalized_text(" ".join(parts))


def has_omics_review_skip_exception(artifacts: dict[str, Any]) -> bool:
    text = omics_review_skip_text(artifacts)
    return any(marker in text for marker in OMICS_REVIEW_SKIP_EXCEPTION_MARKERS)


def complete_core_omics_reviewer_instances(run_state: Any) -> list[dict[str, Any]]:
    return [
        instance
        for instance in complete_independent_instances(run_state)
        if str(instance.get("agent_id", "")) in OMICS_CORE_REVIEWERS
    ]


def team_spawn_lanes(run_state: Any) -> list[dict[str, Any]]:
    if not isinstance(run_state, dict):
        return []
    lanes = run_state.get("team_spawn_lanes", [])
    if not isinstance(lanes, list):
        return []
    return [lane for lane in lanes if isinstance(lane, dict)]


def validate_team_output_artifact_shape(run_state: Any, findings: list[Finding]) -> list[dict[str, Any]]:
    if not isinstance(run_state, dict) or "team_output_artifacts" not in run_state:
        return []
    raw_outputs = run_state.get("team_output_artifacts")
    if not isinstance(raw_outputs, list):
        findings.append(
            Finding(
                "ERROR",
                "INVALID_TEAM_OUTPUT_ARTIFACTS",
                "team_output_artifacts must be an array",
            )
        )
        return []

    outputs: list[dict[str, Any]] = []
    for index, output in enumerate(raw_outputs):
        if not isinstance(output, dict):
            findings.append(
                Finding(
                    "ERROR",
                    "INVALID_TEAM_OUTPUT_ARTIFACT",
                    f"team_output_artifacts[{index}] must be an object",
                )
            )
            continue
        outputs.append(output)
    return outputs


def team_artifact_key(value: dict[str, Any]) -> tuple[str, int] | None:
    try:
        phase = int(value.get("phase"))
    except (TypeError, ValueError):
        return None
    team = str(value.get("team", "")).strip()
    if not team:
        return None
    return team, phase


def find_duplicate_values(values: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        else:
            seen.add(value)
    return sorted(duplicates)


def find_duplicate_keys(keys: list[tuple[str, int]]) -> list[tuple[str, int]]:
    seen: set[tuple[str, int]] = set()
    duplicates: set[tuple[str, int]] = set()
    for key in keys:
        if key in seen:
            duplicates.add(key)
        else:
            seen.add(key)
    return sorted(duplicates)


def validate_complete_team_output_fields(
    output: dict[str, Any],
    artifacts: dict[str, Any],
    findings: list[Finding],
) -> None:
    team = str(output.get("team", "unknown")).strip() or "unknown"
    artifact_id = str(output.get("artifact_id", "")).strip()
    path = str(output.get("path", "")).strip()
    ledger_handoff = str(output.get("ledger_handoff", "")).strip()
    checks_run = output.get("checks_run", [])

    if not artifact_id:
        findings.append(
            Finding(
                "ERROR",
                "TEAM_OUTPUT_MISSING_ARTIFACT_ID",
                f"complete team output for {team} must record an artifact_id",
            )
        )
    if not path:
        findings.append(
            Finding(
                "ERROR",
                "TEAM_OUTPUT_MISSING_PATH",
                f"complete team output for {team} must record an output path",
            )
        )
    else:
        validate_local_artifact_ref_exists(
            artifacts,
            path,
            code="TEAM_OUTPUT_PATH_MISSING",
            message=f"complete team output for {team} references missing artifact path {path}",
            path_label="run_state.json",
            findings=findings,
        )
    if not ledger_handoff:
        findings.append(
            Finding(
                "ERROR",
                "TEAM_OUTPUT_MISSING_LEDGER_HANDOFF",
                f"complete team output for {team} must record a ledger_handoff",
            )
        )
    if not isinstance(checks_run, list) or not [check for check in checks_run if str(check).strip()]:
        findings.append(
            Finding(
                "ERROR",
                "TEAM_OUTPUT_MISSING_CHECKS",
                f"complete team output for {team} must record checks_run",
            )
        )


def validate_team_dag_policy(artifacts: dict[str, Any], findings: list[Finding]) -> None:
    run_state = artifacts.get("run_state")
    if not isinstance(run_state, dict):
        return

    lanes = team_spawn_lanes(run_state)
    outputs = validate_team_output_artifact_shape(run_state, findings)
    if execution_strategy(run_state) == TEAM_LEVEL_STRATEGY and not lanes:
        findings.append(
            Finding(
                "ERROR",
                "TEAM_DAG_REQUIRES_TEAM_SPAWN_LANES",
                "team_level_selective_dag requires at least one team_spawn_lanes record",
            )
        )

    lane_keys_list = [key for lane in lanes if (key := team_artifact_key(lane)) is not None]
    lane_keys = set(lane_keys_list)
    complete_lanes = [lane for lane in lanes if lane.get("status") == "complete"]
    complete_outputs = [output for output in outputs if output.get("status") == "complete"]
    complete_lane_keys = [
        key
        for lane in complete_lanes
        if (key := team_artifact_key(lane)) is not None
    ]
    complete_output_keys = [
        key
        for output in complete_outputs
        if (key := team_artifact_key(output)) is not None
    ]
    complete_output_ids = [
        artifact_id
        for output in complete_outputs
        if (artifact_id := str(output.get("artifact_id", "")).strip())
    ]
    complete_output_by_key = {
        key: output
        for output in complete_outputs
        if (key := team_artifact_key(output)) is not None
    }
    complete_output_by_id = {
        str(output.get("artifact_id", "")).strip(): output
        for output in complete_outputs
        if str(output.get("artifact_id", "")).strip()
    }
    complete_lanes_by_team = {
        str(lane.get("team", "")).strip(): lane
        for lane in complete_lanes
        if str(lane.get("team", "")).strip()
    }

    for team, phase in find_duplicate_keys(complete_lane_keys):
        findings.append(
            Finding(
                "ERROR",
                "TEAM_SPAWN_LANE_DUPLICATE",
                f"complete team_spawn_lanes contains duplicate record for {team} phase {phase}",
            )
        )
    for team, phase in find_duplicate_keys(complete_output_keys):
        findings.append(
            Finding(
                "ERROR",
                "TEAM_OUTPUT_DUPLICATE",
                f"complete team_output_artifacts contains duplicate output for {team} phase {phase}",
            )
        )
    for artifact_id in find_duplicate_values(complete_output_ids):
        findings.append(
            Finding(
                "ERROR",
                "TEAM_OUTPUT_DUPLICATE_ARTIFACT_ID",
                f"complete team_output_artifacts contains duplicate artifact_id {artifact_id}",
            )
        )

    nested_allowed = run_state.get("nested_spawn_allowed") is True
    for lane in lanes:
        team = str(lane.get("team", "unknown")).strip() or "unknown"
        if lane.get("nested_spawn_used") is True and not nested_allowed:
            findings.append(
                Finding(
                    "ERROR",
                    "TEAM_NESTED_SPAWN_NOT_ALLOWED",
                    f"{team} records nested_spawn_used=true but nested_spawn_allowed is false",
                )
            )

    for output in complete_outputs:
        validate_complete_team_output_fields(output, artifacts, findings)
        key = team_artifact_key(output)
        if key is not None and key not in lane_keys:
            findings.append(
                Finding(
                    "ERROR",
                    "TEAM_OUTPUT_WITHOUT_LANE",
                    f"complete team output {output.get('artifact_id', 'unknown')} has no matching team_spawn_lanes record",
                )
            )

    for lane in complete_lanes:
        key = team_artifact_key(lane)
        team = str(lane.get("team", "unknown")).strip() or "unknown"
        phase = key[1] if key else 0
        if not str(lane.get("ledger_handoff", "")).strip():
            findings.append(
                Finding(
                    "ERROR",
                    "TEAM_SPAWN_LANE_MISSING_LEDGER_HANDOFF",
                    f"complete team_spawn_lanes record for {team} must include ledger_handoff",
                )
            )
        if key is None or key not in complete_output_by_key:
            findings.append(
                Finding(
                    "ERROR",
                    "TEAM_SPAWN_LANE_MISSING_OUTPUT_ARTIFACT",
                    f"team_spawn_lanes marks {team} phase {phase} complete but no matching complete team_output_artifacts entry exists",
                )
            )

        dependencies = lane.get("depends_on", [])
        if phase > 1 and not dependencies:
            findings.append(
                Finding(
                    "ERROR",
                    "TEAM_DAG_DEPENDENCY_MISSING",
                    f"{team} phase {phase} must list prior team or artifact dependencies",
                )
            )
        if phase > 1 and isinstance(dependencies, list):
            for dependency in dependencies:
                dependency_id = str(dependency).strip()
                if not dependency_id:
                    continue
                dep_lane = complete_lanes_by_team.get(dependency_id)
                dep_output = complete_output_by_id.get(dependency_id)
                dep_key = team_artifact_key(dep_lane or dep_output or {})
                if dep_key is None:
                    findings.append(
                        Finding(
                            "ERROR",
                            "TEAM_DAG_DEPENDENCY_UNRESOLVED",
                            f"{team} phase {phase} depends on {dependency_id}, but no prior complete team lane or output artifact exists",
                        )
                    )
                elif dep_key[1] >= phase:
                    findings.append(
                        Finding(
                            "ERROR",
                            "TEAM_DAG_DEPENDENCY_ORDER_INVALID",
                            f"{team} phase {phase} depends on non-prior dependency {dependency_id}",
                        )
                    )

    for output in complete_outputs:
        team = str(output.get("team", "unknown")).strip() or "unknown"
        artifact_id = str(output.get("artifact_id", "unknown")).strip() or "unknown"
        key = team_artifact_key(output)
        phase = key[1] if key else 0
        depends_on_outputs = output.get("depends_on_outputs", [])
        if not isinstance(depends_on_outputs, list):
            findings.append(
                Finding(
                    "ERROR",
                    "TEAM_OUTPUT_DEPENDENCIES_INVALID",
                    f"team output {artifact_id} depends_on_outputs must be an array",
                )
            )
            continue
        for dependency_id in depends_on_outputs:
            dependency = str(dependency_id).strip()
            if dependency and dependency not in complete_output_by_id:
                findings.append(
                    Finding(
                        "ERROR",
                        "TEAM_OUTPUT_DEPENDENCY_UNRESOLVED",
                        f"complete team output {artifact_id} for {team} depends on missing complete output {dependency}",
                    )
                )
                continue
            if dependency and dependency == artifact_id:
                findings.append(
                    Finding(
                        "ERROR",
                        "TEAM_OUTPUT_DEPENDENCY_SELF_REFERENCE",
                        f"complete team output {artifact_id} for {team} depends on itself",
                    )
                )
                continue
            dependency_output = complete_output_by_id.get(dependency)
            dependency_key = team_artifact_key(dependency_output or {})
            if dependency_key is not None and dependency_key[1] >= phase:
                findings.append(
                    Finding(
                        "ERROR",
                        "TEAM_OUTPUT_DEPENDENCY_ORDER_INVALID",
                        f"complete team output {artifact_id} for {team} depends on non-prior output {dependency}",
                    )
                )


def final_text_has_tool_use_wording(final_text: Any) -> bool:
    text = normalized_text(final_text)
    for term in TOOL_USE_TERMS:
        if re.search(r"[a-z0-9]", term):
            pattern = rf"(?<![a-z0-9_]){re.escape(term)}(?![a-z0-9_])"
            if re.search(pattern, text):
                return True
        elif term in text:
            return True
    return False


def complete_reviewer_or_team_output_used(run_state: Any) -> bool:
    if not isinstance(run_state, dict):
        return False
    for lane in spawned_review_lanes(run_state):
        if lane.get("status") == "complete":
            return True
    for lane in team_spawn_lanes(run_state):
        if lane.get("status") == "complete":
            return True
    for output in run_state.get("team_output_artifacts", []):
        if isinstance(output, dict) and output.get("status") == "complete":
            return True
    return bool(complete_independent_instances(run_state))


def structured_results_integration_reasons(artifacts: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    run_state = artifacts.get("run_state")
    claims = iter_claims(artifacts.get("claim_ledger"))
    tool_claim_ids = [claim_id(claim) for claim in claims if is_tool_backed_claim(claim)]
    if tool_claim_ids:
        reasons.append(f"tool-backed claims: {', '.join(tool_claim_ids)}")
    if isinstance(run_state, dict):
        for key in (
            "tool_use_log",
            "tool_calls_used",
            "external_tools_used",
            "tool_backed_claim_ids",
            "result_backed_claim_ids",
        ):
            if value_is_truthy(run_state.get(key)):
                reasons.append(f"run_state.{key}")
        for key in (
            "results_integration_required",
            "ranking_changed_by_external_result",
            "omics_result_changed_claim_strength",
            "external_result_changed_label",
            "reviewer_output_changed_claim",
        ):
            if value_is_truthy(run_state.get(key)):
                reasons.append(f"run_state.{key}")
        if complete_reviewer_or_team_output_used(run_state):
            reasons.append("complete reviewer/team output requires source-to-claim integration")
    return list(dict.fromkeys(reasons))


def results_rows_by_claim(results_integration: Any) -> dict[str, list[dict[str, Any]]]:
    rows_by_claim: dict[str, list[dict[str, Any]]] = {}
    if not isinstance(results_integration, dict):
        return rows_by_claim
    for row in results_integration.get("rows", []):
        if not isinstance(row, dict):
            continue
        for cid in value_as_list(row.get("claim_ids")):
            rows_by_claim.setdefault(cid, []).append(row)
    return rows_by_claim


def validate_results_integration_policy(artifacts: dict[str, Any], findings: list[Finding]) -> None:
    structured_reasons = structured_results_integration_reasons(artifacts)
    heuristic_reason = final_text_has_tool_use_wording(artifacts.get("final_text"))
    results_integration = artifacts.get("results_integration")

    if structured_reasons and results_integration is None:
        findings.append(
            Finding(
                "ERROR",
                "RESULTS_INTEGRATION_REQUIRED",
                (
                    "results_integration.json is required when tool/result/reviewer output "
                    f"affects claims, rankings, or labels: {'; '.join(structured_reasons)}"
                ),
                OPTIONAL_BUNDLE_FILES["results_integration"],
            )
        )
        return
    if heuristic_reason and results_integration is None:
        findings.append(
            Finding(
                "WARN",
                "RESULTS_INTEGRATION_HEURISTIC_MISSING",
                (
                    "final text contains tool-use wording; add results_integration.json "
                    "or record why tool output did not affect claims"
                ),
                OPTIONAL_BUNDLE_FILES["results_integration"],
            )
        )
        return
    if results_integration is None:
        return
    if not isinstance(results_integration, dict):
        return

    rows = results_integration.get("rows", [])
    if not isinstance(rows, list) or not rows:
        findings.append(
            Finding(
                "ERROR",
                "RESULTS_INTEGRATION_ROWS_REQUIRED",
                "results_integration.json must contain at least one rows[] item",
                OPTIONAL_BUNDLE_FILES["results_integration"],
            )
        )
        return
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        if not str(row.get("result_id", "")).strip():
            findings.append(
                Finding("ERROR", "RESULTS_INTEGRATION_ROW_MISSING_RESULT_ID", f"rows[{index}] missing result_id")
            )
        if not value_as_list(row.get("claim_ids")):
            findings.append(
                Finding("ERROR", "RESULTS_INTEGRATION_ROW_MISSING_CLAIM_IDS", f"rows[{index}] must map to claim_ids")
            )
        if not str(row.get("ledger_action", "")).strip():
            findings.append(
                Finding(
                    "ERROR",
                    "RESULTS_INTEGRATION_ROW_MISSING_LEDGER_ACTION",
                    f"rows[{index}] must record ledger_action",
                )
            )

    rows_by_claim = results_rows_by_claim(results_integration)
    for claim in iter_claims(artifacts.get("claim_ledger")):
        if is_tool_backed_claim(claim) and claim_id(claim) not in rows_by_claim:
            findings.append(
                Finding(
                    "ERROR",
                    "TOOL_BACKED_CLAIM_MISSING_RESULTS_ROW",
                    f"{claim_id(claim)} is tool-backed but has no results integration row",
                    OPTIONAL_BUNDLE_FILES["results_integration"],
                )
            )


def registered_tool_ids(findings: list[Finding]) -> set[str]:
    registry_path = Path(__file__).resolve().parents[1] / "references" / "tool-registry.json"
    try:
        registry = json.loads(read_text_file(registry_path))
    except FileNotFoundError:
        findings.append(Finding("ERROR", "TOOL_REGISTRY_JSON_MISSING", "tool-registry.json is missing", str(registry_path)))
        return set()
    except json.JSONDecodeError as exc:
        findings.append(Finding("ERROR", "TOOL_REGISTRY_JSON_INVALID", f"tool-registry.json is invalid: {exc}", str(registry_path)))
        return set()
    tools = registry.get("tools", []) if isinstance(registry, dict) else []
    return {str(tool.get("tool_id")).strip() for tool in tools if isinstance(tool, dict) and str(tool.get("tool_id", "")).strip()}


def iter_tool_calls(tool_call_ledger: Any) -> list[dict[str, Any]]:
    if isinstance(tool_call_ledger, dict) and isinstance(tool_call_ledger.get("calls"), list):
        return [call for call in tool_call_ledger["calls"] if isinstance(call, dict)]
    if isinstance(tool_call_ledger, list):
        return [call for call in tool_call_ledger if isinstance(call, dict)]
    return []


def successful_tool_calls_by_claim(tool_call_ledger: Any) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for call in iter_tool_calls(tool_call_ledger):
        if str(call.get("status", "")) not in TOOL_SUCCESS_STATUS:
            continue
        for cid in value_as_list(call.get("affected_claim_ids")):
            out.setdefault(cid, []).append(call)
    return out


def successful_tool_ids(tool_call_ledger: Any) -> set[str]:
    return {
        str(call.get("tool_id", "")).strip()
        for call in iter_tool_calls(tool_call_ledger)
        if str(call.get("status", "")) in TOOL_SUCCESS_STATUS and str(call.get("tool_id", "")).strip()
    }


def validate_tool_ledger_policy(
    artifacts: dict[str, Any],
    findings: list[Finding],
    require_ledger: bool = False,
) -> None:
    tool_call_ledger = artifacts.get("tool_call_ledger")
    claims = iter_claims(artifacts.get("claim_ledger"))
    tool_backed_claims = [claim for claim in claims if is_tool_backed_claim(claim)]
    final_mentions_tool = final_text_has_tool_use_wording(artifacts.get("final_text"))
    results_integration = artifacts.get("results_integration")
    ri_tool_use_log = (
        results_integration.get("tool_use_log", [])
        if isinstance(results_integration, dict) and isinstance(results_integration.get("tool_use_log", []), list)
        else []
    )
    ri_used_tools = [
        str(row.get("tool_id", "")).strip()
        for row in ri_tool_use_log
        if isinstance(row, dict) and (row.get("used") is True or row.get("status") == "used")
    ]

    if tool_call_ledger is None:
        if require_ledger and (tool_backed_claims or final_mentions_tool or ri_used_tools or structured_results_integration_reasons(artifacts)):
            findings.append(
                Finding(
                    "ERROR",
                    "TOOL_CALL_LEDGER_REQUIRED",
                    "tool_call_ledger.json is required for tool-use wording, tool-backed claims, or result integration",
                    OPTIONAL_BUNDLE_FILES["tool_call_ledger"],
                )
            )
        return
    if not isinstance(tool_call_ledger, (dict, list)):
        return

    registry_ids = registered_tool_ids(findings)
    calls = iter_tool_calls(tool_call_ledger)
    success_by_claim = successful_tool_calls_by_claim(tool_call_ledger)
    success_tool_ids = successful_tool_ids(tool_call_ledger)

    for index, call in enumerate(calls):
        tool_id = str(call.get("tool_id", "")).strip()
        status = str(call.get("status", "")).strip()
        if registry_ids and tool_id and tool_id not in registry_ids:
            findings.append(
                Finding(
                    "ERROR",
                    "TOOL_CALL_UNREGISTERED_TOOL",
                    f"tool_call_ledger calls[{index}] references unregistered tool_id {tool_id}",
                    OPTIONAL_BUNDLE_FILES["tool_call_ledger"],
                )
            )
        if status in TOOL_SUCCESS_STATUS and not str(call.get("output_ref", "")).strip():
            findings.append(
                Finding(
                    "ERROR",
                    "TOOL_CALL_SUCCESS_MISSING_OUTPUT_REF",
                    f"tool_call_ledger calls[{index}] status=success requires output_ref",
                    OPTIONAL_BUNDLE_FILES["tool_call_ledger"],
                )
            )
        if status in TOOL_NON_SUCCESS_STATUS and not str(call.get("downgrade_reason", "")).strip():
            findings.append(
                Finding(
                    "ERROR",
                    "TOOL_CALL_NON_SUCCESS_REQUIRES_DOWNGRADE_REASON",
                    f"tool_call_ledger calls[{index}] status={status} requires downgrade_reason",
                    OPTIONAL_BUNDLE_FILES["tool_call_ledger"],
                )
            )
        actual_data_class = str(call.get("actual_data_class", "")).strip()
        allowed_data_class = str(call.get("allowed_data_class", "")).strip()
        runtime_surface = str(call.get("runtime_surface", "")).strip()
        network_boundary = str(call.get("network_boundary", "")).strip()
        query_redaction_applied = call.get("query_redaction_applied")
        query_redaction = str(call.get("query_redaction", "")).strip()
        if allowed_data_class in PUBLIC_ONLY_DATA_CLASSES and actual_data_class and actual_data_class not in PUBLIC_ONLY_DATA_CLASSES:
            findings.append(
                Finding(
                    "ERROR",
                    "TOOL_CALL_DATA_CLASS_EXCEEDS_ALLOWED_SCOPE",
                    f"tool_call_ledger calls[{index}] actual_data_class={actual_data_class} exceeds allowed_data_class={allowed_data_class}",
                    OPTIONAL_BUNDLE_FILES["tool_call_ledger"],
                    "Set allowed_data_class to the approved maximum data class for this tool call, or keep the call public-only by redacting/removing private inputs.",
                )
            )
        if runtime_surface == "mcp_connector" and not str(call.get("mcp_server_name", "")).strip():
            findings.append(
                Finding(
                    "ERROR",
                    "TOOL_CALL_MCP_SERVER_NAME_REQUIRED",
                    f"tool_call_ledger calls[{index}] runtime_surface=mcp_connector requires mcp_server_name",
                    OPTIONAL_BUNDLE_FILES["tool_call_ledger"],
                    "Record the MCP server or connector name so connector-backed evidence can be audited later.",
                )
            )
        if actual_data_class in PRIVACY_SENSITIVE_DATA_CLASSES and not str(call.get("approval_ref", "")).strip():
            findings.append(
                Finding(
                    "ERROR",
                    "TOOL_CALL_PRIVACY_APPROVAL_REQUIRED",
                    f"tool_call_ledger calls[{index}] actual_data_class={actual_data_class} requires approval_ref",
                    OPTIONAL_BUNDLE_FILES["tool_call_ledger"],
                    "Record the local approval, human gate, DUA/IRB note, or explicit private-data handling approval before using sensitive inputs with any tool surface.",
                )
            )
        if (
            actual_data_class in PRIVACY_SENSITIVE_DATA_CLASSES
            and network_boundary != "local-only"
            and query_redaction_applied is not True
            and query_redaction not in {"redacted", "none-needed"}
        ):
            findings.append(
                Finding(
                    "ERROR",
                    "TOOL_CALL_QUERY_REDACTION_REQUIRED",
                    f"tool_call_ledger calls[{index}] actual_data_class={actual_data_class} requires query_redaction_applied=true or query_redaction=redacted/none-needed outside local-only use",
                    OPTIONAL_BUNDLE_FILES["tool_call_ledger"],
                    "Record query redaction status for any sensitive or human-derived data before connector, browser, or public-network tool use.",
                )
            )
        if actual_data_class in PRIVACY_SENSITIVE_DATA_CLASSES and network_boundary in {
            "public-internet",
            "authenticated-connector",
        }:
            findings.append(
                Finding(
                    "ERROR",
                    "TOOL_CALL_PRIVACY_NETWORK_BOUNDARY_BLOCK",
                    f"tool_call_ledger calls[{index}] cannot send {actual_data_class} through {call.get('network_boundary')}",
                    OPTIONAL_BUNDLE_FILES["tool_call_ledger"],
                    "Use local-only handling for sensitive data, or de-identify and record approval before any external or connector-backed use.",
                )
            )

    for claim in tool_backed_claims:
        cid = claim_id(claim)
        if cid not in success_by_claim:
            findings.append(
                Finding(
                    "ERROR",
                    "TOOL_BACKED_CLAIM_MISSING_SUCCESSFUL_CALL",
                    f"{cid} is tool-backed but has no successful tool call affecting the claim",
                    OPTIONAL_BUNDLE_FILES["tool_call_ledger"],
                )
            )
    if final_mentions_tool and not calls:
        findings.append(
            Finding(
                "ERROR",
                "FINAL_TOOL_USE_WORDING_WITHOUT_LEDGER_CALL",
                "final text contains tool-use wording but tool_call_ledger.json has no calls",
                OPTIONAL_BUNDLE_FILES["tool_call_ledger"],
            )
        )
    if final_mentions_tool and calls and not success_tool_ids:
        findings.append(
            Finding(
                "ERROR",
                "FINAL_TOOL_USE_WORDING_WITHOUT_SUCCESSFUL_CALL",
                "final text contains tool-use wording but no successful tool call is recorded",
                OPTIONAL_BUNDLE_FILES["tool_call_ledger"],
            )
        )
    for tool_id in ri_used_tools:
        if tool_id and tool_id not in success_tool_ids:
            findings.append(
                Finding(
                    "ERROR",
                    "RESULTS_INTEGRATION_TOOL_WITHOUT_SUCCESSFUL_CALL",
                    f"results_integration marks {tool_id} used but no successful tool call is recorded",
                    OPTIONAL_BUNDLE_FILES["tool_call_ledger"],
                )
            )


def scope_has_mismatch(scope_match: Any) -> bool:
    if not isinstance(scope_match, dict):
        return False
    return any(str(value) == "mismatch" for value in scope_match.values())


def validate_semantic_scope_policy(artifacts: dict[str, Any], findings: list[Finding]) -> None:
    for claim in iter_claims(artifacts.get("claim_ledger")):
        cid = claim_id(claim)
        verdict = normalized_text(claim.get("entailment_verdict", "not_checked"))
        allowed = str(claim.get("allowed_final_wording", "")).strip()
        high_confidence = is_high_confidence_claim(claim)
        if high_confidence and verdict != "supports":
            findings.append(
                Finding(
                    "ERROR",
                    "HIGH_CONFIDENCE_REQUIRES_ENTAILMENT_SUPPORT",
                    f"{cid} is high-confidence but entailment_verdict is {verdict or 'missing'}",
                    "claim_ledger.json",
                )
            )
        if verdict == "not_checked" and allowed:
            findings.append(
                Finding(
                    "ERROR",
                    "UNCHECKED_ENTAILMENT_CANNOT_HAVE_FINAL_WORDING",
                    f"{cid} has allowed_final_wording but entailment_verdict is not_checked",
                    "claim_ledger.json",
                )
            )
        if scope_has_mismatch(claim.get("scope_match")) and high_confidence:
            findings.append(
                Finding(
                    "ERROR",
                    "SCOPE_MISMATCH_BLOCKS_HIGH_CONFIDENCE",
                    f"{cid} has scope_match mismatch and cannot be high-confidence",
                    "claim_ledger.json",
                )
            )


def validate_workflow_dag_policy(artifacts: dict[str, Any], findings: list[Finding]) -> None:
    run_state = artifacts.get("run_state")
    preflight = artifacts.get("preflight")
    omics_manifest = artifacts.get("omics_run_manifest")
    workflow_dag = artifacts.get("workflow_dag")
    if not isinstance(run_state, dict):
        return
    if execution_strategy(run_state) == TEAM_LEVEL_STRATEGY and workflow_dag is None:
        findings.append(
            Finding(
                "ERROR",
                "WORKFLOW_DAG_REQUIRED_FOR_TEAM_STRATEGY",
                "team_level_selective_dag requires workflow_dag.json",
                OPTIONAL_BUNDLE_FILES["workflow_dag"],
            )
        )
        return
    if not isinstance(workflow_dag, dict):
        return
    alias = str(workflow_dag.get("alias", "")).strip()
    if alias and alias != str(run_state.get("alias", "")).strip():
        findings.append(
            Finding(
                "ERROR",
                "WORKFLOW_DAG_ALIAS_MISMATCH",
                f"workflow_dag alias {alias!r} does not match run_state alias {run_state.get('alias')!r}",
                OPTIONAL_BUNDLE_FILES["workflow_dag"],
            )
        )
    mode = str(workflow_dag.get("mode", "")).strip()
    run_state_mode = str(run_state.get("mode", "")).strip()
    if mode and run_state_mode and mode != run_state_mode:
        findings.append(
            Finding(
                "ERROR",
                "WORKFLOW_DAG_MODE_MISMATCH",
                f"workflow_dag mode {mode!r} does not match run_state mode {run_state_mode!r}",
                OPTIONAL_BUNDLE_FILES["workflow_dag"],
            )
        )
    workflow_id = str(workflow_dag.get("workflow_id", "")).strip()
    run_state_workflow_id = str(run_state.get("workflow_dag_id", "")).strip()
    if workflow_id and run_state_workflow_id and workflow_id != run_state_workflow_id:
        findings.append(
            Finding(
                "ERROR",
                "WORKFLOW_DAG_ID_MISMATCH",
                (
                    f"workflow_dag workflow_id {workflow_id!r} does not match "
                    f"run_state workflow_dag_id {run_state_workflow_id!r}"
                ),
                OPTIONAL_BUNDLE_FILES["workflow_dag"],
            )
        )
    dag_track = str(workflow_dag.get("track", "")).strip()
    declared_omics_tracks = [
        str(value).strip()
        for value in (
            run_state.get("omics_track"),
            preflight.get("requested_omics_track") if isinstance(preflight, dict) else None,
            omics_manifest.get("track") if isinstance(omics_manifest, dict) else None,
        )
        if str(value or "").strip() and str(value).strip() != "not-applicable"
    ]
    if declared_omics_tracks:
        expected_track = declared_omics_tracks[0]
        if any(track != expected_track for track in declared_omics_tracks[1:]):
            findings.append(
                Finding(
                    "ERROR",
                    "OMICS_TRACK_DECLARATION_MISMATCH",
                    f"omics track declarations disagree: {declared_omics_tracks}",
                    OPTIONAL_BUNDLE_FILES["workflow_dag"],
                    "Keep run_state.omics_track, preflight.requested_omics_track, omics_run_manifest.track, and workflow_dag.track aligned.",
                )
            )
        if not dag_track:
            findings.append(
                Finding(
                    "ERROR",
                    "WORKFLOW_DAG_TRACK_MISSING",
                    f"workflow_dag track is missing while omics track {expected_track!r} is declared",
                    OPTIONAL_BUNDLE_FILES["workflow_dag"],
                    "Write workflow_dag.track whenever run_state.omics_track, preflight.requested_omics_track, or omics_run_manifest.track declares an omics track.",
                )
            )
        elif dag_track != expected_track:
            findings.append(
                Finding(
                    "ERROR",
                    "WORKFLOW_DAG_TRACK_MISMATCH",
                    f"workflow_dag track {dag_track!r} does not match requested omics track {expected_track!r}",
                    OPTIONAL_BUNDLE_FILES["workflow_dag"],
                    "When bmat_run.py is called with --track, write the selected omics track into workflow_dag.json.",
                )
            )
    stage_ids = {
        str(stage.get("id", "")).strip()
        for stage in run_state.get("stages", [])
        if isinstance(stage, dict) and str(stage.get("id", "")).strip()
    }
    for node in workflow_dag.get("nodes", []):
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("id", "")).strip()
        if node.get("blocking") is True and node_id and node_id not in stage_ids:
            findings.append(
                Finding(
                    "ERROR",
                    "WORKFLOW_DAG_BLOCKING_NODE_MISSING_STAGE",
                    f"blocking DAG node {node_id} must appear in run_state.stages",
                    OPTIONAL_BUNDLE_FILES["workflow_dag"],
                )
            )


def validate_full_protocol(
    artifacts: dict[str, Any],
    findings: list[Finding],
    required_label: str | None = None,
) -> None:
    run_state = artifacts.get("run_state")
    preflight = artifacts.get("preflight")
    post_write = artifacts.get("post_write_validation")
    if FULL_LABEL not in declared_workflow_labels(artifacts, required_label):
        return

    required_artifacts = {
        "run_state": ("FULL_PROTOCOL_REQUIRES_RUN_STATE", "Full protocol requires run_state.json"),
        "preflight": (
            "FULL_PROTOCOL_REQUIRES_PREFLIGHT",
            f"Full protocol requires {BUNDLE_FILES['preflight']}",
        ),
        "source_corpus": ("FULL_PROTOCOL_REQUIRES_SOURCE_CORPUS", "Full protocol requires source_corpus.json"),
        "claim_ledger": ("FULL_PROTOCOL_REQUIRES_CLAIM_LEDGER", "Full protocol requires claim_ledger.json"),
        "stage_evaluation": ("FULL_PROTOCOL_REQUIRES_STAGE_EVALUATION", "Full protocol requires stage_evaluation.json"),
        "post_write_validation": (
            "FULL_PROTOCOL_REQUIRES_POST_WRITE",
            "Full protocol requires post_write_validation.json",
        ),
    }
    for artifact_key, (code, message) in required_artifacts.items():
        if artifacts.get(artifact_key) is None:
            findings.append(Finding("ERROR", code, message, BUNDLE_FILES[artifact_key]))
    if not str(artifacts.get("final_text") or "").strip():
        findings.append(
            Finding(
                "ERROR",
                "FULL_PROTOCOL_REQUIRES_FINAL_TEXT",
                "Full protocol requires non-empty final.md",
                BUNDLE_FILES["final_text"],
            )
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

    if not complete_independent_instances(run_state):
        findings.append(
            Finding(
                "ERROR",
                "FULL_PROTOCOL_REQUIRES_INDEPENDENT_INSTANCE",
                "Full protocol requires at least one complete spawned_agent_instances record with an independent execution surface",
            )
        )


def validate_compact_standard_artifacts(
    artifacts: dict[str, Any],
    findings: list[Finding],
    required_label: str | None = None,
) -> None:
    if COMPACT_LABEL not in declared_workflow_labels(artifacts, required_label):
        return

    required = {
        "preflight": f"Compact standard workflow requires {BUNDLE_FILES['preflight']} or --preflight",
        "source_corpus": "Compact standard workflow requires source_corpus.json or --source-corpus",
        "claim_ledger": "Compact standard workflow requires claim_ledger.json or --claim-ledger",
        "post_write_validation": "Compact standard workflow requires post_write_validation.json or --post-write-validation",
    }
    for artifact_key, message in required.items():
        if artifacts.get(artifact_key) is None:
            findings.append(
                Finding(
                    "ERROR",
                    "COMPACT_WORKFLOW_REQUIRES_ARTIFACT",
                    message,
                    BUNDLE_FILES[artifact_key],
                )
            )


def validate_spawned_instance_policy(artifacts: dict[str, Any], findings: list[Finding]) -> None:
    run_state = artifacts.get("run_state")
    if isinstance(run_state, dict) and "spawned_review_lanes" in run_state:
        raw_lanes = run_state.get("spawned_review_lanes")
        if not isinstance(raw_lanes, list):
            findings.append(
                Finding(
                    "ERROR",
                    "INVALID_SPAWNED_REVIEW_LANES",
                    "spawned_review_lanes must be an array",
                )
            )
        else:
            for index, lane in enumerate(raw_lanes):
                if not isinstance(lane, dict):
                    findings.append(
                        Finding(
                            "ERROR",
                            "INVALID_SPAWNED_REVIEW_LANE",
                            f"spawned_review_lanes[{index}] must be an object",
                        )
                    )
                    continue
                if lane.get("status") == "complete":
                    role = str(lane.get("role", "")).strip()
                    if not role:
                        findings.append(
                            Finding(
                                "ERROR",
                                "SPAWNED_LANE_MISSING_ROLE",
                                f"complete spawned_review_lanes[{index}] must include role",
                            )
                        )
                    if not str(lane.get("ledger_handoff", "")).strip():
                        findings.append(
                            Finding(
                                "ERROR",
                                "SPAWNED_LANE_MISSING_LEDGER_HANDOFF",
                                f"complete spawned_review_lanes record for {role or index} must include ledger_handoff",
                            )
                        )

    if isinstance(run_state, dict) and "spawned_agent_instances" in run_state:
        raw_instances = run_state.get("spawned_agent_instances")
        if not isinstance(raw_instances, list):
            findings.append(
                Finding(
                    "ERROR",
                    "INVALID_SPAWNED_AGENT_INSTANCES",
                    "spawned_agent_instances must be an array",
                )
            )
            return
        for index, instance in enumerate(raw_instances):
            if not isinstance(instance, dict):
                findings.append(
                    Finding(
                        "ERROR",
                        "INVALID_SPAWNED_AGENT_INSTANCE",
                        f"spawned_agent_instances[{index}] must be an object",
                    )
                )

    instances = spawned_agent_instances(run_state)
    complete_roles = complete_spawned_review_roles(run_state)
    if not instances and not complete_roles:
        return

    instance_ids = [
        instance_id
        for instance in instances
        if (instance_id := str(instance.get("instance_id", "")).strip())
    ]
    for instance_id in find_duplicate_values(instance_ids):
        findings.append(
            Finding(
                "ERROR",
                "SPAWNED_INSTANCE_DUPLICATE_ID",
                f"spawned_agent_instances contains duplicate instance_id {instance_id}",
            )
        )

    known_agent_ids = registry_agent_ids(findings)
    complete_independent_instance_agents: set[str] = set()
    for instance in instances:
        agent_id = str(instance.get("agent_id", "")).strip()
        status = str(instance.get("status", ""))
        execution_surface = str(instance.get("execution_surface", "")).strip()
        input_scope = str(instance.get("input_scope", "")).strip()
        output_artifact = str(instance.get("output_artifact", "")).strip()
        ledger_handoff = str(instance.get("ledger_handoff", "")).strip()
        checks_run = instance.get("checks_run")
        if known_agent_ids and agent_id not in known_agent_ids:
            findings.append(
                Finding(
                    "ERROR",
                    "SPAWNED_INSTANCE_UNKNOWN_AGENT",
                    f"spawned instance references unknown agent_id {agent_id}",
                )
            )
        if status == "complete":
            if execution_surface in INDEPENDENT_INSTANCE_SURFACES:
                complete_independent_instance_agents.add(agent_id)
            else:
                findings.append(
                    Finding(
                        "ERROR",
                        "SPAWNED_INSTANCE_INVALID_EXECUTION_SURFACE",
                        f"complete spawned instance for {agent_id} must use an independent execution_surface",
                    )
                )
            if not input_scope:
                findings.append(
                    Finding(
                        "ERROR",
                        "SPAWNED_INSTANCE_MISSING_INPUT_SCOPE",
                        f"complete spawned instance for {agent_id} must record an input_scope",
                    )
                )
            if not output_artifact:
                findings.append(
                    Finding(
                        "ERROR",
                        "SPAWNED_INSTANCE_MISSING_OUTPUT_ARTIFACT",
                        f"complete spawned instance for {agent_id} must record an output_artifact",
                    )
                )
            else:
                validate_local_artifact_ref_exists(
                    artifacts,
                    output_artifact,
                    code="SPAWNED_INSTANCE_OUTPUT_ARTIFACT_MISSING",
                    message=(
                        f"complete spawned instance for {agent_id} references missing "
                        f"output_artifact {output_artifact}"
                    ),
                    path_label="run_state.json",
                    findings=findings,
                )
            if not isinstance(checks_run, list) or not checks_run:
                findings.append(
                    Finding(
                        "ERROR",
                        "SPAWNED_INSTANCE_MISSING_CHECKS_RUN",
                        f"complete spawned instance for {agent_id} must record non-empty checks_run",
                    )
                )
            elif any(not isinstance(check, str) or not check.strip() for check in checks_run):
                findings.append(
                    Finding(
                        "ERROR",
                        "SPAWNED_INSTANCE_INVALID_CHECKS_RUN",
                        f"complete spawned instance for {agent_id} has invalid checks_run entries",
                    )
                )
            if not ledger_handoff:
                findings.append(
                    Finding(
                        "ERROR",
                        "SPAWNED_INSTANCE_MISSING_LEDGER_HANDOFF",
                        f"complete spawned instance for {agent_id} must record a ledger_handoff",
                    )
                )

    for role in find_duplicate_values(complete_roles):
        findings.append(
            Finding(
                "ERROR",
                "SPAWNED_LANE_DUPLICATE_ROLE",
                f"spawned_review_lanes contains duplicate complete role {role}",
            )
        )
    for role in complete_roles:
        if role not in complete_independent_instance_agents:
            findings.append(
                Finding(
                    "ERROR",
                    "SPAWNED_LANE_MISSING_INSTANCE",
                    f"spawned_review_lanes marks {role} complete but no matching complete independent spawned_agent_instances entry exists",
                )
            )


def validate_omics_reviewer_spawn_policy(artifacts: dict[str, Any], findings: list[Finding]) -> None:
    if not is_omics_run(artifacts):
        return

    run_state = artifacts.get("run_state")
    preflight = artifacts.get("preflight")
    if not isinstance(preflight, dict):
        return
    if isinstance(run_state, dict) and execution_strategy(run_state) == "blocked":
        return

    roles = selected_review_roles(preflight)
    core_roles = sorted(set(roles) & OMICS_CORE_REVIEWERS)
    has_review_budget = spawned_review_allowed(preflight) and spawned_review_budget(preflight) >= 1

    if not has_review_budget or not roles:
        if has_omics_review_skip_exception(artifacts):
            findings.append(
                Finding(
                    "WARN",
                    "OMICS_RUN_REVIEWER_SPAWN_SKIPPED_WITH_DOWNGRADE",
                    "omics run skipped spawned core reviewer with explicit runtime/privacy/user-compact downgrade rationale",
                    BUNDLE_FILES["preflight"],
                )
            )
            return
        findings.append(
            Finding(
                "ERROR",
                "OMICS_RUN_REVIEWER_SPAWN_REQUIRED",
                "omics run requires spawned_review_plan.allowed=true, budget>=1, and a selected core reviewer unless an explicit runtime/privacy/user-compact downgrade reason is recorded",
                BUNDLE_FILES["preflight"],
            )
        )
        return

    if not core_roles:
        findings.append(
            Finding(
                "ERROR",
                "OMICS_RUN_CORE_REVIEWER_REQUIRED",
                "omics run spawned_review_plan must include at least one core reviewer: omics-code-reviewer, omics-provenance-validator, or biostats-repro-auditor",
                BUNDLE_FILES["preflight"],
            )
        )
        return

    if isinstance(run_state, dict) and not complete_core_omics_reviewer_instances(run_state):
        if has_omics_review_skip_exception(artifacts):
            findings.append(
                Finding(
                    "WARN",
                    "OMICS_RUN_CORE_REVIEWER_NOT_COMPLETED_WITH_DOWNGRADE",
                    "omics run planned a core reviewer but no complete core spawned_agent_instances record was found; downgrade rationale is recorded",
                    "run_state.json",
                )
            )
            return
        findings.append(
            Finding(
                "ERROR",
                "OMICS_RUN_REVIEWER_PLAN_NOT_EXECUTED",
                "omics run planned a core spawned reviewer but lacks a complete core spawned_agent_instances record",
                "run_state.json",
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


def validate_policies(
    artifacts: dict[str, Any],
    findings: list[Finding],
    required_label: str | None = None,
    check_tool_ledger: bool = False,
) -> None:
    validate_required_label(artifacts, findings, required_label)
    validate_lead_decision_policy(artifacts, findings, required_label)
    validate_compact_standard_artifacts(artifacts, findings, required_label)
    validate_full_protocol(artifacts, findings, required_label)
    validate_spawned_instance_policy(artifacts, findings)
    validate_omics_reviewer_spawn_policy(artifacts, findings)
    validate_omics_manifest_policy(artifacts, findings)
    validate_team_dag_policy(artifacts, findings)
    validate_workflow_dag_policy(artifacts, findings)
    validate_results_integration_policy(artifacts, findings)
    validate_tool_ledger_policy(artifacts, findings, require_ledger=check_tool_ledger)
    validate_s3_policy(artifacts, findings)
    validate_source_policy(artifacts, findings)
    validate_semantic_scope_policy(artifacts, findings)
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
        hint = f" fix_hint={finding.fix_hint}" if finding.fix_hint else ""
        print(f"{finding.level} {finding.code}: {finding.message}{suffix}{hint}")


def main() -> int:
    args = parse_args()
    if not args.bundle and not any(getattr(args, key, None) for key in BUNDLE_FILES):
        print("ERROR NO_INPUT: provide --bundle or at least one artifact path", file=sys.stderr)
        return 2

    findings: list[Finding] = []
    artifacts = load_artifacts(input_paths(args), findings)
    validate_schemas(artifacts, findings)
    validate_required_artifact_fields(artifacts, findings)
    validate_policies(artifacts, findings, args.require_label, args.check_tool_ledger)
    emit(findings, args.json)
    return 1 if any(finding.level == "ERROR" for finding in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
