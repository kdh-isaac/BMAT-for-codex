from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = SKILL_ROOT / "scripts" / "bmat_validate.py"
FIXTURES = SKILL_ROOT / "tests" / "fixtures"


def run_validator(fixture_name: str) -> subprocess.CompletedProcess[str]:
    return run_validator_path(FIXTURES / fixture_name)


def run_validator_path(bundle_path: Path) -> subprocess.CompletedProcess[str]:
    return run_validator_path_with_env(bundle_path, None)


def run_validator_path_with_env(
    bundle_path: Path,
    env: dict[str, str] | None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "--bundle", str(bundle_path)],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def run_validator_args(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def valid_results_integration_payload() -> dict[str, object]:
    return {
        "schema_version": "0.8",
        "integration_id": "RI-TEST-001",
        "plugin_version": "0.8.0",
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


def combined_output(result: subprocess.CompletedProcess[str]) -> str:
    return result.stdout + result.stderr


def add_valid_team_dag(run_state: dict[str, object]) -> None:
    run_state["execution_strategy"] = "team_level_selective_dag"
    run_state["team_spawn_lanes"] = [
        {
            "team": "idea-discovery-team",
            "phase": 1,
            "depends_on": [],
            "status": "complete",
            "nested_spawn_used": False,
            "ledger_handoff": "TEAM-IDEA-001 accepted into CL-IDEA",
        },
        {
            "team": "experiment-design-team",
            "phase": 2,
            "depends_on": ["idea-discovery-team"],
            "status": "complete",
            "nested_spawn_used": False,
            "ledger_handoff": "TEAM-EXPERIMENT-001 accepted into CL-DESIGN",
        },
    ]
    run_state["team_output_artifacts"] = [
        {
            "team": "idea-discovery-team",
            "phase": 1,
            "artifact_id": "TEAM-IDEA-001",
            "path": "team-outputs/idea-discovery-team.md",
            "status": "complete",
            "input_scope": "candidate hypothesis generation",
            "checks_run": ["formal team output contract checked"],
            "ledger_handoff": "TEAM-IDEA-001 accepted into CL-IDEA",
            "depends_on_outputs": [],
        },
        {
            "team": "experiment-design-team",
            "phase": 2,
            "artifact_id": "TEAM-EXPERIMENT-001",
            "path": "team-outputs/experiment-design-team.md",
            "status": "complete",
            "input_scope": "validation design for narrowed candidate",
            "checks_run": ["formal team output contract checked", "phase dependency checked"],
            "ledger_handoff": "TEAM-EXPERIMENT-001 accepted into CL-DESIGN",
            "depends_on_outputs": ["TEAM-IDEA-001"],
        },
    ]


def make_omics_run_bundle(
    tmp_path: Path,
    *,
    spawned_review_plan: dict[str, object],
    downgrade_reasons: list[str] | None = None,
    skipped_role_outputs: list[dict[str, str]] | None = None,
    spawned_review_lanes: list[dict[str, object]] | None = None,
    spawned_agent_instances: list[dict[str, object]] | None = None,
    independent_review_status: str = "same-model separate-pass validation",
) -> Path:
    bundle = tmp_path / "omics_bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)

    preflight_path = bundle / "preflight.json"
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    preflight["requested_alias"] = "omics-analysis-team"
    preflight["selected_mode"] = "run"
    preflight["deliverable_type"] = "synthetic omics run fixture"
    preflight["required_role_outputs"] = [
        "omics-code-reviewer",
        "omics-provenance-validator",
        "post-write-final-validator",
    ]
    preflight["skipped_role_outputs_with_reason"] = skipped_role_outputs or []
    preflight["spawned_review_plan"] = spawned_review_plan
    preflight["workflow_run_id"] = "omics-run-fixture"
    preflight_path.write_text(json.dumps(preflight, indent=2), encoding="utf-8")

    claim_ledger_path = bundle / "claim_ledger.json"
    claim_ledger = json.loads(claim_ledger_path.read_text(encoding="utf-8"))
    for claim in claim_ledger.get("claims", []):
        if isinstance(claim, dict):
            claim["claim_strength"] = "exploratory"
    claim_ledger_path.write_text(json.dumps(claim_ledger, indent=2), encoding="utf-8")

    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    run_state["run_id"] = "omics-run-fixture"
    run_state["alias"] = "omics-analysis-team"
    run_state["mode"] = "run"
    run_state["execution_strategy"] = "inline_first_selective_review"
    run_state["spawned_review_lanes"] = spawned_review_lanes or []
    run_state["spawned_agent_instances"] = spawned_agent_instances or []
    run_state["final_label"] = "Compact standard workflow"
    run_state["downgrade_reasons"] = downgrade_reasons or []
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    post_write_path = bundle / "post_write_validation.json"
    post_write = json.loads(post_write_path.read_text(encoding="utf-8"))
    post_write["independent_review_status"] = independent_review_status
    post_write["release_ready_claim_strength"] = "exploratory association"
    post_write_path.write_text(json.dumps(post_write, indent=2), encoding="utf-8")

    (bundle / "final.md").write_text(
        "Final workflow label: Compact standard workflow\n"
        "Synthetic omics run fixture for reviewer-spawn policy.\n",
        encoding="utf-8",
    )
    return bundle


def test_valid_bundle_passes() -> None:
    result = run_validator("valid_full_protocol_bundle")
    assert result.returncode == 0, combined_output(result)
    assert "ERROR" not in result.stdout


def test_results_integration_artifact_schema_is_validated_when_present(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    payload = valid_results_integration_payload()
    payload["tool_use_log"][0]["used"] = False
    (bundle / "results_integration.json").write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "SCHEMA_VALIDATION_FAILED" in combined_output(result)
    assert "results_integration" in combined_output(result)


def test_full_protocol_without_independent_review_fails() -> None:
    result = run_validator("invalid_full_protocol_without_independent_review")
    assert result.returncode == 1
    assert "FULL_PROTOCOL_REQUIRES_INDEPENDENT_SURFACE" in combined_output(result)


def test_s3_block_blocks_high_confidence_claim() -> None:
    result = run_validator("invalid_s3_block_high_confidence")
    assert result.returncode == 1
    assert "S3_BLOCKS_HIGH_CONFIDENCE" in combined_output(result)


def test_missing_source_for_source_backed_claim_fails() -> None:
    result = run_validator("invalid_missing_source_for_claim")
    assert result.returncode == 1
    assert "SOURCE_BACKED_CLAIM_MISSING_SOURCE" in combined_output(result)


def test_final_wording_drift_fails() -> None:
    result = run_validator("invalid_final_wording_drift")
    assert result.returncode == 1
    assert "FINAL_WORDING_DRIFT" in combined_output(result)


def test_compact_standard_label_requires_formal_artifacts(tmp_path: Path) -> None:
    final_text = tmp_path / "final.md"
    final_text.write_text("Final workflow label: Compact standard workflow\n", encoding="utf-8")

    result = run_validator_args("--final-text", str(final_text))

    output = combined_output(result)
    assert result.returncode == 1
    assert "COMPACT_WORKFLOW_REQUIRES_ARTIFACT" in output
    assert "preflight.json" in output
    assert "source_corpus.json" in output
    assert "claim_ledger.json" in output
    assert "post_write_validation.json" in output


def test_full_protocol_label_in_final_text_requires_run_state(tmp_path: Path) -> None:
    final_text = tmp_path / "final.md"
    final_text.write_text("Final workflow label: Full protocol followed\n", encoding="utf-8")

    result = run_validator_args("--final-text", str(final_text))

    output = combined_output(result)
    assert result.returncode == 1
    assert "FULL_PROTOCOL_REQUIRES_RUN_STATE" in output
    assert "FULL_PROTOCOL_REQUIRES_PREFLIGHT" in output
    assert "FULL_PROTOCOL_REQUIRES_POST_WRITE" in output


def test_negated_full_protocol_label_does_not_trigger_full_policy(tmp_path: Path) -> None:
    final_text = tmp_path / "final.md"
    final_text.write_text(
        "Final workflow label: Compact standard workflow\n"
        "This is not labeled Full protocol followed because independent review was not run.\n",
        encoding="utf-8",
    )

    result = run_validator_args("--final-text", str(final_text))

    output = combined_output(result)
    assert result.returncode == 1
    assert "COMPACT_WORKFLOW_REQUIRES_ARTIFACT" in output
    assert "FULL_PROTOCOL_REQUIRES_" not in output


def test_complete_spawned_review_lane_requires_actual_instance(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    run_state.pop("spawned_agent_instances")
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "SPAWNED_LANE_MISSING_INSTANCE" in combined_output(result)


def test_full_protocol_requires_complete_independent_instance(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    run_state["spawned_review_lanes"] = []
    run_state.pop("spawned_agent_instances")
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "FULL_PROTOCOL_REQUIRES_INDEPENDENT_INSTANCE" in combined_output(result)


def test_failed_spawned_instance_does_not_satisfy_full_protocol(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    run_state["spawned_review_lanes"] = []
    run_state["spawned_agent_instances"][0]["status"] = "failed"
    run_state["spawned_agent_instances"][0]["failure_or_downgrade_reason"] = "synthetic failed reviewer"
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "FULL_PROTOCOL_REQUIRES_INDEPENDENT_INSTANCE" in combined_output(result)


def test_unknown_spawned_instance_agent_fails(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    run_state["spawned_agent_instances"][0]["agent_id"] = "ghost-reviewer"
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "SPAWNED_INSTANCE_UNKNOWN_AGENT" in combined_output(result)


def test_complete_spawned_instance_requires_output_artifact(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    run_state["spawned_agent_instances"][0]["output_artifact"] = ""
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "SPAWNED_INSTANCE_MISSING_OUTPUT_ARTIFACT" in combined_output(result)


def test_duplicate_spawned_instance_id_fails(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    run_state["spawned_agent_instances"].append(dict(run_state["spawned_agent_instances"][0]))
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "SPAWNED_INSTANCE_DUPLICATE_ID" in combined_output(result)


def test_malformed_spawned_instances_shape_returns_policy_error(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    run_state["spawned_agent_instances"] = {"agent_id": "citation-verifier"}
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    assert result.returncode == 1
    output = combined_output(result)
    assert "INVALID_SPAWNED_AGENT_INSTANCES" in output
    assert "Traceback" not in output


def test_omics_run_reviewer_budget_zero_without_exception_fails(tmp_path: Path) -> None:
    bundle = make_omics_run_bundle(
        tmp_path,
        spawned_review_plan={
            "allowed": False,
            "budget": 0,
            "selected_roles": [],
            "rationale": "Inline deterministic checks were considered sufficient.",
        },
        downgrade_reasons=["No spawned independent reviewer."],
    )

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "OMICS_RUN_REVIEWER_SPAWN_REQUIRED" in combined_output(result)


def test_omics_run_reviewer_budget_zero_with_runtime_exception_warns(tmp_path: Path) -> None:
    bundle = make_omics_run_bundle(
        tmp_path,
        spawned_review_plan={
            "allowed": False,
            "budget": 0,
            "selected_roles": [],
            "rationale": "Spawned-subagent support unavailable in this runtime.",
        },
        skipped_role_outputs=[
            {
                "role": "omics-code-reviewer",
                "reason": "spawned-subagent support unavailable; compact inline-only downgrade recorded",
            }
        ],
        downgrade_reasons=["spawned-subagent support unavailable; downgraded to Compact standard workflow"],
    )

    result = run_validator_path(bundle)

    assert result.returncode == 0, combined_output(result)
    assert "OMICS_RUN_REVIEWER_SPAWN_SKIPPED_WITH_DOWNGRADE" in combined_output(result)


def test_omics_run_requires_core_reviewer_role(tmp_path: Path) -> None:
    bundle = make_omics_run_bundle(
        tmp_path,
        spawned_review_plan={
            "allowed": True,
            "budget": 1,
            "selected_roles": ["citation-verifier"],
            "rationale": "Incorrectly selected a non-core reviewer for omics run.",
        },
    )

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "OMICS_RUN_CORE_REVIEWER_REQUIRED" in combined_output(result)


def test_omics_run_core_reviewer_instance_passes(tmp_path: Path) -> None:
    bundle = make_omics_run_bundle(
        tmp_path,
        spawned_review_plan={
            "allowed": True,
            "budget": 1,
            "selected_roles": ["omics-code-reviewer"],
            "rationale": "Core reviewer spawned after S1-S3 locks.",
        },
        spawned_review_lanes=[
            {
                "role": "omics-code-reviewer",
                "status": "complete",
                "rationale": "Reviewed code, leakage, and reproducibility.",
                "ledger_handoff": "CL-001 code/provenance checks accepted",
            }
        ],
        spawned_agent_instances=[
            {
                "instance_id": "OMICS-CODE-REVIEW-001",
                "agent_id": "omics-code-reviewer",
                "execution_surface": "spawned_subagent",
                "spawn_tool": "multi_agent_v1.spawn_agent",
                "thread_or_task_id": "synthetic-omics-code-review",
                "parent_run_id": "omics-run-fixture",
                "status": "complete",
                "input_scope": "synthetic omics scripts and result tables",
                "output_artifact": "review/omics-code-reviewer.md",
                "checks_run": ["script reproducibility", "raw-data safety", "leakage review"],
                "ledger_handoff": "CL-001 code/provenance checks accepted",
            }
        ],
        independent_review_status="spawned_subagent omics-code-reviewer complete",
    )

    result = run_validator_path(bundle)

    assert result.returncode == 0, combined_output(result)
    assert "VALIDATION_PASSED" in combined_output(result)


def test_valid_team_level_selective_dag_passes(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    add_valid_team_dag(run_state)
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    assert result.returncode == 0, combined_output(result)
    assert "ERROR" not in result.stdout


def test_complete_team_spawn_lane_requires_team_output_artifact(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    add_valid_team_dag(run_state)
    run_state["team_output_artifacts"] = run_state["team_output_artifacts"][:1]
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "TEAM_SPAWN_LANE_MISSING_OUTPUT_ARTIFACT" in combined_output(result)


def test_team_nested_spawn_requires_explicit_approval(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    add_valid_team_dag(run_state)
    run_state["team_spawn_lanes"][0]["nested_spawn_used"] = True
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "TEAM_NESTED_SPAWN_NOT_ALLOWED" in combined_output(result)


def test_team_phase_dependency_must_resolve_to_prior_complete_output(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    add_valid_team_dag(run_state)
    run_state["team_spawn_lanes"][1]["depends_on"] = ["missing-team"]
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "TEAM_DAG_DEPENDENCY_UNRESOLVED" in combined_output(result)


def test_malformed_team_output_artifacts_shape_returns_policy_error(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    run_state["team_output_artifacts"] = {"team": "idea-discovery-team"}
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    output = combined_output(result)
    assert result.returncode == 1
    assert "INVALID_TEAM_OUTPUT_ARTIFACTS" in output
    assert "Traceback" not in output


def test_team_output_dependency_must_resolve_to_complete_artifact(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    add_valid_team_dag(run_state)
    run_state["team_output_artifacts"][1]["depends_on_outputs"] = ["missing-output"]
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "TEAM_OUTPUT_DEPENDENCY_UNRESOLVED" in combined_output(result)


def test_duplicate_complete_team_spawn_lane_fails(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    add_valid_team_dag(run_state)
    run_state["team_spawn_lanes"].append(dict(run_state["team_spawn_lanes"][0]))
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "TEAM_SPAWN_LANE_DUPLICATE" in combined_output(result)


def test_duplicate_complete_team_output_key_fails(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    add_valid_team_dag(run_state)
    duplicate_output = dict(run_state["team_output_artifacts"][0])
    duplicate_output["artifact_id"] = "TEAM-IDEA-DUPLICATE"
    duplicate_output["path"] = "team-outputs/idea-discovery-team-duplicate.md"
    run_state["team_output_artifacts"].append(duplicate_output)
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "TEAM_OUTPUT_DUPLICATE" in combined_output(result)


def test_duplicate_complete_team_output_artifact_id_fails(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    add_valid_team_dag(run_state)
    run_state["team_output_artifacts"][1]["artifact_id"] = "TEAM-IDEA-001"
    run_state["team_output_artifacts"][1]["depends_on_outputs"] = []
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "TEAM_OUTPUT_DUPLICATE_ARTIFACT_ID" in combined_output(result)


def test_team_output_dependency_cannot_self_reference(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    add_valid_team_dag(run_state)
    run_state["team_output_artifacts"][1]["depends_on_outputs"] = ["TEAM-EXPERIMENT-001"]
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "TEAM_OUTPUT_DEPENDENCY_SELF_REFERENCE" in combined_output(result)


def test_team_output_dependency_must_reference_prior_phase(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    add_valid_team_dag(run_state)
    run_state["team_output_artifacts"][0]["depends_on_outputs"] = ["TEAM-EXPERIMENT-001"]
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    result = run_validator_path(bundle)

    assert result.returncode == 1
    assert "TEAM_OUTPUT_DEPENDENCY_ORDER_INVALID" in combined_output(result)


def test_missing_run_state_required_field_fails_without_jsonschema(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    shutil.copytree(FIXTURES / "valid_full_protocol_bundle", bundle)
    run_state_path = bundle / "run_state.json"
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    del run_state["final_label"]
    run_state_path.write_text(json.dumps(run_state, indent=2), encoding="utf-8")

    blocker = tmp_path / "no_jsonschema"
    blocker.mkdir()
    (blocker / "jsonschema.py").write_text('raise ImportError("blocked by test")\n', encoding="utf-8")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(blocker) + os.pathsep + env.get("PYTHONPATH", "")

    result = run_validator_path_with_env(bundle, env)

    output = combined_output(result)
    assert result.returncode == 1
    assert "SCHEMA_VALIDATION_SKIPPED" in output
    assert "RUN_STATE_REQUIRED_FIELD_MISSING" in output
    assert "final_label" in output
    assert "Traceback" not in output
