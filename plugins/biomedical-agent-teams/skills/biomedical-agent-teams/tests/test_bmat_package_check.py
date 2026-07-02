from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = SKILL_ROOT.parents[1]
PACKAGE_CHECK = SKILL_ROOT / "scripts" / "bmat_package_check.py"
DOCS_LIST = SKILL_ROOT / "scripts" / "bmat_docs_list.py"
PLUGIN_JSON = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
UTF8_BOM_BYTES = b"\xef\xbb\xbf"
ROUTER_ROOT_GUARD_PHRASE = (
    "Resolve every command recipe path relative to the directory containing this `SKILL.md`"
)
ROUTER_LAZY_LOAD_GUARD_PHRASE = (
    "Do not load every agent, command, reference, contract, or template by default."
)
ROUTER_INVENTORY_DISCOVERY_GUARD_PHRASE = (
    "Use `source-manifest.json` and `scripts/bmat_docs_list.py` for inventory discovery."
)
VALIDATOR_RUNTIME_DOWNGRADE_TOKEN = "validator_unavailable_due_to_runtime"
SKILL_ROUTER_MAX_BYTES = 16_000
CROSS_PLATFORM_PREFLIGHT_TOKENS = (
    "host_os",
    "path_style",
    "python_invocation",
    "shell_family",
    "codex_runtime_capability_surface",
    "compute_budget",
)


def package_check_for(root: Path) -> Path:
    candidates = [
        root / "scripts" / "bmat_package_check.py",
        root / "skills" / "biomedical-agent-teams" / "scripts" / "bmat_package_check.py",
        root
        / "plugins"
        / "biomedical-agent-teams"
        / "skills"
        / "biomedical-agent-teams"
        / "scripts"
        / "bmat_package_check.py",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return PACKAGE_CHECK


def run_package_check(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(package_check_for(root)), "--root", str(root)],
        text=True,
        capture_output=True,
        check=False,
    )


def run_docs_list(root: Path) -> subprocess.CompletedProcess[str]:
    script = root / "skills" / "biomedical-agent-teams" / "scripts" / "bmat_docs_list.py"
    if not script.exists():
        script = DOCS_LIST
    return subprocess.run(
        [sys.executable, str(script), "--root", str(root)],
        text=True,
        capture_output=True,
        check=False,
    )


def copy_plugin(tmp_path: Path) -> Path:
    target = tmp_path / "biomedical-agent-teams"
    ignore = shutil.ignore_patterns("__pycache__", ".pytest_cache")
    shutil.copytree(PLUGIN_ROOT, target, ignore=ignore)
    return target


def prefix_utf8_bom(path: Path) -> None:
    path.write_bytes(UTF8_BOM_BYTES + path.read_bytes())


def test_current_plugin_default_prompts_fit_codex_limit() -> None:
    payload = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))
    default_prompts = payload.get("interface", {}).get("defaultPrompt", [])

    assert isinstance(default_prompts, list)
    assert len(default_prompts) <= 3


def test_current_package_check_passes() -> None:
    result = run_package_check(PLUGIN_ROOT)

    assert result.returncode == 0, result.stdout + result.stderr


def test_run_package_check_executes_checker_from_candidate_root(tmp_path: Path) -> None:
    plugin_root = copy_plugin(tmp_path)
    local_checker = plugin_root / "skills" / "biomedical-agent-teams" / "scripts" / "bmat_package_check.py"
    local_checker.write_text(
        "import sys\nprint('LOCAL_PACKAGE_CHECK_SENTINEL')\nsys.exit(7)\n",
        encoding="utf-8",
    )

    result = run_package_check(plugin_root)

    assert result.returncode == 7
    assert "LOCAL_PACKAGE_CHECK_SENTINEL" in result.stdout


def test_package_check_accepts_standalone_installed_skill_root(tmp_path: Path) -> None:
    skill_root = tmp_path / ".agents" / "skills" / "biomedical-agent-teams"
    ignore = shutil.ignore_patterns("__pycache__", ".pytest_cache")
    shutil.copytree(SKILL_ROOT, skill_root, ignore=ignore)

    result = run_package_check(skill_root)

    assert result.returncode == 0, result.stdout + result.stderr


def test_package_check_accepts_utf8_bom_prefixed_command_and_agent(tmp_path: Path) -> None:
    plugin_root = copy_plugin(tmp_path)
    skill_root = plugin_root / "skills" / "biomedical-agent-teams"
    prefix_utf8_bom(skill_root / "commands" / "evidence-audit-team.md")
    prefix_utf8_bom(skill_root / "agents" / "citation-verifier.md")

    result = run_package_check(plugin_root)

    assert result.returncode == 0, result.stdout + result.stderr


def test_docs_list_accepts_utf8_bom_prefixed_command_frontmatter(tmp_path: Path) -> None:
    plugin_root = copy_plugin(tmp_path)
    skill_root = plugin_root / "skills" / "biomedical-agent-teams"
    prefix_utf8_bom(skill_root / "commands" / "evidence-audit-team.md")

    result = run_docs_list(plugin_root)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "\ufeff" not in result.stdout
    assert "`commands\\evidence-audit-team.md` - Biomedical evidence-audit team" in result.stdout


def test_runtime_preflight_schema_has_codex_cross_platform_fields() -> None:
    schema_text = (SKILL_ROOT / "contracts" / "runtime-capability-preflight.schema.json").read_text(
        encoding="utf-8"
    )
    template_text = (SKILL_ROOT / "templates" / "runtime-capability-preflight-template.md").read_text(
        encoding="utf-8"
    )

    for token in CROSS_PLATFORM_PREFLIGHT_TOKENS:
        assert token in schema_text
    for token in ("Windows", "macOS", "PowerShell", "zsh", "sys.executable"):
        assert token in template_text


def test_current_skill_router_stays_under_loader_budget() -> None:
    skill_path = SKILL_ROOT / "SKILL.md"

    assert len(skill_path.read_bytes()) <= SKILL_ROUTER_MAX_BYTES


def test_package_check_flags_plugin_default_prompt_limit(tmp_path: Path) -> None:
    plugin_root = copy_plugin(tmp_path)
    plugin_json = plugin_root / ".codex-plugin" / "plugin.json"
    payload = json.loads(plugin_json.read_text(encoding="utf-8"))
    payload.setdefault("interface", {})["defaultPrompt"] = [
        "biomedical-research-council smoke prompt",
        "omics-analysis-team smoke prompt",
        "evidence-audit-team smoke prompt",
        "experiment-design-team excess prompt",
    ]
    plugin_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    result = run_package_check(plugin_root)

    assert result.returncode == 1
    assert "DEFAULT_PROMPT_LIMIT_EXCEEDED" in result.stdout


def test_package_check_flags_missing_skill_root_relative_router_guard(tmp_path: Path) -> None:
    plugin_root = copy_plugin(tmp_path)
    skill_path = plugin_root / "skills" / "biomedical-agent-teams" / "SKILL.md"
    text = skill_path.read_text(encoding="utf-8")
    skill_path.write_text(text.replace(ROUTER_ROOT_GUARD_PHRASE, ""), encoding="utf-8")

    result = run_package_check(plugin_root)

    assert result.returncode == 1
    assert "ROUTER_ROOT_GUARD_MISSING" in result.stdout


def test_package_check_flags_bloated_skill_router(tmp_path: Path) -> None:
    plugin_root = copy_plugin(tmp_path)
    skill_path = plugin_root / "skills" / "biomedical-agent-teams" / "SKILL.md"
    skill_path.write_text(
        skill_path.read_text(encoding="utf-8") + "\n" + ("x" * (SKILL_ROUTER_MAX_BYTES + 1)),
        encoding="utf-8",
    )

    result = run_package_check(plugin_root)

    assert result.returncode == 1
    assert "SKILL_ROUTER_TOO_LARGE" in result.stdout


def test_package_check_flags_missing_lazy_load_guard(tmp_path: Path) -> None:
    plugin_root = copy_plugin(tmp_path)
    skill_path = plugin_root / "skills" / "biomedical-agent-teams" / "SKILL.md"
    text = skill_path.read_text(encoding="utf-8")
    skill_path.write_text(text.replace(ROUTER_LAZY_LOAD_GUARD_PHRASE, ""), encoding="utf-8")

    result = run_package_check(plugin_root)

    assert result.returncode == 1
    assert "ROUTER_LAZY_LOAD_GUARD_MISSING" in result.stdout


def test_package_check_flags_missing_inventory_discovery_guard(tmp_path: Path) -> None:
    plugin_root = copy_plugin(tmp_path)
    skill_path = plugin_root / "skills" / "biomedical-agent-teams" / "SKILL.md"
    text = skill_path.read_text(encoding="utf-8")
    skill_path.write_text(
        text.replace(ROUTER_INVENTORY_DISCOVERY_GUARD_PHRASE, ""),
        encoding="utf-8",
    )

    result = run_package_check(plugin_root)

    assert result.returncode == 1
    assert "ROUTER_INVENTORY_DISCOVERY_GUARD_MISSING" in result.stdout


def test_package_check_flags_missing_validator_runtime_downgrade_guard(tmp_path: Path) -> None:
    plugin_root = copy_plugin(tmp_path)
    skill_path = plugin_root / "skills" / "biomedical-agent-teams" / "SKILL.md"
    text = skill_path.read_text(encoding="utf-8")
    skill_path.write_text(
        text.replace(VALIDATOR_RUNTIME_DOWNGRADE_TOKEN, "validator-runtime-token-removed"),
        encoding="utf-8",
    )

    result = run_package_check(plugin_root)

    assert result.returncode == 1
    assert "VALIDATOR_RUNTIME_DOWNGRADE_GUARD_MISSING" in result.stdout


def test_package_check_flags_non_codex_runtime_assumption(tmp_path: Path) -> None:
    plugin_root = copy_plugin(tmp_path)
    command_path = plugin_root / "skills" / "biomedical-agent-teams" / "commands" / "idea-discovery-team.md"
    command_path.write_text(
        command_path.read_text(encoding="utf-8")
        + "\n\nRelease-critical execution requires " + "host" + ".delegate fanout.\n",
        encoding="utf-8",
    )

    result = run_package_check(plugin_root)

    assert result.returncode == 1
    assert "NON_CODEX_HOST_DELEGATE_REFERENCE" in result.stdout


def test_package_check_flags_non_codex_instruction_dependency(tmp_path: Path) -> None:
    plugin_root = copy_plugin(tmp_path)
    agent_path = plugin_root / "skills" / "biomedical-agent-teams" / "agents" / "omics-reporter.md"
    agent_path.write_text(
        agent_path.read_text(encoding="utf-8") + "\n\nAlso inherit " + "CLA" + "UDE.md when present.\n",
        encoding="utf-8",
    )

    result = run_package_check(plugin_root)

    assert result.returncode == 1
    assert "NON_CODEX_MD_REFERENCE" in result.stdout


def test_package_check_flags_missing_cross_platform_preflight_field(tmp_path: Path) -> None:
    plugin_root = copy_plugin(tmp_path)
    schema_path = plugin_root / "skills" / "biomedical-agent-teams" / "contracts" / "runtime-capability-preflight.schema.json"
    schema_path.write_text(
        schema_path.read_text(encoding="utf-8").replace('"host_os": { "type": "string" },', ""),
        encoding="utf-8",
    )

    result = run_package_check(plugin_root)

    assert result.returncode == 1
    assert "RUNTIME_PREFLIGHT_PORTABILITY_FIELD_MISSING" in result.stdout


def test_package_check_flags_source_manifest_missing_actual_command(tmp_path: Path) -> None:
    plugin_root = copy_plugin(tmp_path)
    source_manifest_path = plugin_root / "skills" / "biomedical-agent-teams" / "source-manifest.json"
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    source_manifest["commands"] = [
        command for command in source_manifest["commands"] if command != "omics-analysis-team"
    ]
    source_manifest_path.write_text(json.dumps(source_manifest, indent=2), encoding="utf-8")

    result = run_package_check(plugin_root)

    assert result.returncode == 1
    assert "SOURCE_MANIFEST_SET_MISMATCH" in result.stdout


def test_package_check_flags_stale_fixture_plugin_version(tmp_path: Path) -> None:
    plugin_root = copy_plugin(tmp_path)
    fixture_path = plugin_root / "skills" / "biomedical-agent-teams" / "tests" / "fixtures" / "valid_full_protocol_bundle" / "run_state.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    payload["plugin_version"] = "invalid-stale-version"
    fixture_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    result = run_package_check(plugin_root)

    assert result.returncode == 1
    assert "FIXTURE_VERSION_MISMATCH" in result.stdout
