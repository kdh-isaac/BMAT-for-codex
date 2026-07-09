from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType


SKILL_ROOT = Path(__file__).resolve().parents[1]
INIT_BUNDLE = SKILL_ROOT / "scripts" / "bmat_init_bundle.py"
BMAT_RUN = SKILL_ROOT / "scripts" / "bmat_run.py"
BMAT_ADAPTER = SKILL_ROOT / "scripts" / "bmat_codex_adapter.py"
VALIDATOR = SKILL_ROOT / "scripts" / "bmat_validate.py"
PREFLIGHT_FILE = "runtime_capability_preflight.json"
UTF8_BOM_BYTES = b"\xef\xbb\xbf"


def load_init_bundle_module(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("bmat_init_bundle_under_test", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_plugin_version_accepts_utf8_bom_prefixed_version_file(tmp_path: Path) -> None:
    skill_root = tmp_path / "skill"
    scripts = skill_root / "scripts"
    scripts.mkdir(parents=True)
    script_copy = scripts / "bmat_init_bundle.py"
    shutil.copy2(INIT_BUNDLE, script_copy)
    (skill_root / "VERSION").write_bytes(UTF8_BOM_BYTES + b"1.1.0\n")

    module = load_init_bundle_module(script_copy)

    assert module.plugin_version() == "1.1.0"


def test_shell_family_detects_windows_powershell_from_comspec(monkeypatch) -> None:
    module = load_init_bundle_module(INIT_BUNDLE)

    monkeypatch.delenv("SHELL", raising=False)
    monkeypatch.setenv(
        "COMSPEC",
        r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
    )

    assert module.shell_family() == "powershell"


def test_omics_run_scaffold_records_track_ambiguity_and_blocks_run_validation(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle with spaces"
    init_result = subprocess.run(
        [
            sys.executable,
            str(INIT_BUNDLE),
            "--workflow",
            "omics-analysis-team",
            "--mode",
            "run",
            "--topic",
            "synthetic omics scaffold",
            "--out",
            str(bundle),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert init_result.returncode == 0, init_result.stdout + init_result.stderr
    assert (bundle / PREFLIGHT_FILE).exists()
    assert not (bundle / "preflight.json").exists()
    preflight = json.loads((bundle / PREFLIGHT_FILE).read_text(encoding="utf-8"))
    lead_decision = json.loads((bundle / "lead_decision.json").read_text(encoding="utf-8"))
    assert preflight["runtime_id"] == preflight["runtime_capability_preflight_id"]
    assert preflight["codex_client"] == "codex"
    assert preflight["plugin_version"] == "1.1.0"
    assert preflight["workflow_tier"] == "compact"
    assert preflight["requested_omics_track"] == "track_ambiguous"
    assert "omics_track_ambiguity_note" in preflight
    assert lead_decision["requested_alias"] == "omics-analysis-team"
    assert lead_decision["selected_mode"] == "run"
    assert lead_decision["omics_subtrack"] == "track_ambiguous"
    assert preflight["python_invocation"]
    assert preflight["capabilities"]["shell_available"] == "yes"
    assert preflight["validator_cli_available"] == "yes"
    assert not (bundle / "omics_run_manifest.json").exists()

    validate_result = subprocess.run(
        [sys.executable, str(VALIDATOR), "--bundle", str(bundle)],
        text=True,
        capture_output=True,
        check=False,
    )
    output = validate_result.stdout + validate_result.stderr

    assert validate_result.returncode == 1, output
    assert "OMICS_RUN_TRACK_REQUIRED" in output
    assert "Traceback" not in output


def test_generated_readme_validator_command_uses_plugin_script_path(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    init_result = subprocess.run(
        [
            sys.executable,
            str(INIT_BUNDLE),
            "--workflow",
            "evidence-audit-team",
            "--mode",
            "audit",
            "--topic",
            "synthetic README command smoke",
            "--out",
            str(bundle),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert init_result.returncode == 0, init_result.stdout + init_result.stderr

    readme = (bundle / "README.md").read_text(encoding="utf-8")
    assert "scripts/bmat_validate.py --bundle <this-directory>" not in readme
    assert "not a bundle-local `scripts/` directory" in readme
    assert PREFLIGHT_FILE in readme

    command_match = re.search(r'`python "([^"]+bmat_validate\.py)" --bundle "([^"]+)"`', readme)
    assert command_match, readme
    validator_path = Path(command_match.group(1))
    bundle_path = Path(command_match.group(2))
    assert validator_path == VALIDATOR
    assert bundle_path == bundle.resolve()

    validate_result = subprocess.run(
        [sys.executable, str(validator_path), "--bundle", str(bundle_path)],
        cwd=bundle,
        text=True,
        capture_output=True,
        check=False,
    )
    assert validate_result.returncode == 0, validate_result.stdout + validate_result.stderr


def test_bmat_codex_adapter_executes_command_collects_artifacts_and_validates(tmp_path: Path) -> None:
    bundle = tmp_path / "adapter_bundle"
    result = subprocess.run(
        [
            sys.executable,
            str(BMAT_ADAPTER),
            "--alias",
            "evidence-audit-team",
            "--mode",
            "audit",
            "--tier",
            "full",
            "--question",
            "synthetic adapter artifact collection smoke",
            "--out",
            str(bundle),
            "--force",
            "--codex-command",
            sys.executable,
            "-c",
            "from pathlib import Path; Path('adapter_payload.txt').write_text('adapter ok\\n', encoding='utf-8'); print('adapter stdout sentinel')",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    adapter_run = json.loads((bundle / "adapter_run.json").read_text(encoding="utf-8"))
    artifact_manifest = json.loads((bundle / "adapter_artifact_manifest.json").read_text(encoding="utf-8"))
    artifact_paths = {artifact["path"] for artifact in artifact_manifest["artifacts"]}

    assert adapter_run["command_executed"] is True
    assert adapter_run["command_exit"] == 0
    assert adapter_run["command_timed_out"] is False
    assert adapter_run["validator_exit"] == 0
    assert (bundle / "adapter_payload.txt").read_text(encoding="utf-8") == "adapter ok\n"
    assert "adapter stdout sentinel" in (bundle / "adapter_command_stdout.md").read_text(encoding="utf-8")
    assert "adapter_payload.txt" in artifact_paths
    assert "adapter_command_stdout.md" in artifact_paths
    assert "adapter_validator_stdout.log" in artifact_paths
    assert "adapter_run.json" in artifact_paths


def test_bmat_codex_adapter_times_out_command_and_still_collects_artifacts(tmp_path: Path) -> None:
    bundle = tmp_path / "adapter_timeout_bundle"
    result = subprocess.run(
        [
            sys.executable,
            str(BMAT_ADAPTER),
            "--alias",
            "evidence-audit-team",
            "--mode",
            "audit",
            "--tier",
            "full",
            "--question",
            "synthetic adapter timeout smoke",
            "--out",
            str(bundle),
            "--force",
            "--command-timeout-seconds",
            "1",
            "--codex-command",
            sys.executable,
            "-c",
            "import time; time.sleep(2)",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 124, result.stdout + result.stderr
    adapter_run = json.loads((bundle / "adapter_run.json").read_text(encoding="utf-8"))
    artifact_manifest = json.loads((bundle / "adapter_artifact_manifest.json").read_text(encoding="utf-8"))
    artifact_paths = {artifact["path"] for artifact in artifact_manifest["artifacts"]}

    assert adapter_run["command_executed"] is True
    assert adapter_run["command_exit"] == 124
    assert adapter_run["command_timed_out"] is True
    assert adapter_run["validator_exit"] == 0
    assert "Command timed out after 1 seconds." in (bundle / "adapter_command_stderr.log").read_text(encoding="utf-8")
    assert "adapter_command_stderr.log" in artifact_paths
    assert "adapter_run.json" in artifact_paths


def test_bmat_run_dry_run_creates_dag_tool_ledger_and_workbench(tmp_path: Path) -> None:
    bundle = tmp_path / "run_bundle"
    result = subprocess.run(
        [
            sys.executable,
            str(BMAT_RUN),
            "--alias",
            "evidence-audit-team",
            "--mode",
            "audit",
            "--question",
            "synthetic runner smoke",
            "--out",
            str(bundle),
            "--dry-run",
            "--validate",
            "--export",
            "markdown",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert (bundle / "workflow_dag.json").exists()
    assert (bundle / "results_integration.json").exists()
    assert (bundle / "tool_call_ledger.json").exists()
    assert (bundle / "source_verification.json").exists()
    assert (bundle / "claim_support_matrix.json").exists()
    assert (bundle / "review_artifact_manifest.json").exists()
    assert list((bundle / "reports").glob("*/index.md"))


def test_bmat_run_normalizes_workflow_dag_to_requested_mode(tmp_path: Path) -> None:
    bundle = tmp_path / "run_bundle"
    result = subprocess.run(
        [
            sys.executable,
            str(BMAT_RUN),
            "--alias",
            "omics-analysis-team",
            "--mode",
            "audit",
            "--question",
            "synthetic runner mode smoke",
            "--out",
            str(bundle),
            "--dry-run",
            "--validate",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    run_state = json.loads((bundle / "run_state.json").read_text(encoding="utf-8"))
    preflight = json.loads((bundle / PREFLIGHT_FILE).read_text(encoding="utf-8"))
    workflow_dag = json.loads((bundle / "workflow_dag.json").read_text(encoding="utf-8"))
    assert run_state["mode"] == "audit"
    assert preflight["selected_mode"] == "audit"
    assert preflight["runtime_id"] == preflight["runtime_capability_preflight_id"]
    assert preflight["capabilities"]["file_write_available"] == "yes"
    assert workflow_dag["mode"] == "audit"
    assert run_state["workflow_dag_id"] == "omics-analysis-team.audit"
    assert preflight["workflow_dag_id"] == "omics-analysis-team.audit"
    assert workflow_dag["workflow_id"] == "omics-analysis-team.audit"


def test_bmat_run_rejects_unknown_domain_pack(tmp_path: Path) -> None:
    bundle = tmp_path / "run_bundle"
    result = subprocess.run(
        [
            sys.executable,
            str(BMAT_RUN),
            "--alias",
            "omics-analysis-team",
            "--mode",
            "audit",
            "--question",
            "synthetic unknown domain-pack smoke",
            "--out",
            str(bundle),
            "--dry-run",
            "--domain-pack",
            "ghost-pack",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "invalid choice" in result.stderr
    assert not bundle.exists()


def test_bmat_run_accepts_cell_therapy_domain_pack(tmp_path: Path) -> None:
    bundle = tmp_path / "run_bundle"
    result = subprocess.run(
        [
            sys.executable,
            str(BMAT_RUN),
            "--alias",
            "evidence-audit-team",
            "--mode",
            "audit",
            "--question",
            "synthetic cell therapy domain-pack smoke",
            "--out",
            str(bundle),
            "--dry-run",
            "--validate",
            "--domain-pack",
            "cell-therapy",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    run_state = json.loads((bundle / "run_state.json").read_text(encoding="utf-8"))
    preflight = json.loads((bundle / PREFLIGHT_FILE).read_text(encoding="utf-8"))
    assert run_state["domain_pack"] == "cell-therapy"
    assert preflight["domain_pack"] == "cell-therapy"
    assert preflight["domain_specific_failure_modes_loaded"] is True


def test_bmat_run_extended_tier_and_omics_fields_validate(tmp_path: Path) -> None:
    bundle = tmp_path / "extended_runner_bundle"
    result = subprocess.run(
        [
            sys.executable,
            str(BMAT_RUN),
            "--alias",
            "omics-analysis-team",
            "--mode",
            "run",
            "--question",
            "synthetic future runner field smoke",
            "--tier",
            "full",
            "--track",
            "tenx-gex",
            "--out",
            str(bundle),
            "--dry-run",
            "--validate",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    run_state_path = bundle / "run_state.json"
    preflight_path = bundle / PREFLIGHT_FILE
    run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    lead_decision = json.loads((bundle / "lead_decision.json").read_text(encoding="utf-8"))
    workflow_dag = json.loads((bundle / "workflow_dag.json").read_text(encoding="utf-8"))
    omics_manifest = json.loads((bundle / "omics_run_manifest.json").read_text(encoding="utf-8"))
    omics_metadata_check = json.loads((bundle / "omics_metadata_check.json").read_text(encoding="utf-8"))
    source_verification = json.loads((bundle / "source_verification.json").read_text(encoding="utf-8"))
    support_matrix = json.loads((bundle / "claim_support_matrix.json").read_text(encoding="utf-8"))
    review_manifest = json.loads((bundle / "review_artifact_manifest.json").read_text(encoding="utf-8"))
    assert run_state["workflow_tier"] == "full"
    assert run_state["omics_track"] == "tenx-gex"
    assert preflight["workflow_tier"] == "full"
    assert preflight["requested_omics_track"] == "tenx-gex"
    assert lead_decision["omics_subtrack"] == "tenx-gex"
    assert workflow_dag["track"] == "tenx-gex"
    assert omics_manifest["track"] == "tenx-gex"
    assert omics_metadata_check["track"] == "tenx-gex"
    assert source_verification["rows"] == []
    assert support_matrix["rows"] == []
    assert review_manifest["review_instances"] == []
    assert omics_manifest["assay_metadata"]["cellranger_version"] == "TODO"
    assert "molecule_info_h5" in omics_manifest["generated_artifacts"]

    validate_result = subprocess.run(
        [sys.executable, str(VALIDATOR), "--bundle", str(bundle), "--check-tool-ledger"],
        text=True,
        capture_output=True,
        check=False,
    )

    assert validate_result.returncode == 0, validate_result.stdout + validate_result.stderr
    output = validate_result.stdout + validate_result.stderr
    assert "SCHEMA_VALIDATION_FAILED" not in output
    assert "OMICS_RUN_REVIEWER_SPAWN_SKIPPED_WITH_DOWNGRADE" in output


def test_bmat_run_p2_tenx_subtracks_scaffold_track_specific_fields(tmp_path: Path) -> None:
    expected = {
        "tenx-citeseq": ("multi", "feature_barcode_matrix"),
        "tenx-vdj": ("vdj", "vdj_clonotypes"),
        "tenx-multiome": ("arc", "fragments_tsv_gz"),
    }
    for track, (cellranger_command, artifact_key) in expected.items():
        bundle = tmp_path / track
        result = subprocess.run(
            [
                sys.executable,
                str(BMAT_RUN),
                "--alias",
                "omics-analysis-team",
                "--mode",
                "run",
                "--question",
                f"synthetic {track} runner field smoke",
                "--tier",
                "full",
                "--track",
                track,
                "--out",
                str(bundle),
                "--dry-run",
                "--validate",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr

        omics_manifest = json.loads((bundle / "omics_run_manifest.json").read_text(encoding="utf-8"))
        assert omics_manifest["track"] == track
        assert omics_manifest["assay_metadata"]["cellranger_command"] == cellranger_command
        assert artifact_key in omics_manifest["generated_artifacts"]


def test_bmat_run_all_workflow_dags_scaffold_stages_and_validate(tmp_path: Path) -> None:
    for alias in (
        "biomedical-research-council",
        "idea-discovery-team",
        "omics-analysis-team",
        "evidence-audit-team",
        "experiment-design-team",
        "translational-scout-team",
    ):
        bundle = tmp_path / alias
        result = subprocess.run(
            [
                sys.executable,
                str(BMAT_RUN),
                "--alias",
                alias,
                "--mode",
                "audit",
                "--question",
                f"synthetic {alias} stage smoke",
                "--out",
                str(bundle),
                "--dry-run",
                "--validate",
            ],
            text=True,
            capture_output=True,
            check=False,
        )

        assert result.returncode == 0, result.stdout + result.stderr
        run_state = json.loads((bundle / "run_state.json").read_text(encoding="utf-8"))
        workflow_dag = json.loads((bundle / "workflow_dag.json").read_text(encoding="utf-8"))
        run_stage_ids = {
            stage["id"]
            for stage in run_state["stages"]
            if isinstance(stage, dict) and stage.get("id")
        }
        blocking_node_ids = {
            node["id"]
            for node in workflow_dag["nodes"]
            if isinstance(node, dict) and node.get("blocking") is True
        }

        assert run_state["alias"] == alias
        assert workflow_dag["alias"] == alias
        assert workflow_dag["mode"] == "audit"
        assert workflow_dag["workflow_id"] == f"{alias}.audit"
        assert blocking_node_ids <= run_stage_ids
        assert (bundle / "results_integration.json").exists()
        assert (bundle / "tool_call_ledger.json").exists()
        assert (bundle / "source_verification.json").exists()
        assert (bundle / "claim_support_matrix.json").exists()
        assert (bundle / "review_artifact_manifest.json").exists()
        if alias == "omics-analysis-team":
            assert (bundle / "omics_metadata_check.json").exists()
        if alias == "experiment-design-team":
            assert (bundle / "experiment_design.json").exists()
