from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest


SKILL_ROOT = Path(__file__).resolve().parents[1]
MIGRATOR = SKILL_ROOT / "scripts" / "bmat_migrate_bundle.py"
CONTRACTS = SKILL_ROOT / "contracts"
SCHEMAS = {
    "run_state.json": "workflow-run.schema.json",
    "source_corpus.json": "source-corpus.schema.json",
    "source_verification.json": "source-verification.schema.json",
    "claim_ledger.json": "claim-ledger.schema.json",
    "claim_support_matrix.json": "claim-support-matrix.schema.json",
    "review_artifact_manifest.json": "review-artifact-manifest.schema.json",
    "tool_call_ledger.json": "tool-call-ledger.schema.json",
}


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def tree_snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def run_migration(source: Path, out: Path | None = None) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(MIGRATOR), "--source", str(source), "--json"]
    if out is not None:
        command.extend(["--out", str(out)])
    return subprocess.run(command, text=True, capture_output=True, check=False)


def make_legacy_bundle(root: Path) -> Path:
    root.mkdir()
    write_json(
        root / "run_state.json",
        {
            "run_id": "legacy-run-001",
            "alias": "evidence-audit-team",
            "mode": "audit",
            "plugin_version": "1.1.1",
            "execution_strategy": "inline_first_selective_review",
            "nested_spawn_allowed": False,
            "spawned_review_lanes": [],
            "team_spawn_lanes": [],
            "spawned_agent_instances": [],
            "stages": [{"id": "S3", "required": True, "status": "pass", "evidence": "legacy pass"}],
            "final_label": "Full protocol followed",
            "downgrade_reasons": [],
        },
    )
    write_json(
        root / "source_corpus.json",
        {
            "corpus_id": "legacy-corpus-001",
            "created_at": "2026-01-02",
            "query_or_origin": "legacy fixture query",
            "sources": [
                {
                    "source_id": "S-FIXTURE",
                    "source_type": "local-file",
                    "identifier": "fixture-record",
                    "version_or_retrieval_date": "unknown",
                    "inclusion_status": "included",
                    "claim_use": "legacy support",
                    "checked_by": "legacy checker",
                    "limitations": "offline fixture",
                    "evidence_spans": [
                        {
                            "span_id": "SPAN-OLD",
                            "location": "paragraph 1",
                            "evidence_span_ref": "paragraph 1",
                        }
                    ],
                }
            ],
        },
    )
    write_json(
        root / "source_verification.json",
        {
            "schema_version": "1.0",
            "verification_id": "legacy-verification-001",
            "plugin_version": "1.1.1",
            "workflow_run_id": "legacy-run-001",
            "checked_at": "2026-01-02T00:00:00Z",
            "rows": [
                {
                    "source_id": "S-FIXTURE",
                    "source_type": "local-file",
                    "identifier": "fixture-record",
                    "identifier_status": "verified",
                    "metadata_match": "pass",
                    "verification_mode": "fixture",
                    "release_eligible": True,
                    "fixture_only": True,
                    "retrieval_surface": "offline-fixture",
                    "claim_ids_checked": ["CL-001"],
                    "verification_limitations": "fixture only",
                },
                {
                    "source_id": "S-LEGACY-LIVE",
                    "source_type": "DOI",
                    "identifier": "10.0000/legacy",
                    "canonical_identifier": "10.0000/legacy",
                    "identifier_status": "verified",
                    "metadata_match": "pass",
                    "verification_mode": "live-tool",
                    "release_eligible": True,
                    "fixture_only": False,
                    "retrieval_surface": "legacy-api",
                    "claim_ids_checked": ["CL-001"],
                    "verification_limitations": "no v2 receipt",
                    "integrity_status": "unknown",
                    "version_status": "unknown",
                },
            ],
        },
    )
    write_json(
        root / "claim_ledger.json",
        {
            "claims": [
                {
                    "claim_id": "CL-001",
                    "atomic_claim": "A legacy claim.",
                    "source_backed": True,
                    "claim_strength": "high-confidence",
                    "audit_status": "pass",
                    "entailment_verdict": "supports",
                    "scope_match": {
                        "species": "match",
                        "cell_type": "match",
                        "assay": "match",
                        "endpoint": "match",
                    },
                }
            ]
        },
    )
    write_json(
        root / "claim_support_matrix.json",
        {
            "schema_version": "1.0",
            "support_matrix_id": "legacy-support-001",
            "plugin_version": "1.1.1",
            "workflow_run_id": "legacy-run-001",
            "rows": [
                {
                    "claim_id": "CL-001",
                    "source_id": "S-FIXTURE",
                    "evidence_span_ref": "SPAN-OLD",
                    "support_verdict": "supports",
                    "scope_match": {
                        "species": "match",
                        "cell_type": "match",
                        "assay": "match",
                        "endpoint": "match",
                    },
                    "overclaim_risk": "low",
                    "allowed_in_final": True,
                    "allowed_final_wording": "A legacy claim.",
                    "review_surface": "legacy-reviewer",
                    "independent_review_required": True,
                    "limitations": "no receipt",
                }
            ],
        },
    )
    write_json(
        root / "review_artifact_manifest.json",
        {
            "schema_version": "1.0",
            "workflow_run_id": "legacy-run-001",
            "plugin_version": "1.1.1",
            "review_instances": [
                {
                    "instance_id": "OLD-REVIEW-001",
                    "agent_id": "citation-verifier",
                    "execution_surface": "tool_backed_validator",
                    "output_artifact": "review.md",
                    "output_sha256": "0" * 64,
                }
            ],
        },
    )
    write_json(
        root / "tool_call_ledger.json",
        {
            "schema_version": "1.0",
            "ledger_id": "legacy-tools-001",
            "plugin_version": "1.1.1",
            "workflow_run_id": "legacy-run-001",
            "calls": [
                {
                    "call_id": "OLD-CALL-001",
                    "tool_id": "legacy-api",
                    "status": "success",
                    "inputs_digest": "legacy query",
                    "output_ref": "legacy-output.json",
                    "affected_claim_ids": ["CL-001"],
                    "provenance": {"source_id": "S-LEGACY-LIVE"},
                }
            ],
        },
    )
    return root


def assert_schema_valid(bundle: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    format_checker = jsonschema.FormatChecker()
    for artifact, schema_name in SCHEMAS.items():
        payload = json.loads((bundle / artifact).read_text(encoding="utf-8"))
        schema = json.loads((CONTRACTS / schema_name).read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema, format_checker=format_checker).validate(payload)


def walk_values(value: Any):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key, item
            yield from walk_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk_values(item)


def test_migration_is_schema_valid_conservative_and_does_not_change_source(tmp_path: Path) -> None:
    source = make_legacy_bundle(tmp_path / "legacy")
    destination = tmp_path / "migrated"
    before = tree_snapshot(source)

    result = run_migration(source, destination)

    assert result.returncode == 0, result.stdout + result.stderr
    assert tree_snapshot(source) == before
    assert_schema_valid(destination)

    verification = json.loads((destination / "source_verification.json").read_text(encoding="utf-8"))
    fixture, formerly_live = verification["rows"]
    assert fixture["verification_mode"] == "fixture"
    assert fixture["fixture_only"] is True
    assert fixture["release_eligible"] is False
    assert fixture["identifier_status"] == "not-checked"
    assert fixture["metadata_match"] == "not-checked"
    assert fixture["canonical_identifier"] == "unknown"
    assert formerly_live["verification_mode"] == "not-checked"
    assert formerly_live["fixture_only"] is False
    assert formerly_live["release_eligible"] is False
    assert formerly_live["identifier_status"] == "not-checked"
    assert formerly_live["integrity_status"] == "unknown"
    assert formerly_live["version_status"] == "unknown"

    corpus = json.loads((destination / "source_corpus.json").read_text(encoding="utf-8"))
    assert corpus["sources"][0]["inclusion_status"] == "not-checked"
    assert "evidence_spans" not in corpus["sources"][0]

    support = json.loads((destination / "claim_support_matrix.json").read_text(encoding="utf-8"))
    support_row = support["rows"][0]
    assert support_row["support_verdict"] == "not-checked"
    assert support_row["allowed_in_final"] is False
    assert support_row["release_eligible"] is False
    assert set(support_row["scope_match"]) == {
        "species",
        "cell_type",
        "assay",
        "endpoint",
        "population_or_model",
        "intervention_or_exposure",
        "biological_context",
    }
    assert support_row["scope_match"]["population_or_model"] == "not-assessed"

    reviews = json.loads((destination / "review_artifact_manifest.json").read_text(encoding="utf-8"))
    assert reviews["review_instances"] == []
    calls = json.loads((destination / "tool_call_ledger.json").read_text(encoding="utf-8"))
    assert calls["calls"][0]["status"] == "unavailable"
    assert "output_ref" not in calls["calls"][0]

    for artifact in SCHEMAS:
        payload = json.loads((destination / artifact).read_text(encoding="utf-8"))
        for key, value in walk_values(payload):
            if key == "release_eligible":
                assert value is False
            if key == "identifier_status":
                assert value != "verified"

    report = json.loads((destination / "migration_report.json").read_text(encoding="utf-8"))
    reverify = json.loads((destination / "reverification_required.json").read_text(encoding="utf-8"))
    assert report["source_unchanged"] is True
    assert report["release_eligible"] is False
    assert report["reverification_required_count"] == len(reverify["items"])
    assert report["reverification_required_count"] >= 7
    assert reverify["release_eligible"] is False


def test_default_output_is_sibling_and_existing_destination_is_never_overwritten(tmp_path: Path) -> None:
    source = make_legacy_bundle(tmp_path / "legacy")

    first = run_migration(source)

    destination = tmp_path / "legacy-v2"
    assert first.returncode == 0, first.stdout + first.stderr
    assert destination.is_dir()
    sentinel = destination / "sentinel.txt"
    sentinel.write_text("do not overwrite\n", encoding="utf-8")
    before = tree_snapshot(destination)

    second = run_migration(source)

    assert second.returncode == 2
    assert "refusing to overwrite" in second.stderr
    assert tree_snapshot(destination) == before


def test_nested_output_and_malformed_json_fail_without_publishing_output(tmp_path: Path) -> None:
    source = make_legacy_bundle(tmp_path / "legacy")
    nested = source / "migrated"

    nested_result = run_migration(source, nested)

    assert nested_result.returncode == 2
    assert "must not be inside" in nested_result.stderr
    assert not nested.exists()

    malformed_source = tmp_path / "malformed"
    malformed_source.mkdir()
    (malformed_source / "source_verification.json").write_text("{not-json", encoding="utf-8")
    malformed_out = tmp_path / "malformed-v2"

    malformed_result = run_migration(malformed_source, malformed_out)

    assert malformed_result.returncode == 2
    assert "cannot parse JSON artifact" in malformed_result.stderr
    assert not malformed_out.exists()
    assert (malformed_source / "source_verification.json").read_text(encoding="utf-8") == "{not-json"


def test_v2_artifact_round_trip_is_byte_stable(tmp_path: Path) -> None:
    source = tmp_path / "already-v2"
    source.mkdir()
    payload = {
        "schema_version": "2.0",
        "verification_id": "sv-v2",
        "plugin_version": "1.2.0",
        "workflow_run_id": "run-v2",
        "checked_at": "2026-07-10T00:00:00Z",
        "rows": [
            {
                "source_id": "S-001",
                "source_type": "DOI",
                "identifier": "10.0000/example",
                "canonical_identifier": "unknown",
                "identifier_status": "not-checked",
                "metadata_match": "not-checked",
                "verification_mode": "not-checked",
                "release_eligible": False,
                "fixture_only": False,
                "checked_at": "2026-07-10T00:00:00Z",
                "retrieval_surface": "not-checked",
                "claim_ids_checked": [],
                "verification_limitations": "not checked",
                "integrity_status": "unknown",
                "version_status": "unknown",
            }
        ],
    }
    write_json(source / "source_verification.json", payload)
    original = (source / "source_verification.json").read_bytes()
    destination = tmp_path / "round-trip"

    result = run_migration(source, destination)

    assert result.returncode == 0, result.stdout + result.stderr
    assert (source / "source_verification.json").read_bytes() == original
    assert (destination / "source_verification.json").read_bytes() == original
    report = json.loads((destination / "migration_report.json").read_text(encoding="utf-8"))
    assert report["migrated_files"] == []
    assert report["unchanged_files"] == ["source_verification.json"]
    assert report["reverification_required_count"] == 0


def test_unknown_v1_artifact_is_preserved_and_flagged_for_manual_migration(tmp_path: Path) -> None:
    source = tmp_path / "legacy"
    source.mkdir()
    write_json(source / "custom_extension.json", {"schema_version": "1.0", "status": "verified"})
    original = (source / "custom_extension.json").read_bytes()
    destination = tmp_path / "migrated"

    result = run_migration(source, destination)

    assert result.returncode == 0, result.stdout + result.stderr
    assert (destination / "custom_extension.json").read_bytes() == original
    report = json.loads((destination / "migration_report.json").read_text(encoding="utf-8"))
    reverify = json.loads((destination / "reverification_required.json").read_text(encoding="utf-8"))
    assert report["legacy_unconverted_files"] == ["custom_extension.json"]
    assert "LEGACY_ARTIFACT_CONVERTER_UNAVAILABLE" in {
        warning["code"] for warning in report["warnings"]
    }
    assert reverify["items"][0]["reason_code"] == "MANUAL_V2_MIGRATION_REQUIRED"


def test_source_symlink_is_rejected_when_platform_allows_symlink_creation(tmp_path: Path) -> None:
    source = tmp_path / "legacy"
    source.mkdir()
    outside = tmp_path / "outside.json"
    write_json(outside, {"schema_version": "1.0"})
    link = source / "linked.json"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlink creation is not available for this Windows account")
    destination = tmp_path / "migrated"

    result = run_migration(source, destination)

    assert result.returncode == 2
    assert "symbolic link or reparse point" in result.stderr
    assert not destination.exists()
