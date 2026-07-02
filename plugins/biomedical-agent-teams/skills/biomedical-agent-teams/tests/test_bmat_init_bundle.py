from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path
from types import ModuleType


SKILL_ROOT = Path(__file__).resolve().parents[1]
INIT_BUNDLE = SKILL_ROOT / "scripts" / "bmat_init_bundle.py"
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
    (skill_root / "VERSION").write_bytes(UTF8_BOM_BYTES + b"0.8.4\n")

    module = load_init_bundle_module(script_copy)

    assert module.plugin_version() == "0.8.4"
