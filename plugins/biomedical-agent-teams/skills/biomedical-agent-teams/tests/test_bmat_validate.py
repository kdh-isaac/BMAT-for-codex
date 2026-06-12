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


def test_valid_bundle_passes() -> None:
    result = run_validator("valid_full_protocol_bundle")
    assert result.returncode == 0, combined_output(result)
    assert "ERROR" not in result.stdout


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
