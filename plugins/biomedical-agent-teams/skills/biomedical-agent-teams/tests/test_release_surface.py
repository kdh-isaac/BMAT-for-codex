from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")


SKILL_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = SKILL_ROOT.parents[1]
BOM_SIGNATURES = (
    (b"\xff\xfe\x00\x00", "UTF-32 LE BOM"),
    (b"\x00\x00\xfe\xff", "UTF-32 BE BOM"),
    (b"\xef\xbb\xbf", "UTF-8 BOM"),
    (b"\xff\xfe", "UTF-16 LE BOM"),
    (b"\xfe\xff", "UTF-16 BE BOM"),
)
BOM_CHECK_EXTENSIONS = {
    ".json",
    ".jsonl",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
BOM_CHECK_FILENAMES = {"VERSION"}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def release_text_paths() -> list[Path]:
    paths = [
        PLUGIN_ROOT / ".codex-plugin" / "plugin.json",
        PLUGIN_ROOT / ".codex-plugin" / "biomedical-agent-teams.md",
    ]
    for path in sorted(SKILL_ROOT.rglob("*")):
        if not path.is_file():
            continue
        if any(part in {"__pycache__", ".pytest_cache"} for part in path.parts):
            continue
        if "agents" in path.relative_to(SKILL_ROOT).parts:
            continue
        if path.name in BOM_CHECK_FILENAMES or path.suffix.lower() in BOM_CHECK_EXTENSIONS:
            paths.append(path)
    return paths


def test_release_surface_files_exist() -> None:
    required_paths = [
        SKILL_ROOT / "references" / "tool-registry.md",
        SKILL_ROOT / "contracts" / "lead-decision.schema.json",
        SKILL_ROOT / "contracts" / "omics-run-manifest.schema.json",
        SKILL_ROOT / "contracts" / "results-integration.schema.json",
        SKILL_ROOT / "contracts" / "source-verification.schema.json",
        SKILL_ROOT / "contracts" / "claim-support-matrix.schema.json",
        SKILL_ROOT / "contracts" / "omics-metadata-check.schema.json",
        SKILL_ROOT / "contracts" / "experiment-design.schema.json",
        SKILL_ROOT / "contracts" / "review-artifact-manifest.schema.json",
        SKILL_ROOT / "templates" / "lead-decision-template.md",
        SKILL_ROOT / "templates" / "results-integration-template.md",
        SKILL_ROOT / "templates" / "research-overview-template.md",
        SKILL_ROOT / "templates" / "source-verification-template.md",
        SKILL_ROOT / "templates" / "claim-support-matrix-template.md",
        SKILL_ROOT / "templates" / "omics-metadata-check-template.md",
        SKILL_ROOT / "templates" / "experiment-design-template.md",
        SKILL_ROOT / "templates" / "review-artifact-manifest-template.md",
        SKILL_ROOT / "evals" / "public_omics_benchmark_cases.jsonl",
        SKILL_ROOT / "scripts" / "bmat_source_check.py",
        SKILL_ROOT / "scripts" / "bmat_omics_metadata_check.py",
        SKILL_ROOT / "scripts" / "bmat_experiment_design_check.py",
        SKILL_ROOT / "scripts" / "bmat_public_omics_benchmark_smoke.py",
        PLUGIN_ROOT / ".codex-plugin" / "biomedical-agent-teams.md",
    ]

    for path in required_paths:
        assert path.exists(), path


def test_release_surface_text_files_are_bom_free() -> None:
    for path in release_text_paths():
        with path.open("rb") as handle:
            prefix = handle.read(4)
        for signature, label in BOM_SIGNATURES:
            assert not prefix.startswith(signature), f"{label} present in {path}"


def test_version_aligned_in_primary_metadata() -> None:
    version = (SKILL_ROOT / "VERSION").read_text(encoding="utf-8").strip()

    assert version == "1.1.0"
    assert read_json(SKILL_ROOT / "manifest.json")["version"] == version
    assert read_json(SKILL_ROOT / "manifest.json")["adapter_version"] == version
    assert read_json(SKILL_ROOT / "source-manifest.json")["version"] == version
    assert read_json(SKILL_ROOT / "agent-registry.json")["version"] == version
    assert read_json(PLUGIN_ROOT / ".codex-plugin" / "plugin.json")["version"] == version


def test_manifest_lists_release_resources() -> None:
    source_manifest = read_json(SKILL_ROOT / "source-manifest.json")

    assert "tool-registry" in source_manifest["references"]
    assert "claim-ledger.schema" in source_manifest["contracts"]
    assert "lead-decision.schema" in source_manifest["contracts"]
    assert "omics-run-manifest.schema" in source_manifest["contracts"]
    assert "results-integration.schema" in source_manifest["contracts"]
    assert "source-verification.schema" in source_manifest["contracts"]
    assert "claim-support-matrix.schema" in source_manifest["contracts"]
    assert "omics-metadata-check.schema" in source_manifest["contracts"]
    assert "experiment-design.schema" in source_manifest["contracts"]
    assert "review-artifact-manifest.schema" in source_manifest["contracts"]
    assert "tool-call-ledger.schema" in source_manifest["contracts"]
    assert "workflow-dag.schema" in source_manifest["contracts"]
    assert "lead-decision-template" in source_manifest["templates"]
    assert "results-integration-template" in source_manifest["templates"]
    assert "research-overview-template" in source_manifest["templates"]
    assert "research-workbench-index-template" in source_manifest["templates"]
    assert "source-verification-template" in source_manifest["templates"]
    assert "claim-support-matrix-template" in source_manifest["templates"]
    assert "omics-metadata-check-template" in source_manifest["templates"]
    assert "experiment-design-template" in source_manifest["templates"]
    assert "review-artifact-manifest-template" in source_manifest["templates"]
    assert "bmat_tool_ledger_check" in source_manifest["scripts"]
    assert "bmat_codex_adapter" in source_manifest["scripts"]
    assert "bmat_public_omics_benchmark_smoke" in source_manifest["scripts"]
    assert "bmat_source_check" in source_manifest["scripts"]
    assert "bmat_omics_metadata_check" in source_manifest["scripts"]
    assert "bmat_experiment_design_check" in source_manifest["scripts"]
    assert "bmat_run" in source_manifest["scripts"]
    assert "evidence-audit-team" in source_manifest["workflow_dags"]
    assert "cell-therapy" in source_manifest["domain_packs"]
    assert "immuno-oncology" in source_manifest["domain_packs"]
    release_note_keys = [key for key in source_manifest if key.startswith("new_in_v")]
    assert release_note_keys == ["new_in_v1_0_0", "new_in_v1_1_0"]
    assert (
        "runtime-capability-preflight-canonical-artifact-name"
        in source_manifest["new_in_v1_0_0"]
    )
    assert (
        "legacy-preflight-json-backward-compatible-alias-with-warning"
        in source_manifest["new_in_v1_0_0"]
    )
    assert (
        "golden-eval-hard-gates-for-tournament-loop-ranking-and-codex-runtime"
        in source_manifest["new_in_v1_0_0"]
    )
    assert (
        "global-expected-block-action-gate-for-golden-eval"
        in source_manifest["new_in_v1_0_0"]
    )
    assert (
        "tool-call-ledger-schema-and-checker"
        in source_manifest["new_in_v1_0_0"]
    )
    assert (
        "workflow-dag-schema-and-six-command-dags"
        in source_manifest["new_in_v1_0_0"]
    )
    assert "lead-decision-contract-and-validator-gates" in source_manifest["new_in_v1_1_0"]
    assert "omics-run-manifest-v2-for-tenx-and-bulk-rnaseq" in source_manifest["new_in_v1_1_0"]
    assert "public-omics-real-world-benchmark-smoke-harness" in source_manifest["new_in_v1_1_0"]
    assert "tenx-and-bulk-golden-task-expansion" in source_manifest["new_in_v1_1_0"]
    assert (
        "release-mode-source-verification-and-claim-support-gates"
        in source_manifest["new_in_v1_1_0"]
    )
    assert "omics-track-ambiguity-blocks-run-mode" in source_manifest["new_in_v1_1_0"]
    assert "omics-metadata-check-contract-and-local-checker" in source_manifest["new_in_v1_1_0"]
    assert (
        "review-artifact-manifest-hash-bound-independent-review"
        in source_manifest["new_in_v1_1_0"]
    )
    assert "experiment-design-contract-and-local-checker" in source_manifest["new_in_v1_1_0"]


def test_immuno_oncology_domain_pack_has_marker_and_boundary_assets() -> None:
    pack_root = SKILL_ROOT / "domain-packs" / "immuno-oncology"
    marker_panels = read_json(pack_root / "marker-panels.json")
    boundaries = (pack_root / "interpretation-boundaries.md").read_text(encoding="utf-8")

    assert marker_panels["domain_pack"] == "immuno-oncology"
    panel_ids = {panel["panel_id"] for panel in marker_panels["marker_panels"]}
    assert {
        "io-t-cell-state-core",
        "io-myeloid-suppression-core",
        "io-tumor-immune-interface",
        "cart-product-context",
    } <= panel_ids

    for token in (
        "TME and Bulk-Proxy Boundaries",
        "Single-Cell and Spatial Boundaries",
        "CAR-T and Adoptive-Cell Therapy Boundaries",
        "tumor-biopsy TME association alone",
    ):
        assert token in boundaries


def test_tool_registry_blocks_unlogged_tool_claims() -> None:
    text = (SKILL_ROOT / "references" / "tool-registry.md").read_text(encoding="utf-8")

    assert "Do not report a tool as used unless" in text
    assert "source-corpus row" in text
    assert "results integration row" in text
    assert "selected specialist lanes in parallel" in text
    assert "dependency graph" in text


def test_tool_call_ledger_schema_has_execution_governance_fields() -> None:
    schema = read_json(SKILL_ROOT / "contracts" / "tool-call-ledger.schema.json")
    call_properties = schema["properties"]["calls"]["items"]["properties"]

    for field in (
        "allowed_data_class",
        "actual_data_class",
        "query_redaction",
        "query_redaction_applied",
        "approval_ref",
        "runtime_surface",
        "mcp_server_name",
        "artifact_sha256",
        "retention_policy",
        "network_boundary",
        "pii_risk",
    ):
        assert field in call_properties


def test_omics_manifest_schema_has_p2_track_specific_artifacts() -> None:
    schema = read_json(SKILL_ROOT / "contracts" / "omics-run-manifest.schema.json")
    assay_properties = schema["properties"]["assay_metadata"]["properties"]
    artifact_properties = schema["properties"]["generated_artifacts"]["properties"]

    for field in (
        "feature_reference_ref",
        "antibody_panel_ref",
        "vdj_reference",
        "gex_linkage_key",
        "atac_reference",
        "feature_linkage_ref",
    ):
        assert field in assay_properties

    for field in (
        "feature_reference_csv",
        "feature_barcode_matrix",
        "vdj_contig_annotations",
        "vdj_clonotypes",
        "fragments_tsv_gz",
        "atac_peak_matrix",
        "arc_summary_html",
    ):
        assert field in artifact_properties


def test_results_integration_schema_classifies_result_status() -> None:
    schema = read_json(SKILL_ROOT / "contracts" / "results-integration.schema.json")
    row_schema = schema["properties"]["rows"]["items"]["properties"]
    status_enum = set(row_schema["status"]["enum"])
    ledger_action_enum = set(row_schema["ledger_action"]["enum"])

    assert {"support", "contradiction", "null", "ambiguous", "qc-failed"} <= status_enum
    assert {"add", "update", "downgrade", "exclude", "no-change", "block"} <= ledger_action_enum
    assert schema["properties"]["tool_use_log"]["items"]["allOf"][0]["then"]["properties"]["result_rows"]["minItems"] == 1


def valid_results_integration_payload() -> dict:
    return {
        "schema_version": "1.0",
        "integration_id": "RI-TEST-001",
        "plugin_version": "1.1.0",
        "source_corpus_lock": "locked",
        "tool_use_log": [
            {
                "tool_id": "spawned-reviewer-lane",
                "status": "used",
                "used": True,
                "source_corpus_rows": ["SC-001"],
                "result_rows": ["RI-ROW-001"],
                "downgrade_reason": "",
            }
        ],
        "rows": [
            {
                "result_id": "RI-ROW-001",
                "result_type": "literature",
                "source_ref": "SC-001",
                "claim_ids": ["CL-001"],
                "status": "support",
                "evidence_direction": "supports",
                "confidence": "moderate",
                "interpretation": "Public literature supports a bounded claim.",
                "limitations": "Synthetic regression fixture.",
                "ledger_action": "update",
            }
        ],
        "final_claim_policy": "ledger-only",
        "human_review_status": "not-needed",
    }


def test_results_integration_schema_requires_used_status_consistency() -> None:
    schema = read_json(SKILL_ROOT / "contracts" / "results-integration.schema.json")
    payload = valid_results_integration_payload()

    jsonschema.validate(payload, schema)

    payload["tool_use_log"][0]["status"] = "skipped"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload, schema)


def test_results_integration_schema_requires_downgrade_reason_for_unused_tool() -> None:
    schema = read_json(SKILL_ROOT / "contracts" / "results-integration.schema.json")
    payload = valid_results_integration_payload()
    payload["tool_use_log"][0] = {
        "tool_id": "pubmed-ncbi-entrez",
        "status": "unavailable",
        "used": False,
        "source_corpus_rows": [],
        "result_rows": [],
        "downgrade_reason": "",
    }

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload, schema)


def test_source_corpus_requires_evidence_spans_for_included_sources() -> None:
    schema = read_json(SKILL_ROOT / "contracts" / "source-corpus.schema.json")
    payload = {
        "corpus_id": "corpus-test",
        "created_at": "2026-07-06",
        "sources": [
            {
                "source_id": "S-001",
                "source_type": "PMID",
                "identifier": "12345678",
                "version_or_retrieval_date": "retrieved 2026-07-06",
                "inclusion_status": "included",
                "claim_use": "supports CL-001",
                "checked_by": "citation-verifier",
                "limitations": "synthetic regression fixture",
            }
        ],
    }

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload, schema)

    payload["sources"][0]["evidence_spans"] = [
        {
            "span_id": "S-001-span-001",
            "location": "abstract:sent1",
            "scope_note": "synthetic evidence span with bounded scope",
        }
    ]
    jsonschema.validate(payload, schema)


def test_research_overview_template_is_ledger_bound() -> None:
    text = (SKILL_ROOT / "templates" / "research-overview-template.md").read_text(encoding="utf-8")

    for token in ("central claim ledger", "source corpus", "results integration", "meta-review"):
        assert token in text
    assert "Do not introduce new claims" in text
    assert "workflow label" in text


def test_command_recipes_name_v1_1_release_gate_artifacts() -> None:
    required_tokens = (
        "## 1.1 Release-Gate Artifacts",
        "lead_decision.json",
        "workflow_dag.json",
        "results_integration.json",
        "tool_call_ledger.json",
        "evidence_spans[]",
    )

    for command in sorted((SKILL_ROOT / "commands").glob("*.md")):
        text = command.read_text(encoding="utf-8")
        assert "## 1.0 Release-Gate Artifacts" not in text
        for token in required_tokens:
            assert token in text, f"{command.name} missing {token}"


def workflow_declared_outputs(alias: str) -> set[str]:
    workflow = read_json(SKILL_ROOT / "workflows" / f"{alias}.json")
    outputs: set[str] = set()
    for node in workflow["nodes"]:
        outputs.update(node["outputs"])
    return outputs


def test_workflow_dags_declare_release_gate_outputs() -> None:
    common_outputs = {
        "runtime_capability_preflight",
        "workflow_run",
        "source_corpus",
        "source_verification",
        "claim_ledger",
        "claim_support_matrix",
        "results_integration",
        "post_write_validation",
        "review_artifact_manifest",
        "final_text",
    }

    for workflow_path in sorted((SKILL_ROOT / "workflows").glob("*.json")):
        alias = workflow_path.stem
        outputs = workflow_declared_outputs(alias)
        missing = common_outputs - outputs
        assert not missing, f"{alias} missing release outputs: {sorted(missing)}"

    omics_outputs = workflow_declared_outputs("omics-analysis-team")
    assert {"omics_run_manifest", "omics_metadata_check"} <= omics_outputs

    design_outputs = workflow_declared_outputs("experiment-design-team")
    assert "experiment_design" in design_outputs


def test_current_user_facing_surfaces_have_no_legacy_version_residue() -> None:
    checked_paths = [
        PLUGIN_ROOT / "README.md",
        PLUGIN_ROOT / "README.quickstart.md",
        PLUGIN_ROOT / ".codex-plugin" / "plugin.json",
        PLUGIN_ROOT / ".codex-plugin" / "biomedical-agent-teams.md",
        SKILL_ROOT / "README.md",
        SKILL_ROOT / "SKILL.md",
    ]
    checked_paths.extend(sorted((SKILL_ROOT / "agents").glob("*.md")))
    checked_paths.extend(sorted((SKILL_ROOT / "commands").glob("*.md")))
    checked_paths.extend(sorted((SKILL_ROOT / "codex-agents").glob("*.toml")))
    checked_paths.extend(sorted((SKILL_ROOT / "loops").glob("*.md")))
    checked_paths.extend(sorted((SKILL_ROOT / "references").glob("*.md")))
    checked_paths.extend(sorted((SKILL_ROOT / "templates").glob("*.md")))

    forbidden_patterns = {
        "old_semver": re.compile(r"(?<![\w.])(0\.(?:3|4|8|9)\.\d+|1\.0\.0)(?![\w.])"),
        "old_release_gate": re.compile(r"1\.0 Release-Gate|README 35|35 agent"),
        "old_current_version": re.compile(r"Current (?:plugin )?version: `1\.0"),
        "claude_runtime_surface": re.compile(
            r"Claude Code|Claude-only|claude-code|\.claude|claude plugin",
            re.IGNORECASE,
        ),
        "standalone_legacy_preflight": re.compile(r"(?<!runtime_capability_)preflight\.json"),
    }
    allowed_matches = {
        (
            SKILL_ROOT / "templates" / "rollback-resume-template.md",
            "standalone_legacy_preflight",
        ),
    }

    for path in checked_paths:
        text = path.read_text(encoding="utf-8")
        for label, pattern in forbidden_patterns.items():
            match = pattern.search(text)
            if (path, label) in allowed_matches:
                continue
            assert match is None, f"{path} contains {label}: {match.group(0)!r}"


def test_provenance_architect_names_v1_traceability_artifacts() -> None:
    text = (SKILL_ROOT / "agents" / "provenance-traceability-architect.md").read_text(encoding="utf-8")

    for token in (
        "evidence_spans[]",
        "evidence_edges[]",
        "results_integration.json",
        "tool_call_ledger.json",
        "workflow_dag.json",
    ):
        assert token in text


def test_user_facing_command_examples_are_cross_platform() -> None:
    docs = [
        PLUGIN_ROOT / "README.md",
        PLUGIN_ROOT / "README.quickstart.md",
        SKILL_ROOT / "SKILL.md",
        SKILL_ROOT / "README.md",
        SKILL_ROOT / "evals" / "README.md",
    ]

    for path in docs:
        text = path.read_text(encoding="utf-8")
        assert "/tmp/" not in text, f"{path} contains a Unix-only /tmp example"
        assert "python3 " not in text, f"{path} should use cross-platform `python` examples"
        assert " \\\n" not in text, f"{path} contains shell-specific line continuations"
