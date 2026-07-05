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
    (skill_root / "VERSION").write_bytes(UTF8_BOM_BYTES + b"1.0.0\n")

    module = load_init_bundle_module(script_copy)

    assert module.plugin_version() == "1.0.0"


def test_shell_family_detects_windows_powershell_from_comspec(monkeypatch) -> None:
    module = load_init_bundle_module(INIT_BUNDLE)

    monkeypatch.delenv("SHELL", raising=False)
    monkeypatch.setenv(
        "COMSPEC",
        r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
    )

    assert module.shell_family() == "powershell"


def test_omics_run_scaffold_validates_with_explicit_reviewer_downgrade(tmp_path: Path) -> None:
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
    assert preflight["runtime_id"] == preflight["runtime_capability_preflight_id"]
    assert preflight["codex_client"] == "codex"
    assert preflight["plugin_version"] == "1.0.0"
    assert preflight["python_invocation"]
    assert preflight["capabilities"]["shell_available"] == "yes"
    assert preflight["validator_cli_available"] == "yes"

    validate_result = subprocess.run(
        [sys.executable, str(VALIDATOR), "--bundle", str(bundle)],
        text=True,
        capture_output=True,
        check=False,
    )
    output = validate_result.stdout + validate_result.stderr

    assert validate_result.returncode == 0, output
    assert "OMICS_RUN_REVIEWER_SPAWN_SKIPPED_WITH_DOWNGRADE" in output
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
