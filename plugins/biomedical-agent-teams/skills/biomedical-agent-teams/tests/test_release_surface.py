from __future__ import annotations

import json
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
    paths = [PLUGIN_ROOT / ".codex-plugin" / "plugin.json"]
    for path in sorted(SKILL_ROOT.rglob("*")):
        if not path.is_file():
            continue
        if any(part in {"__pycache__", ".pytest_cache"} for part in path.parts):
            continue
        if path.name in BOM_CHECK_FILENAMES or path.suffix.lower() in BOM_CHECK_EXTENSIONS:
            paths.append(path)
    return paths


def test_release_surface_files_exist() -> None:
    required_paths = [
        SKILL_ROOT / "references" / "tool-registry.md",
        SKILL_ROOT / "contracts" / "results-integration.schema.json",
        SKILL_ROOT / "templates" / "results-integration-template.md",
        SKILL_ROOT / "templates" / "research-overview-template.md",
    ]

    for path in required_paths:
        assert path.exists(), path


def test_release_surface_text_files_are_bom_free() -> None:
    for path in release_text_paths():
        prefix = path.read_bytes()[:4]
        for signature, label in BOM_SIGNATURES:
            assert not prefix.startswith(signature), f"{label} present in {path}"


def test_version_aligned_in_primary_metadata() -> None:
    version = (SKILL_ROOT / "VERSION").read_text(encoding="utf-8").strip()

    assert version == "0.8.7"
    assert read_json(SKILL_ROOT / "manifest.json")["version"] == version
    assert read_json(SKILL_ROOT / "manifest.json")["adapter_version"] == version
    assert read_json(SKILL_ROOT / "source-manifest.json")["version"] == version
    assert read_json(SKILL_ROOT / "agent-registry.json")["version"] == version
    assert read_json(PLUGIN_ROOT / ".codex-plugin" / "plugin.json")["version"] == version


def test_manifest_lists_release_resources() -> None:
    source_manifest = read_json(SKILL_ROOT / "source-manifest.json")

    assert "tool-registry" in source_manifest["references"]
    assert "results-integration.schema" in source_manifest["contracts"]
    assert "results-integration-template" in source_manifest["templates"]
    assert "research-overview-template" in source_manifest["templates"]
    assert "utf8-bom-tolerant-command-and-agent-markdown-loading" in source_manifest["new_in_v0_8_1"]
    assert (
        "utf8-bom-tolerant-validator-loop-golden-eval-elo-and-init-bundle-loading"
        in source_manifest["new_in_v0_8_2"]
    )
    assert "elo-cli-zero-override-preservation" in source_manifest["new_in_v0_8_3"]
    assert (
        "utf8-bom-tolerant-codex-agent-toml-template-test-loader"
        in source_manifest["new_in_v0_8_4"]
    )
    assert (
        "spawned-agent-instance-complete-evidence-policy"
        in source_manifest["new_in_v0_8_5"]
    )
    assert (
        "posix-stable-docs-inventory-path-output"
        in source_manifest["new_in_v0_8_6"]
    )
    assert (
        "omics-run-init-bundle-scaffold-downgrade-policy"
        in source_manifest["new_in_v0_8_7"]
    )
    assert (
        "bom-free-release-surface-package-gate"
        in source_manifest["new_in_v0_8_7"]
    )


def test_tool_registry_blocks_unlogged_tool_claims() -> None:
    text = (SKILL_ROOT / "references" / "tool-registry.md").read_text(encoding="utf-8")

    assert "Do not report a tool as used unless" in text
    assert "source-corpus row" in text
    assert "results integration row" in text
    assert "selected specialist lanes in parallel" in text
    assert "dependency graph" in text


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
        "schema_version": "0.8",
        "integration_id": "RI-TEST-001",
        "plugin_version": "0.8.7",
        "source_corpus_lock": "locked",
        "tool_use_log": [
            {
                "tool_id": "pubmed-ncbi-entrez",
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


def test_research_overview_template_is_ledger_bound() -> None:
    text = (SKILL_ROOT / "templates" / "research-overview-template.md").read_text(encoding="utf-8")

    for token in ("central claim ledger", "source corpus", "results integration", "meta-review"):
        assert token in text
    assert "Do not introduce new claims" in text
    assert "workflow label" in text
