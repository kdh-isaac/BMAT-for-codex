#!/usr/bin/env python3
"""Local Codex adapter for BMAT workflow bundles.

This adapter is intentionally conservative. It creates a validator-visible
bundle, optionally runs a user-provided Codex command, captures command output,
records collected artifacts, then validates the bundle. It never calls external
services unless the caller passes a command with --codex-command.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import bmat_run


SKILL_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = SKILL_ROOT / "scripts" / "bmat_validate.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Orchestrate a local BMAT Codex run bundle.")
    parser.add_argument("--alias", choices=bmat_run.bmat_init_bundle.WORKFLOWS, required=True)
    parser.add_argument("--mode", choices=bmat_run.bmat_init_bundle.MODES, default="standard")
    parser.add_argument("--tier", choices=("compact", "full"), default="compact")
    parser.add_argument("--track", choices=bmat_run.OMICS_TRACKS)
    parser.add_argument("--question", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--domain-pack", choices=bmat_run.available_domain_packs(), default="generic-biomedical")
    parser.add_argument("--codex-command", nargs=argparse.REMAINDER, help="Optional Codex command to run after scaffold creation.")
    parser.add_argument("--command-timeout-seconds", type=int, default=120, help="Timeout for the optional Codex command.")
    parser.add_argument("--validator-timeout-seconds", type=int, default=60, help="Timeout for the validator command.")
    parser.add_argument("--dry-run", action="store_true", help="Create and validate scaffold artifacts only.")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def text_or_empty(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def run_capture(command: list[str], cwd: Path | None = None, timeout_seconds: int | None = None) -> dict[str, Any]:
    try:
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False, timeout=timeout_seconds)
        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        stderr = text_or_empty(exc.stderr)
        stderr += f"\nCommand timed out after {timeout_seconds} seconds.\n"
        return {
            "returncode": 124,
            "stdout": text_or_empty(exc.stdout),
            "stderr": stderr,
            "timed_out": True,
        }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect_artifacts(bundle: Path) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    for path in sorted(bundle.rglob("*")):
        if not path.is_file():
            continue
        if any(part in {"__pycache__", ".pytest_cache"} for part in path.parts):
            continue
        stat = path.stat()
        artifacts.append(
            {
                "path": path.relative_to(bundle).as_posix(),
                "size_bytes": stat.st_size,
                "sha256": sha256_file(path),
            }
        )
    return artifacts


def main() -> int:
    args = parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    run_args = argparse.Namespace(
        alias=args.alias,
        mode=args.mode,
        tier=args.tier,
        track=args.track,
        question=args.question,
        out=args.out,
        domain_pack=args.domain_pack,
        dry_run=True,
        validate=False,
        export="none",
        force=args.force,
    )
    payloads = bmat_run.bmat_init_bundle.build_payloads(args.alias, args.mode, args.question, args.out)
    bmat_run.enrich_payloads(payloads, run_args)
    bmat_run.write_payloads(payloads, args.out, args.force)
    print(f"BMAT Codex adapter scaffold created: {args.out.resolve()}")

    adapter_record: dict[str, Any] = {
        "schema_version": "1.0",
        "adapter_id": f"adapter-{payloads['run_state.json']['run_id']}",
        "created_at": utc_now(),
        "workflow_run_id": payloads["run_state.json"]["run_id"],
        "alias": args.alias,
        "mode": args.mode,
        "tier": args.tier,
        "track": bmat_run.selected_omics_track(args),
        "domain_pack": args.domain_pack,
        "dry_run": bool(args.dry_run),
        "codex_command": args.codex_command or [],
        "command_timeout_seconds": args.command_timeout_seconds,
        "validator_timeout_seconds": args.validator_timeout_seconds,
        "command_executed": False,
        "command_exit": None,
        "command_timed_out": False,
        "validator_exit": None,
        "validator_timed_out": False,
    }

    command_exit = 0
    if args.codex_command and not args.dry_run:
        command_result = run_capture(args.codex_command, cwd=args.out, timeout_seconds=args.command_timeout_seconds)
        command_exit = command_result["returncode"]
        adapter_record["command_executed"] = True
        adapter_record["command_exit"] = command_exit
        adapter_record["command_timed_out"] = command_result["timed_out"]
        (args.out / "adapter_command_stdout.md").write_text(command_result["stdout"], encoding="utf-8")
        (args.out / "adapter_command_stderr.log").write_text(command_result["stderr"], encoding="utf-8")
    elif args.codex_command and args.dry_run:
        print("Dry run: codex-command was recorded but not executed.")
        (args.out / "adapter_command_stdout.md").write_text("Dry run: command not executed.\n", encoding="utf-8")
        (args.out / "adapter_command_stderr.log").write_text("", encoding="utf-8")

    validator_result = run_capture(
        [sys.executable, str(VALIDATOR), "--bundle", str(args.out), "--check-tool-ledger"],
        timeout_seconds=args.validator_timeout_seconds,
    )
    adapter_record["validator_exit"] = validator_result["returncode"]
    adapter_record["validator_timed_out"] = validator_result["timed_out"]
    (args.out / "adapter_validator_stdout.log").write_text(validator_result["stdout"], encoding="utf-8")
    (args.out / "adapter_validator_stderr.log").write_text(validator_result["stderr"], encoding="utf-8")
    write_json(args.out / "adapter_run.json", adapter_record)

    manifest_path = args.out / "adapter_artifact_manifest.json"
    if manifest_path.exists():
        manifest_path.unlink()
    write_json(
        manifest_path,
        {
            "schema_version": "1.0",
            "generated_at": utc_now(),
            "artifacts": collect_artifacts(args.out),
        },
    )

    if command_exit:
        return command_exit
    return validator_result["returncode"]


if __name__ == "__main__":
    raise SystemExit(main())
