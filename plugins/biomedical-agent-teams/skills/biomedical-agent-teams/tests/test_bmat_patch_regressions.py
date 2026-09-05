"""Regression cases for the 1.2.1 structural review findings."""
from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

import bmat_run
import bmat_validate
import bmat_workflow_policy
from bmat_artifacts import ARTIFACT_FILES

SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"


def run_script(name, *args, env=None):
    return subprocess.run([sys.executable, "-B", str(SCRIPTS / name), *map(str, args)],
                          capture_output=True, text=True, env=env)


def payloads(alias, mode, tier, out):
    args = argparse.Namespace(alias=alias, mode=mode, tier=tier, track=None,
        question="Synthetic planning probe", out=out, domain_pack="generic-biomedical",
        dry_run=True, validate=False, export="none", force=False)
    result = bmat_run.bmat_init_bundle.build_payloads(alias, mode, args.question, out)
    bmat_run.enrich_payloads(result, args)
    return result


@pytest.mark.parametrize("alias", bmat_run.bmat_init_bundle.WORKFLOWS)
def test_quick_compact_reduces_work_and_full_keeps_gates(alias, tmp_path):
    quick = payloads(alias, "quick", "compact", tmp_path)
    standard = payloads(alias, "standard", "compact", tmp_path)
    full = payloads(alias, "audit", "full", tmp_path)
    assert len(quick) < len(full)
    assert len(quick["workflow_dag.json"]["nodes"]) < len(full["workflow_dag.json"]["nodes"])
    assert len(standard["workflow_dag.json"]["nodes"]) < len(full["workflow_dag.json"]["nodes"])
    assert not any(n.get("independence_required") for n in quick["workflow_dag.json"]["nodes"])
    assert any(n.get("independence_required") for n in full["workflow_dag.json"]["nodes"])
    for mode in ("deep", "audit", "run"):
        plan = bmat_run.workflow_dag_for_run(alias, mode, "compact")
        assert plan["nodes"] == bmat_run.select_workflow_dag(alias)["nodes"]
    assert bmat_run.workflow_dag_for_run(alias, "quick", "full")["nodes"] == bmat_run.select_workflow_dag(alias)["nodes"]
    for data in (quick, standard, full):
        seen = set()
        for node in data["workflow_dag.json"]["nodes"]:
            assert set(node.get("requires", [])) <= seen
            seen.add(node["id"])


def test_idea_quick_is_ideation_but_standard_scaffolds_empty_draft(tmp_path):
    quick = payloads("idea-discovery-team", "quick", "compact", tmp_path)
    assert quick["workflow_dag.json"]["track"] == "hypothesis-ideation"
    assert "hypothesis_tournament.json" not in quick
    draft = payloads("idea-discovery-team", "standard", "compact", tmp_path)["hypothesis_tournament.json"]
    assert draft["status"] == "draft"
    assert draft["candidates"] == draft["judge_scores"] == draft["final_ranking"] == []
    assert draft["candidate_order_randomization"]["seed"] is None
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((SKILL / "contracts/hypothesis-tournament.schema.json").read_text())
    jsonschema.Draft202012Validator(schema).validate(draft)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.Draft202012Validator(schema).validate({**draft, "status": "complete"})


@pytest.mark.parametrize("kind", ["array", "scalar", "null"])
def test_manifest_accepts_general_json_data(kind, tmp_path):
    data = {"array": [{"gene": "EXAMPLE", "score": 0.5}], "scalar": 42, "null": None}[kind]
    (tmp_path / "run_state.json").write_text(json.dumps({"run_id": "test", "plugin_version": "1.2.1"}))
    (tmp_path / "analysis.json").write_text(json.dumps(data))
    result = run_script("bmat_bundle_manifest.py", "--bundle", tmp_path)
    assert result.returncode == 0, result.stderr
    manifest = json.loads((tmp_path / "bundle_manifest.json").read_text())
    entry = next(e for e in manifest["entries"] if e["path"] == "analysis.json")
    assert entry["schema_version"] == "not-applicable"
    assert entry["sha256"] == bmat_validate.sha256_file(tmp_path / "analysis.json")


def test_manifest_still_rejects_array_in_contract_file(tmp_path):
    (tmp_path / "run_state.json").write_text(json.dumps({"run_id": "test", "plugin_version": "1.2.1"}))
    (tmp_path / "claim_ledger.json").write_text("[]")
    result = run_script("bmat_bundle_manifest.py", "--bundle", tmp_path)
    assert result.returncode != 0
    assert "must contain a JSON object" in result.stderr


@pytest.mark.parametrize("draft", [False, True])
def test_release_rejects_missing_or_draft_tournament_in_complete_fixture(tmp_path, draft):
    bundle = tmp_path / "bundle"
    shutil.copytree(SKILL / "tests/fixtures/valid_full_protocol_bundle", bundle)
    for filename in ("run_state.json", "runtime_capability_preflight.json", "lead_decision.json"):
        path = bundle / filename
        data = json.loads(path.read_text())
        for key in ("alias", "requested_alias"):
            if key in data:
                data[key] = "idea-discovery-team"
        path.write_text(json.dumps(data), encoding="utf-8")
    state = json.loads((bundle / "run_state.json").read_text())
    dag = bmat_run.workflow_dag_for_run("idea-discovery-team", "audit", "full")
    dag.update(schema_version="2.0", workflow_run_id=state["run_id"],
               plugin_version=state["plugin_version"], created_at=state["created_at"])
    state["workflow_dag_id"] = dag["workflow_id"]
    state["stages"] = [{"id": n["id"], "required": True, "status": "pass",
                        "evidence": "Synthetic regression mutation only"} for n in dag["nodes"]]
    (bundle / "run_state.json").write_text(json.dumps(state), encoding="utf-8")
    (bundle / "workflow_dag.json").write_text(json.dumps(dag), encoding="utf-8")
    if draft:
        tournament = bmat_run.default_hypothesis_tournament(state["run_id"], state["plugin_version"], "test", "generic-biomedical")
        (bundle / "hypothesis_tournament.json").write_text(json.dumps(tournament), encoding="utf-8")
    assert run_script("bmat_bundle_manifest.py", "--bundle", bundle).returncode == 0
    result = run_script("bmat_validate.py", "--bundle", bundle, "--release", "--json")
    assert result.returncode == 1, result.stdout + result.stderr
    codes = {row["code"] for row in json.loads(result.stdout) if row["level"] == "ERROR"}
    expected = "TOURNAMENT_DRAFT_NOT_RELEASE_ELIGIBLE" if draft else "TOURNAMENT_ARTIFACT_REQUIRED"
    # No unrelated gate failure can mask this regression.
    assert codes == ({expected} if draft else {expected, "WORKFLOW_DAG_OUTPUT_MISSING"})


def test_missing_declared_artifact_is_detected_from_central_registry():
    data = {"workflow_dag": {"nodes": [{"outputs": ["runtime_capability_preflight", "source_verification"]}]},
            "preflight": {}, "source_verification": None}
    assert bmat_workflow_policy.missing_declared_artifacts(data, ARTIFACT_FILES) == ["source_verification"]


def test_bundle_and_standalone_tournament_checks_agree():
    from test_bmat_tournament_v2 import valid_tournament
    import bmat_tournament_check
    valid = valid_tournament()
    broken = copy.deepcopy(valid)
    broken["candidates"][0]["blinded_candidate_id"] = broken["candidates"][0]["hypothesis_id"]
    for data in (valid, broken):
        findings = []
        bmat_validate.validate_hypothesis_tournament_policy({"hypothesis_tournament": data}, findings)
        assert {f.code for f in findings} == {f.code for f in bmat_tournament_check.check(data)}


def test_domain_file_availability_does_not_claim_reading(tmp_path):
    preflight = payloads("biomedical-research-council", "standard", "compact", tmp_path)["runtime_capability_preflight.json"]
    assert preflight["domain_specific_failure_modes_available"] is True
    assert preflight["domain_specific_failure_modes_loaded"] is False


def test_release_selftest_fails_without_jsonschema(tmp_path):
    (tmp_path / "jsonschema.py").write_text('raise ImportError("intentional dependency blocker")\n')
    env = os.environ.copy()
    env["PYTHONPATH"] = str(tmp_path) + os.pathsep + env.get("PYTHONPATH", "")
    result = run_script("bmat_selftest.py", "--root", SKILL, "--release", "--skip-golden", env=env)
    assert result.returncode == 1
    assert "release_passed" not in result.stdout
    assert "SCHEMA_VALIDATION_UNAVAILABLE" in result.stdout or "SCHEMA_VALIDATION_SKIPPED" in result.stdout


def test_installed_docs_and_independence_policy_are_consistent():
    plugin = SKILL.parents[1]
    for name in ("validation-boundaries.md", "migration-v1-to-v2.md", "release-checklist.md", "workflow-planning.md"):
        assert (plugin / "docs" / name).is_file()
    hybrid = (SKILL / "references/hybrid-execution-policy.md").read_text()
    council = (SKILL / "commands/biomedical-research-council.md").read_text()
    assert "same-model separate-pass review independent unless" not in hybrid
    assert "tool-corroborated review surface" not in council
    assert "Treat the user as an expert in immunology" not in council
