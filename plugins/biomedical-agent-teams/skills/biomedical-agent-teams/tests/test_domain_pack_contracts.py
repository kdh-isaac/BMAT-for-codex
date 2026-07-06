from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = SKILL_ROOT.parents[1]
PACKAGE_CHECK = SKILL_ROOT / "scripts" / "bmat_package_check.py"


def run_package_check(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(PACKAGE_CHECK), "--root", str(root)],
        text=True,
        capture_output=True,
        check=False,
    )


def test_package_check_requires_immuno_oncology_marker_panels(tmp_path: Path) -> None:
    plugin_copy = tmp_path / "biomedical-agent-teams"
    shutil.copytree(PLUGIN_ROOT, plugin_copy, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))

    marker_panels = (
        plugin_copy
        / "skills"
        / "biomedical-agent-teams"
        / "domain-packs"
        / "immuno-oncology"
        / "marker-panels.json"
    )
    marker_panels.unlink()

    result = run_package_check(plugin_copy)
    output = result.stdout + result.stderr

    assert result.returncode == 1
    assert "DOMAIN_PACK_FILE_MISSING" in output
    assert "immuno-oncology missing marker-panels.json" in output
