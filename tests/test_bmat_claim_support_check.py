from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "plugins" / "biomedical-agent-teams" / "skills" / "biomedical-agent-teams"
CONTRACTS = SKILL_ROOT / "contracts"
SOURCE_CHECK = SKILL_ROOT / "scripts" / "bmat_source_check.py"
CLAIM_CHECK = SKILL_ROOT / "scripts" / "bmat_claim_support_check.py"
NOW = "2026-07-10T00:00:00Z"
VERSION = "1.2.0"
RUN_ID = "run-v2-test"


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_text(value: str) -> str:
    return digest_bytes(value.encode("utf-8"))


def write_json(path: Path, payload: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(payload, indent=2).encode("utf-8")
    path.write_bytes(content)
    return digest_bytes(content)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def schema(name: str) -> dict:
    return read_json(CONTRACTS / name)


def build_bundle(tmp_path: Path) -> tuple[Path, dict[str, dict]]:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    excerpt = "A bounded public evidence excerpt supports the synthetic claim."
    snapshot_sha = write_json(bundle / "evidence" / "source.json", {"excerpt": excerpt})
    tool_output_sha = write_json(
        bundle / "receipts" / "pubmed.json",
        {"pmid": "12345678", "title": "Synthetic source"},
    )
    review_sha = write_json(bundle / "reviews" / "review.json", {"verdict": "supports"})
    review_input_sha = write_json(bundle / "reviews" / "input.json", {"claim_id": "CL-001"})
    prompt_bytes = b"Review the bounded claim against the recorded evidence."
    (bundle / "reviews" / "prompt.txt").write_bytes(prompt_bytes)
    prompt_sha = digest_bytes(prompt_bytes)
    runtime_sha = write_json(bundle / "reviews" / "runtime.json", {"session": "session-2"})

    payloads = {
        "run_state.json": {
            "run_id": RUN_ID,
            "plugin_version": VERSION,
        },
        "source_corpus.json": {
            "schema_version": "2.0",
            "corpus_id": "corpus-v2-test",
            "plugin_version": VERSION,
            "workflow_run_id": RUN_ID,
            "created_at": NOW,
            "query_or_origin": "public identifier fixture for deterministic validation",
            "sources": [
                {
                    "source_id": "S-001",
                    "source_type": "PMID",
                    "identifier": "12345678",
                    "title_or_name": "Synthetic source",
                    "version_or_retrieval_date": NOW,
                    "retrieved_at": NOW,
                    "query_or_origin": "recorded public metadata",
                    "inclusion_status": "included",
                    "claim_use": "supports CL-001 at bounded wording",
                    "checked_by": "pubmed-ncbi-entrez",
                    "limitations": "synthetic deterministic receipt",
                    "evidence_spans": [
                        {
                            "span_id": "S-001-span-001",
                            "source_id": "S-001",
                            "source_snapshot_ref": "evidence/source.json",
                            "source_snapshot_sha256": snapshot_sha,
                            "locator": "abstract:sentence-1",
                            "section": "abstract",
                            "paragraph_or_table": "paragraph-1",
                            "sentence_or_cell": "sentence-1",
                            "evidence_text_sha256": digest_text(excerpt),
                            "short_evidence_excerpt": excerpt,
                            "retrieved_at": NOW,
                            "extraction_actor": "citation-verifier",
                            "limitations": "synthetic short excerpt",
                        }
                    ],
                }
            ],
        },
        "claim_ledger.json": {
            "schema_version": "2.0",
            "claim_ledger_id": "claims-v2-test",
            "plugin_version": VERSION,
            "workflow_run_id": RUN_ID,
            "created_at": NOW,
            "claims": [
                {
                    "claim_id": "CL-001",
                    "atomic_claim": "The source supports a bounded synthetic claim.",
                    "claim_profile": "high_confidence",
                    "claim_strength": "high-confidence",
                    "source_ids": ["S-001"],
                    "evidence_items": [{"source_id": "S-001"}],
                    "allowed_final_wording": "The source supports a bounded synthetic claim.",
                }
            ],
        },
        "tool_call_ledger.json": {
            "schema_version": "2.0",
            "ledger_id": "tools-v2-test",
            "plugin_version": VERSION,
            "workflow_run_id": RUN_ID,
            "created_at": NOW,
            "calls": [
                {
                    "call_id": "TC-001",
                    "tool_id": "pubmed-ncbi-entrez",
                    "status": "success",
                    "inputs_digest": digest_text("12345678"),
                    "query_identifiers": ["12345678"],
                    "affected_source_ids": ["S-001"],
                    "affected_claim_ids": ["CL-001"],
                    "result_ids": ["PMID:12345678"],
                    "output_ref": "receipts/pubmed.json",
                    "output_sha256": tool_output_sha,
                    "started_at": NOW,
                    "completed_at": "2026-07-10T00:00:01Z",
                    "query_redaction": "none-needed",
                    "query_redaction_applied": False,
                    "allowed_data_class": "public-only",
                    "actual_data_class": "public-only",
                    "approval_ref": "not-applicable",
                    "runtime_surface": "codex_tool",
                    "retention_policy": "bundle-artifact",
                    "network_boundary": "public-internet",
                    "pii_risk": "none",
                }
            ],
        },
        "source_verification.json": {
            "schema_version": "2.0",
            "verification_id": "source-verification-v2-test",
            "plugin_version": VERSION,
            "workflow_run_id": RUN_ID,
            "checked_at": NOW,
            "rows": [
                {
                    "source_id": "S-001",
                    "source_type": "PMID",
                    "identifier": "12345678",
                    "canonical_identifier": "PMID:12345678",
                    "identifier_status": "verified",
                    "metadata_match": "pass",
                    "verification_mode": "live-tool",
                    "release_eligible": True,
                    "fixture_only": False,
                    "checked_at": NOW,
                    "retrieved_at": NOW,
                    "retrieval_surface": "NCBI PubMed E-utilities recorded response",
                    "claim_ids_checked": ["CL-001"],
                    "verification_limitations": "recorded metadata validates identity, not scientific truth",
                    "integrity_status": "current",
                    "version_status": "version-of-record",
                    "canonical_title": "Synthetic source",
                    "resolver": "NCBI PubMed E-utilities",
                    "tool_id": "pubmed-ncbi-entrez",
                    "tool_call_id": "TC-001",
                    "output_ref": "receipts/pubmed.json",
                    "output_sha256": tool_output_sha,
                }
            ],
        },
        "review_artifact_manifest.json": {
            "schema_version": "2.0",
            "review_manifest_id": "reviews-v2-test",
            "plugin_version": VERSION,
            "workflow_run_id": RUN_ID,
            "created_at": NOW,
            "review_instances": [
                {
                    "instance_id": "REV-001",
                    "agent_id": "reviewer-1",
                    "actor_type": "model",
                    "provider": "test-provider",
                    "model": "independent-test-model",
                    "model_version": "1",
                    "authoring_provider": "test-provider",
                    "authoring_model": "authoring-test-model",
                    "authoring_model_version": "1",
                    "authoring_execution_session_id": "session-1",
                    "authoring_identity_available": True,
                    "execution_surface": "spawned_subagent",
                    "execution_session_id": "session-2",
                    "spawn_event_id": "spawn-1",
                    "input_scope": "CL-001 and S-001 recorded evidence",
                    "input_artifact_refs": ["reviews/input.json"],
                    "input_artifact_sha256": {"reviews/input.json": review_input_sha},
                    "prompt_template_ref": "reviews/prompt.txt",
                    "prompt_template_sha256": prompt_sha,
                    "output_artifact": "reviews/review.json",
                    "output_sha256": review_sha,
                    "checks_run": ["claim-source entailment", "seven-axis scope"],
                    "changed_claim_ids": [],
                    "ledger_handoff": "CL-001 reviewed without wording changes",
                    "results_integration_rows": ["RI-001"],
                    "independence_class": "separate-model",
                    "independent_review_eligible": True,
                    "fixture_only": False,
                    "authoring_context_shared": False,
                    "started_at": NOW,
                    "completed_at": "2026-07-10T00:00:02Z",
                    "runtime_receipt_ref": "reviews/runtime.json",
                    "runtime_receipt_sha256": runtime_sha,
                    "limitations": "synthetic deterministic review receipt",
                }
            ],
        },
        "claim_support_matrix.json": {
            "schema_version": "2.0",
            "support_matrix_id": "support-v2-test",
            "plugin_version": VERSION,
            "workflow_run_id": RUN_ID,
            "created_at": NOW,
            "rows": [
                {
                    "claim_id": "CL-001",
                    "source_id": "S-001",
                    "evidence_span_ref": "S-001-span-001",
                    "support_verdict": "supports",
                    "scope_match": {
                        "species": "match",
                        "cell_type": "not-applicable",
                        "assay": "match",
                        "endpoint": "match",
                        "population_or_model": "match",
                        "intervention_or_exposure": "match",
                        "biological_context": "match",
                    },
                    "overclaim_risk": "low",
                    "allowed_in_final": True,
                    "allowed_final_wording": "The source supports a bounded synthetic claim.",
                    "review_surface": "separate-model",
                    "review_actor_id": "reviewer-1",
                    "review_instance_id": "REV-001",
                    "review_artifact_ref": "reviews/review.json",
                    "review_artifact_sha256": review_sha,
                    "independent_review_required": True,
                    "release_eligible": True,
                    "limitations": "synthetic deterministic support receipt",
                }
            ],
        },
    }
    for name, payload in payloads.items():
        write_json(bundle / name, payload)
    return bundle, payloads


def run_source_check(bundle: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SOURCE_CHECK),
            "--source-corpus",
            str(bundle / "source_corpus.json"),
            "--claim-ledger",
            str(bundle / "claim_ledger.json"),
            "--tool-call-ledger",
            str(bundle / "tool_call_ledger.json"),
            "--bundle-root",
            str(bundle),
            "--out",
            str(bundle / "source_verification_checked.json"),
            *extra,
        ],
        text=True,
        capture_output=True,
        check=False,
    )


def run_claim_check(bundle: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLAIM_CHECK), "--bundle", str(bundle), "--release", "--json"],
        text=True,
        capture_output=True,
        check=False,
    )


def codes(result: subprocess.CompletedProcess[str]) -> set[str]:
    payload = json.loads(result.stdout)
    return {finding["code"] for finding in payload["findings"]}


@pytest.mark.parametrize(
    "schema_name",
    [
        "source-verification.schema.json",
        "tool-call-ledger.schema.json",
        "claim-support-matrix.schema.json",
        "source-corpus.schema.json",
    ],
)
def test_v2_contracts_are_valid_draft_2020_12_schemas(schema_name: str) -> None:
    jsonschema.Draft202012Validator.check_schema(schema(schema_name))


def test_offline_fixture_is_explicitly_non_release_and_never_auto_links_call(tmp_path: Path) -> None:
    bundle, _ = build_bundle(tmp_path)

    result = run_source_check(bundle, "--offline-fixture", "--json")

    assert result.returncode == 0, result.stdout + result.stderr
    verification = read_json(bundle / "source_verification_checked.json")
    row = verification["rows"][0]
    assert verification["schema_version"] == "2.0"
    assert row["identifier_status"] == "not-checked"
    assert row["metadata_match"] == "not-checked"
    assert row["verification_mode"] == "fixture"
    assert row["fixture_only"] is True
    assert row["release_eligible"] is False
    assert "tool_call_id" not in row


def test_explicit_live_tool_receipt_passes_exact_cross_artifact_checks(tmp_path: Path) -> None:
    bundle, _ = build_bundle(tmp_path)

    result = run_source_check(
        bundle,
        "--verification-input",
        str(bundle / "source_verification.json"),
        "--json",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert codes(result) == set()


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        ("missing-call", "SOURCE_VERIFICATION_TOOL_CALL_MISSING"),
        ("failed-call", "SOURCE_VERIFICATION_TOOL_CALL_NOT_SUCCESSFUL"),
        ("tool-id", "SOURCE_VERIFICATION_TOOL_ID_MISMATCH"),
        ("source-id", "SOURCE_VERIFICATION_SOURCE_NOT_AFFECTED_BY_CALL"),
        ("query-id", "SOURCE_VERIFICATION_QUERY_IDENTIFIER_MISMATCH"),
        ("output-ref", "SOURCE_VERIFICATION_OUTPUT_REF_MISMATCH"),
        ("output-sha", "SOURCE_VERIFICATION_OUTPUT_SHA256_MISMATCH"),
    ],
)
def test_live_tool_receipt_rejects_unrelated_or_drifted_call(
    tmp_path: Path, mutation: str, expected_code: str
) -> None:
    bundle, payloads = build_bundle(tmp_path)
    ledger = copy.deepcopy(payloads["tool_call_ledger.json"])
    verification = copy.deepcopy(payloads["source_verification.json"])
    call = ledger["calls"][0]
    if mutation == "missing-call":
        call["call_id"] = "TC-OTHER"
    elif mutation == "failed-call":
        call["status"] = "failed"
        call["downgrade_reason"] = "synthetic failure"
    elif mutation == "tool-id":
        call["tool_id"] = "other-resolver"
    elif mutation == "source-id":
        call["affected_source_ids"] = ["S-OTHER"]
    elif mutation == "query-id":
        call["query_identifiers"] = ["99999999"]
    elif mutation == "output-ref":
        call["output_ref"] = "receipts/other.json"
    elif mutation == "output-sha":
        call["output_sha256"] = "0" * 64
    write_json(bundle / "tool_call_ledger.json", ledger)
    write_json(bundle / "source_verification.json", verification)

    result = run_source_check(
        bundle,
        "--verification-input",
        str(bundle / "source_verification.json"),
        "--json",
    )

    assert result.returncode == 1
    assert expected_code in codes(result), result.stdout + result.stderr


def test_fixture_input_cannot_claim_verified_or_release_eligible(tmp_path: Path) -> None:
    bundle, payloads = build_bundle(tmp_path)
    verification = copy.deepcopy(payloads["source_verification.json"])
    row = verification["rows"][0]
    row.update(
        {
            "verification_mode": "fixture",
            "fixture_only": True,
            "release_eligible": True,
            "retrieval_surface": "offline-fixture",
            "verification_limitations": "fixture only",
        }
    )
    write_json(bundle / "source_verification.json", verification)

    result = run_source_check(
        bundle,
        "--verification-input",
        str(bundle / "source_verification.json"),
        "--json",
    )

    assert result.returncode == 1
    assert {
        "FIXTURE_VERIFICATION_CANNOT_BE_VERIFIED",
        "FIXTURE_METADATA_CANNOT_PASS",
        "FIXTURE_NOT_RELEASE_ELIGIBLE",
    } <= codes(result)


def test_local_file_receipt_recomputes_snapshot_hash_and_size(tmp_path: Path) -> None:
    bundle, payloads = build_bundle(tmp_path)
    corpus = copy.deepcopy(payloads["source_corpus.json"])
    source = corpus["sources"][0]
    source["source_type"] = "local-file"
    source["identifier"] = "evidence/source.json"
    source["checked_by"] = "local-file"
    snapshot_path = bundle / "evidence" / "source.json"
    snapshot_sha = digest_bytes(snapshot_path.read_bytes())
    verification = copy.deepcopy(payloads["source_verification.json"])
    row = verification["rows"][0]
    for field in ("resolver", "tool_id", "tool_call_id", "output_ref", "output_sha256"):
        row.pop(field, None)
    row.update(
        {
            "source_type": "local-file",
            "identifier": "evidence/source.json",
            "canonical_identifier": f"sha256:{snapshot_sha}",
            "verification_mode": "local-file",
            "retrieval_surface": "local bundle snapshot",
            "integrity_status": "not-applicable",
            "version_status": "local-snapshot",
            "local_snapshot_ref": "evidence/source.json",
            "local_snapshot_sha256": snapshot_sha,
            "local_snapshot_size_bytes": snapshot_path.stat().st_size,
        }
    )
    write_json(bundle / "source_corpus.json", corpus)
    write_json(bundle / "source_verification.json", verification)

    valid = run_source_check(
        bundle,
        "--verification-input",
        str(bundle / "source_verification.json"),
        "--json",
    )
    assert valid.returncode == 0, valid.stdout + valid.stderr

    snapshot_path.write_bytes(snapshot_path.read_bytes() + b"\nchanged")
    stale = run_source_check(
        bundle,
        "--verification-input",
        str(bundle / "source_verification.json"),
        "--json",
    )
    assert stale.returncode == 1
    assert "SOURCE_VERIFICATION_LOCAL_SNAPSHOT_HASH_MISMATCH" in codes(stale)


def test_valid_claim_support_bundle_passes(tmp_path: Path) -> None:
    bundle, _ = build_bundle(tmp_path)

    result = run_claim_check(bundle)

    assert result.returncode == 0, result.stdout + result.stderr
    assert codes(result) == set()


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        ("scope-partial", "HIGH_CONFIDENCE_REQUIRES_STRICT_SUPPORT"),
        ("weak-support", "WEAK_SUPPORT_CANNOT_BE_HIGH_CONFIDENCE"),
        ("wrong-claim-source", "CLAIM_SUPPORT_SOURCE_NOT_LINKED_TO_CLAIM"),
        ("unresolved-span", "EVIDENCE_SPAN_REF_UNRESOLVED"),
        ("wording", "CLAIM_SUPPORT_WORDING_CONFLICT"),
        ("review-hash", "CLAIM_SUPPORT_REVIEW_ARTIFACT_HASH_MISMATCH"),
        ("same-model-review", "INDEPENDENT_REVIEW_RECEIPT_INELIGIBLE"),
        ("stale-run", "STALE_WORKFLOW_RUN_ID"),
        ("retracted", "RETRACTED_SOURCE_CANNOT_SUPPORT_FINAL_CLAIM"),
        ("snapshot-hash", "EVIDENCE_SNAPSHOT_HASH_MISMATCH"),
        ("duplicate-support", "DUPLICATE_SUPPORT_ROW"),
        ("duplicate-verification", "SOURCE_VERIFICATION_DUPLICATE_SOURCE_ROW"),
        ("span-owner", "EVIDENCE_SPAN_SOURCE_OWNERSHIP_MISMATCH"),
    ],
)
def test_claim_support_checker_rejects_release_provenance_drift(
    tmp_path: Path, mutation: str, expected_code: str
) -> None:
    bundle, payloads = build_bundle(tmp_path)
    matrix = copy.deepcopy(payloads["claim_support_matrix.json"])
    claims = copy.deepcopy(payloads["claim_ledger.json"])
    verification = copy.deepcopy(payloads["source_verification.json"])
    corpus = copy.deepcopy(payloads["source_corpus.json"])
    review = copy.deepcopy(payloads["review_artifact_manifest.json"])
    if mutation == "scope-partial":
        matrix["rows"][0]["scope_match"]["assay"] = "partial"
    elif mutation == "weak-support":
        matrix["rows"][0]["support_verdict"] = "weakly-supports"
    elif mutation == "wrong-claim-source":
        claims["claims"][0]["source_ids"] = ["S-OTHER"]
        claims["claims"][0]["evidence_items"] = [{"source_id": "S-OTHER"}]
    elif mutation == "unresolved-span":
        matrix["rows"][0]["evidence_span_ref"] = "S-001-missing"
    elif mutation == "wording":
        matrix["rows"][0]["allowed_final_wording"] = "Conflicting wording."
    elif mutation == "review-hash":
        matrix["rows"][0]["review_artifact_sha256"] = "0" * 64
    elif mutation == "same-model-review":
        review["review_instances"][0]["model"] = review["review_instances"][0]["authoring_model"]
        review["review_instances"][0]["model_version"] = review["review_instances"][0]["authoring_model_version"]
    elif mutation == "stale-run":
        matrix["workflow_run_id"] = "run-stale"
    elif mutation == "retracted":
        verification["rows"][0]["integrity_status"] = "retracted"
        verification["rows"][0]["release_eligible"] = False
    elif mutation == "snapshot-hash":
        corpus["sources"][0]["evidence_spans"][0]["source_snapshot_sha256"] = "0" * 64
    elif mutation == "duplicate-support":
        matrix["rows"].append(copy.deepcopy(matrix["rows"][0]))
    elif mutation == "duplicate-verification":
        verification["rows"].append(copy.deepcopy(verification["rows"][0]))
    elif mutation == "span-owner":
        corpus["sources"][0]["evidence_spans"][0]["source_id"] = "S-OTHER"
    write_json(bundle / "claim_support_matrix.json", matrix)
    write_json(bundle / "claim_ledger.json", claims)
    write_json(bundle / "source_verification.json", verification)
    write_json(bundle / "source_corpus.json", corpus)
    write_json(bundle / "review_artifact_manifest.json", review)

    result = run_claim_check(bundle)

    assert result.returncode == 1
    assert expected_code in codes(result), result.stdout + result.stderr


def test_claim_support_schema_rejects_incomplete_seven_axis_scope(tmp_path: Path) -> None:
    _, payloads = build_bundle(tmp_path)
    matrix = copy.deepcopy(payloads["claim_support_matrix.json"])
    del matrix["rows"][0]["scope_match"]["biological_context"]

    validator = jsonschema.Draft202012Validator(
        schema("claim-support-matrix.schema.json"),
        format_checker=jsonschema.FormatChecker(),
    )

    assert list(validator.iter_errors(matrix))


def test_source_corpus_schema_rejects_path_traversal_snapshot(tmp_path: Path) -> None:
    _, payloads = build_bundle(tmp_path)
    corpus = copy.deepcopy(payloads["source_corpus.json"])
    corpus["sources"][0]["evidence_spans"][0]["source_snapshot_ref"] = "../secret.txt"

    validator = jsonschema.Draft202012Validator(
        schema("source-corpus.schema.json"),
        format_checker=jsonschema.FormatChecker(),
    )

    assert list(validator.iter_errors(corpus))
