from __future__ import annotations

import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType


SKILL_ROOT = Path(__file__).resolve().parents[1]
INIT_BUNDLE = SKILL_ROOT / "scripts" / "bmat_init_bundle.py"
VALIDATOR = SKILL_ROOT / "scripts" / "bmat_validate.py"
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
    (skill_root / "VERSION").write_bytes(UTF8_BOM_BYTES + b"0.8.8\n")

    module = load_init_bundle_module(script_copy)

    assert module.plugin_version() == "0.8.8"


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
