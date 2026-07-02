#!/usr/bin/env python3
"""Validate the Biomedical Agent Teams package layout.

This checks the plugin package itself, not an individual BMAT workflow artifact
bundle. It is intentionally dependency-free so it can run in source checkouts,
marketplace sources, and installed cache roots.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Finding:
    level: str
    code: str
    message: str
    path: str = ""


COUNT_KEYS = {
    "agent_count": ("agents", "*.md"),
    "command_count": ("commands", "*.md"),
    "template_count": ("templates", "*.md"),
    "contract_count": ("contracts", "*.json"),
    "reference_count": ("references", "*.md"),
    "loop_count": ("loops", "*.md"),
    "codex_agent_template_count": ("codex-agents", "*.toml"),
    "script_count": ("scripts", "*.py"),
}
SOURCE_MANIFEST_COLLECTIONS = {
    "commands": ("commands", ".md"),
    "agent_roster": ("agents", ".md"),
    "contracts": ("contracts", ".json"),
    "templates": ("templates", ".md"),
    "references": ("references", ".md"),
    "loops": ("loops", ".md"),
    "scripts": ("scripts", ".py"),
    "codex_agent_templates": ("codex-agents", ".toml"),
}
CODEX_DEFAULT_PROMPT_LIMIT = 3
SKILL_ROUTER_MAX_BYTES = 16_000
ROUTER_ROOT_GUARD_PHRASE = (
    "Resolve every command recipe path relative to the directory containing this `SKILL.md`"
)
LAZY_LOAD_GUARD_PHRASES = {
    "ROUTER_LAZY_LOAD_GUARD_MISSING": "Do not load every agent, command, reference, contract, or template by default.",
    "ROUTER_INVENTORY_DISCOVERY_GUARD_MISSING": "Use `source-manifest.json` and `scripts/bmat_docs_list.py` for inventory discovery.",
    "VALIDATOR_RUNTIME_DOWNGRADE_GUARD_MISSING": "validator_unavailable_due_to_runtime",
    "VALIDATOR_FULL_PROTOCOL_CEILING_MISSING": "Do not claim `Full protocol followed`",
}
CODEX_ONLY_BLOCKED_TERMS = {
    "NON_CODEX_MD_REFERENCE": "CLA" + "UDE.md",
    "NON_CODEX_HOST_DELEGATE_REFERENCE": "host" + ".delegate",
    "NON_CODEX_SUBAGENT_REFERENCE": "Clau" + "de subagent",
    "NON_CODEX_HOOK_REFERENCE": "Clau" + "de hook",
    "NON_CODEX_MARKETPLACE_REFERENCE": "Clau" + "de marketplace",
    "NON_CODEX_ONLY_COMMAND_REFERENCE": "Clau" + "de-only slash command",
}
UTF8_BOM = "\ufeff"
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


def count_golden_tasks(skill_root: Path, findings: list[Finding]) -> int:
    path = skill_root / "evals" / "golden_tasks.jsonl"
    text = read_text(path, findings)
    return sum(1 for line in text.splitlines() if line.strip())


def special_counts(skill_root: Path, findings: list[Finding]) -> dict[str, int]:
    return {
        "test_fixture_count": len([path for path in (skill_root / "tests" / "fixtures").iterdir() if path.is_dir()])
        if (skill_root / "tests" / "fixtures").exists()
        else 0,
        "eval_count": len(list((skill_root / "evals").glob("*.py"))),
        "golden_task_count": count_golden_tasks(skill_root, findings),
        "agent_registry_count": 1 if (skill_root / "agent-registry.json").exists() else 0,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a BMAT plugin package.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="BMAT skill root, plugin root, marketplace repo root, or installed cache root.",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable findings.")
    return parser.parse_args()


def strip_bom(text: str) -> str:
    return text[1:] if text.startswith(UTF8_BOM) else text


def read_json(path: Path, findings: list[Finding]) -> Any:
    try:
        return json.loads(strip_bom(path.read_text(encoding="utf-8-sig")))
    except FileNotFoundError:
        findings.append(Finding("ERROR", "FILE_MISSING", "JSON file missing", str(path)))
    except UnicodeDecodeError as exc:
        findings.append(Finding("ERROR", "TEXT_DECODE_ERROR", f"could not decode as UTF-8: {exc}", str(path)))
    except json.JSONDecodeError as exc:
        findings.append(Finding("ERROR", "INVALID_JSON", f"invalid JSON: {exc}", str(path)))
    return None


def read_text(path: Path, findings: list[Finding]) -> str:
    try:
        return strip_bom(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        findings.append(Finding("ERROR", "FILE_MISSING", "file missing", str(path)))
    except UnicodeDecodeError as exc:
        findings.append(Finding("ERROR", "TEXT_DECODE_ERROR", f"could not decode as UTF-8: {exc}", str(path)))
    return ""


def bom_check_paths(skill_root: Path) -> list[Path]:
    paths: list[Path] = []
    plugin_json_path = plugin_json_path_for(skill_root)
    if plugin_json_path is not None:
        paths.append(plugin_json_path)

    for path in sorted(skill_root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in {"__pycache__", ".pytest_cache"} for part in path.parts):
            continue
        if path.name in BOM_CHECK_FILENAMES or path.suffix.lower() in BOM_CHECK_EXTENSIONS:
            paths.append(path)
    return paths


def validate_no_bom_bytes(skill_root: Path, findings: list[Finding]) -> None:
    for path in bom_check_paths(skill_root):
        try:
            prefix = path.read_bytes()[:4]
        except OSError as exc:
            findings.append(Finding("ERROR", "FILE_READ_ERROR", f"could not read file bytes: {exc}", str(path)))
            continue
        for signature, label in BOM_SIGNATURES:
            if prefix.startswith(signature):
                findings.append(
                    Finding(
                        "ERROR",
                        "BOM_BYTES_PRESENT",
                        f"{label} detected at file start; release files must be BOM-free",
                        str(path),
                    )
                )
                break


def resolve_skill_root(root: Path, findings: list[Finding]) -> Path:
    root = root.resolve()
    candidates = [
        root,
        root / "skills" / "biomedical-agent-teams",
        root / "plugins" / "biomedical-agent-teams" / "skills" / "biomedical-agent-teams",
    ]
    for candidate in candidates:
        if (candidate / "SKILL.md").exists() and (candidate / "VERSION").exists():
            return candidate
    findings.append(
        Finding(
            "ERROR",
            "SKILL_ROOT_NOT_FOUND",
            "could not resolve BMAT skill root from --root",
            str(root),
        )
    )
    return root


def plugin_root_for(skill_root: Path) -> Path:
    if skill_root.parent.name == "skills":
        candidate = skill_root.parents[1]
        if (candidate / ".codex-plugin" / "plugin.json").exists():
            return candidate
    return skill_root


def plugin_json_path_for(skill_root: Path) -> Path | None:
    plugin_json = plugin_root_for(skill_root) / ".codex-plugin" / "plugin.json"
    if plugin_json.exists():
        return plugin_json
    return None


def frontmatter_value(frontmatter: str, key: str) -> str | None:
    match = re.search(rf"^{key}:\s*(.*)$", frontmatter, re.M)
    if not match:
        return None
    value = match.group(1).strip()
    if value and value not in {">", "|", ">-", "|-"}:
        return value.strip('"')

    tail = frontmatter[match.end() :].splitlines()
    block: list[str] = []
    for line in tail:
        if line and not line.startswith((" ", "\t")):
            break
        stripped = line.strip()
        if stripped:
            block.append(stripped)
    return " ".join(block) if block else None


def extract_frontmatter(text: str, path: Path, findings: list[Finding]) -> dict[str, str]:
    text = strip_bom(text)
    match = re.match(r"\A---\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", text, re.S)
    if not match:
        findings.append(Finding("ERROR", "FRONTMATTER_MISSING", "frontmatter missing", str(path)))
        return {}
    frontmatter = match.group(1)
    out: dict[str, str] = {}
    for key in ("name", "description"):
        value = frontmatter_value(frontmatter, key)
        if value:
            out[key] = value
        else:
            findings.append(Finding("ERROR", "FRONTMATTER_FIELD_MISSING", f"{key} missing", str(path)))
    version_match = re.search(r'^\s*version:\s*"([^"]+)"\s*$', frontmatter, re.M)
    if version_match:
        out["version"] = version_match.group(1)
    else:
        findings.append(Finding("ERROR", "FRONTMATTER_VERSION_MISSING", "metadata.version missing", str(path)))
    return out


def expect_equal(
    actual: Any,
    expected: Any,
    code: str,
    message: str,
    path: Path | str,
    findings: list[Finding],
) -> None:
    if actual != expected:
        findings.append(
            Finding("ERROR", code, f"{message}: expected {expected!r}, found {actual!r}", str(path))
        )


def validate_versions(skill_root: Path, findings: list[Finding]) -> str:
    version = read_text(skill_root / "VERSION", findings).strip()
    plugin_json_path = plugin_json_path_for(skill_root)
    plugin = read_json(plugin_json_path, findings) if plugin_json_path is not None else None
    manifest = read_json(skill_root / "manifest.json", findings)
    source_manifest = read_json(skill_root / "source-manifest.json", findings)
    registry = read_json(skill_root / "agent-registry.json", findings)
    skill_text = read_text(skill_root / "SKILL.md", findings)
    frontmatter = extract_frontmatter(skill_text, skill_root / "SKILL.md", findings)

    if isinstance(plugin, dict):
        expect_equal(plugin.get("version"), version, "VERSION_MISMATCH", "plugin.json version mismatch", plugin_json_path or "", findings)
    if isinstance(manifest, dict):
        expect_equal(manifest.get("version"), version, "VERSION_MISMATCH", "manifest version mismatch", skill_root / "manifest.json", findings)
        expect_equal(manifest.get("adapter_version"), version, "VERSION_MISMATCH", "manifest adapter_version mismatch", skill_root / "manifest.json", findings)
    if isinstance(source_manifest, dict):
        expect_equal(source_manifest.get("version"), version, "VERSION_MISMATCH", "source-manifest version mismatch", skill_root / "source-manifest.json", findings)
    if isinstance(registry, dict):
        expect_equal(registry.get("version"), version, "VERSION_MISMATCH", "agent-registry version mismatch", skill_root / "agent-registry.json", findings)
    if frontmatter:
        expect_equal(frontmatter.get("version"), version, "VERSION_MISMATCH", "SKILL metadata version mismatch", skill_root / "SKILL.md", findings)

    for toml in sorted((skill_root / "codex-agents").glob("*.toml")):
        text = read_text(toml, findings)
        match = re.search(r'^version\s*=\s*"([^"]+)"\s*$', text, re.M)
        if not match:
            findings.append(Finding("ERROR", "TOML_VERSION_MISSING", "TOML version missing", str(toml)))
        else:
            expect_equal(match.group(1), version, "VERSION_MISMATCH", "TOML version mismatch", toml, findings)

    return version


def validate_plugin_interface(skill_root: Path, findings: list[Finding]) -> None:
    plugin_json_path = plugin_json_path_for(skill_root)
    if plugin_json_path is None:
        return
    plugin = read_json(plugin_json_path, findings)
    if not isinstance(plugin, dict):
        return
    interface = plugin.get("interface")
    if not isinstance(interface, dict):
        findings.append(
            Finding(
                "ERROR",
                "PLUGIN_INTERFACE_MISSING",
                "plugin.json interface object missing",
                str(plugin_json_path),
            )
        )
        return
    default_prompts = interface.get("defaultPrompt", [])
    if not isinstance(default_prompts, list):
        findings.append(
            Finding(
                "ERROR",
                "DEFAULT_PROMPT_INVALID",
                "interface.defaultPrompt must be a list",
                str(plugin_json_path),
            )
        )
        return
    if len(default_prompts) > CODEX_DEFAULT_PROMPT_LIMIT:
        findings.append(
            Finding(
                "ERROR",
                "DEFAULT_PROMPT_LIMIT_EXCEEDED",
                (
                    "interface.defaultPrompt exceeds Codex loader limit: "
                    f"maximum {CODEX_DEFAULT_PROMPT_LIMIT}, found {len(default_prompts)}"
                ),
                str(plugin_json_path),
            )
        )


def validate_counts(skill_root: Path, findings: list[Finding]) -> None:
    manifest = read_json(skill_root / "manifest.json", findings)
    source_manifest = read_json(skill_root / "source-manifest.json", findings)
    for key, (folder, pattern) in COUNT_KEYS.items():
        count = len(list((skill_root / folder).glob(pattern)))
        if isinstance(manifest, dict):
            expect_equal(manifest.get(key), count, "COUNT_MISMATCH", f"manifest {key} mismatch", skill_root / "manifest.json", findings)
        if isinstance(source_manifest, dict):
            expect_equal(source_manifest.get(key), count, "COUNT_MISMATCH", f"source-manifest {key} mismatch", skill_root / "source-manifest.json", findings)

    for key, count in special_counts(skill_root, findings).items():
        if isinstance(manifest, dict):
            expect_equal(manifest.get(key), count, "COUNT_MISMATCH", f"manifest {key} mismatch", skill_root / "manifest.json", findings)
        if isinstance(source_manifest, dict):
            expect_equal(source_manifest.get(key), count, "COUNT_MISMATCH", f"source-manifest {key} mismatch", skill_root / "source-manifest.json", findings)

    if isinstance(source_manifest, dict):
        for collection, (folder, suffix) in SOURCE_MANIFEST_COLLECTIONS.items():
            entries = source_manifest.get(collection, [])
            if not isinstance(entries, list):
                findings.append(
                    Finding(
                        "ERROR",
                        "SOURCE_MANIFEST_COLLECTION_INVALID",
                        f"{collection} must be a list",
                        str(skill_root / "source-manifest.json"),
                    )
                )
                continue
            invalid_entries = [entry for entry in entries if not isinstance(entry, str) or not entry.strip()]
            if invalid_entries:
                findings.append(
                    Finding(
                        "ERROR",
                        "SOURCE_MANIFEST_COLLECTION_INVALID",
                        f"{collection} contains non-string or blank entries",
                        str(skill_root / "source-manifest.json"),
                    )
                )
                continue
            listed = {entry.strip() for entry in entries}
            actual = {
                path.stem
                for path in (skill_root / folder).glob(f"*{suffix}")
                if path.is_file()
            }
            if listed != actual:
                findings.append(
                    Finding(
                        "ERROR",
                        "SOURCE_MANIFEST_SET_MISMATCH",
                        (
                            f"{collection} must exactly match {folder} resource stems; "
                            f"missing_from_manifest={sorted(actual - listed)!r}; "
                            f"stale_in_manifest={sorted(listed - actual)!r}"
                        ),
                        str(skill_root / "source-manifest.json"),
                    )
                )


def validate_registry(skill_root: Path, findings: list[Finding]) -> None:
    registry = read_json(skill_root / "agent-registry.json", findings)
    if not isinstance(registry, dict):
        return
    seen: set[str] = set()
    for index, agent in enumerate(registry.get("agents", [])):
        if not isinstance(agent, dict):
            findings.append(Finding("ERROR", "AGENT_REGISTRY_INVALID", f"agents[{index}] is not an object", str(skill_root / "agent-registry.json")))
            continue
        agent_id = str(agent.get("agent_id", "")).strip()
        if not agent_id:
            findings.append(Finding("ERROR", "AGENT_ID_MISSING", f"agents[{index}] missing agent_id", str(skill_root / "agent-registry.json")))
            continue
        if agent_id in seen:
            findings.append(Finding("ERROR", "AGENT_ID_DUPLICATE", f"duplicate agent_id: {agent_id}", str(skill_root / "agent-registry.json")))
        seen.add(agent_id)
        prompt_path = agent.get("prompt_path")
        if not prompt_path or not (skill_root / str(prompt_path)).exists():
            findings.append(Finding("ERROR", "PROMPT_PATH_MISSING", f"{agent_id} prompt_path missing", str(skill_root / "agent-registry.json")))
        template_path = agent.get("toml_template_path")
        if agent.get("spawnable") is True and (not template_path or not (skill_root / str(template_path)).exists()):
            findings.append(Finding("ERROR", "TOML_TEMPLATE_MISSING", f"{agent_id} spawnable template missing", str(skill_root / "agent-registry.json")))


def validate_fixture_versions(skill_root: Path, version: str, findings: list[Finding]) -> None:
    fixtures_root = skill_root / "tests" / "fixtures"
    if not fixtures_root.exists():
        return
    for path in sorted(fixtures_root.glob("*/*.json")):
        payload = read_json(path, findings)
        if not isinstance(payload, dict) or "plugin_version" not in payload:
            continue
        expect_equal(
            payload.get("plugin_version"),
            version,
            "FIXTURE_VERSION_MISMATCH",
            "bundled fixture plugin_version mismatch",
            path,
            findings,
        )


def validate_router_mentions(skill_root: Path, findings: list[Finding]) -> None:
    skill_path = skill_root / "SKILL.md"
    skill_text = read_text(skill_path, findings)
    source_manifest = read_json(skill_root / "source-manifest.json", findings)
    try:
        skill_size = len(skill_path.read_bytes())
    except FileNotFoundError:
        skill_size = 0
    if skill_size > SKILL_ROUTER_MAX_BYTES:
        findings.append(
            Finding(
                "ERROR",
                "SKILL_ROUTER_TOO_LARGE",
                (
                    "SKILL.md must remain a lightweight router and lazy-load "
                    f"command/reference docs: maximum {SKILL_ROUTER_MAX_BYTES} bytes, found {skill_size}"
                ),
                str(skill_path),
            )
        )
    normalized_skill_text = re.sub(r"\s+", " ", skill_text)
    if ROUTER_ROOT_GUARD_PHRASE not in skill_text:
        findings.append(
            Finding(
                "ERROR",
                "ROUTER_ROOT_GUARD_MISSING",
                "router must require command recipes to resolve relative to the active SKILL.md directory",
                str(skill_path),
            )
        )
    for code, phrase in LAZY_LOAD_GUARD_PHRASES.items():
        if phrase not in normalized_skill_text:
            findings.append(
                Finding(
                    "ERROR",
                    code,
                    f"router missing required lazy-load/runtime downgrade guard phrase: {phrase}",
                    str(skill_path),
                )
            )
    if not isinstance(source_manifest, dict):
        return
    for command in source_manifest.get("commands", []):
        if f"commands/{command}.md" not in skill_text:
            findings.append(Finding("ERROR", "ROUTER_REFERENCE_MISSING", f"router does not mention command {command}", str(skill_path)))


def validate_docs_inventory(skill_root: Path, findings: list[Finding]) -> None:
    for folder in ("commands", "references", "loops", "templates"):
        for path in sorted((skill_root / folder).glob("*.md")):
            text = read_text(path, findings)
            match = re.match(r"\A---\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", text, re.S)
            if not match:
                continue
            frontmatter = match.group(1)
            if not (frontmatter_value(frontmatter, "summary") or frontmatter_value(frontmatter, "description")):
                findings.append(
                    Finding(
                        "WARN",
                        "DOC_FRONTMATTER_FIELD_MISSING",
                        "optional docs inventory summary or description missing",
                        str(path),
                    )
                )


def validate_codex_runtime_portability(skill_root: Path, findings: list[Finding]) -> None:
    runtime_schema_text = read_text(skill_root / "contracts" / "runtime-capability-preflight.schema.json", findings)
    runtime_template_text = read_text(skill_root / "templates" / "runtime-capability-preflight-template.md", findings)
    required_schema_tokens = (
        "host_os",
        "path_style",
        "python_invocation",
        "shell_family",
        "codex_runtime_capability_surface",
        "compute_budget",
    )
    for token in required_schema_tokens:
        if token not in runtime_schema_text:
            findings.append(
                Finding(
                    "ERROR",
                    "RUNTIME_PREFLIGHT_PORTABILITY_FIELD_MISSING",
                    f"runtime capability preflight schema missing {token}",
                    str(skill_root / "contracts" / "runtime-capability-preflight.schema.json"),
                )
            )
    required_template_tokens = ("Windows", "macOS", "PowerShell", "zsh", "sys.executable")
    for token in required_template_tokens:
        if token not in runtime_template_text:
            findings.append(
                Finding(
                    "ERROR",
                    "RUNTIME_PREFLIGHT_PORTABILITY_TEMPLATE_MISSING",
                    f"runtime capability preflight template missing {token}",
                    str(skill_root / "templates" / "runtime-capability-preflight-template.md"),
                )
            )

    for folder in ("commands", "references", "loops", "templates", "agents"):
        for path in sorted((skill_root / folder).glob("*.md")):
            text = read_text(path, findings)
            for code, term in CODEX_ONLY_BLOCKED_TERMS.items():
                if term in text:
                    findings.append(
                        Finding(
                            "ERROR",
                            code,
                            f"Codex-facing docs must not depend on non-Codex runtime term {term!r}",
                            str(path),
                        )
                    )


def main() -> int:
    args = parse_args()
    findings: list[Finding] = []
    skill_root = resolve_skill_root(args.root, findings)
    if skill_root.exists():
        validate_no_bom_bytes(skill_root, findings)
        version = validate_versions(skill_root, findings)
        validate_plugin_interface(skill_root, findings)
        validate_counts(skill_root, findings)
        validate_registry(skill_root, findings)
        validate_fixture_versions(skill_root, version, findings)
        validate_router_mentions(skill_root, findings)
        validate_docs_inventory(skill_root, findings)
        validate_codex_runtime_portability(skill_root, findings)

    if args.json:
        print(json.dumps([finding.__dict__ for finding in findings], indent=2, sort_keys=True))
    else:
        if findings:
            for finding in findings:
                print(f"{finding.level}: {finding.code}: {finding.message} {finding.path}".rstrip())
        else:
            print(f"BMAT package check passed: {skill_root}")

    return 1 if any(finding.level == "ERROR" for finding in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
