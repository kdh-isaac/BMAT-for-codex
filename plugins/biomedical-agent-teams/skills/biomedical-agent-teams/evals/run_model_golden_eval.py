#!/usr/bin/env python3
"""Generate model-style BMAT golden-eval outputs.

This harness defines the runtime metadata and adapter boundary for model-in-the-
loop evaluation. CI should use ``--sample-mode``. Real model or Codex execution
must be supplied explicitly through ``--adapter-command``; the harness does not
silently fake live invocation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any


EVAL_ROOT = Path(__file__).resolve().parent
SKILL_ROOT = EVAL_ROOT.parent
SCORER = EVAL_ROOT / "run_golden_eval.py"
UTF8_BOM = "\ufeff"


def strip_bom(text: str) -> str:
    return text[1:] if text.startswith(UTF8_BOM) else text


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        stripped = strip_bom(line.strip())
        if not stripped:
            continue
        try:
            row = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}:{line_number}: invalid JSONL: {exc}") from exc
        if not isinstance(row, dict):
            raise SystemExit(f"{path}:{line_number}: row must be an object")
        rows.append(row)
    return rows


def plugin_version() -> str:
    try:
        return (SKILL_ROOT / "VERSION").read_text(encoding="utf-8-sig").strip()
    except FileNotFoundError:
        return "unknown"


def prompt_hash(prompt: str) -> str:
    return "sha256:" + hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def shell_family() -> str:
    for value in (os.environ.get("SHELL"), os.environ.get("COMSPEC")):
        if not value:
            continue
        shell = value.replace("\\", "/").rstrip("/").split("/")[-1].lower()
        if shell in {"bash", "zsh", "sh", "fish", "dash"}:
            return "bash" if shell in {"sh", "dash"} else shell
        if shell in {"powershell", "powershell.exe", "pwsh", "pwsh.exe"}:
            return "powershell"
        if shell in {"cmd", "cmd.exe"}:
            return "cmd"
    return "unknown"


def sample_output_for_task(task: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    expected = task.get("expected_detection", [])
    expected_modes = [str(item) for item in expected] if isinstance(expected, list) else []
    expected_block = bool(task.get("expected_block", False))
    prompt = str(task.get("prompt", ""))
    return {
        "task_id": str(task.get("task_id")),
        "plugin_version": plugin_version(),
        "runtime": args.runtime,
        "host_os": platform.system() or "unknown",
        "shell_family": shell_family(),
        "python_invocation": sys.executable,
        "model_name": args.model,
        "prompt_hash": prompt_hash(prompt),
        "detected_failure_modes": expected_modes if expected_block else [],
        "blocked": expected_block,
        "downgraded": expected_block,
        "output_text": (
            "Sample-mode BMAT output. This row is generated from public synthetic "
            "golden-task expectations and is not a live model invocation."
        ),
    }


def base_output_for_task(task: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    prompt = str(task.get("prompt", ""))
    return {
        "task_id": str(task.get("task_id")),
        "plugin_version": plugin_version(),
        "runtime": args.runtime,
        "host_os": platform.system() or "unknown",
        "shell_family": shell_family(),
        "python_invocation": sys.executable,
        "model_name": args.model,
        "prompt_hash": prompt_hash(prompt),
    }


def parse_adapter_row(stdout: str, task: dict[str, Any]) -> dict[str, Any]:
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    if not lines:
        raise SystemExit(f"{task.get('task_id')}: adapter produced no JSON output")
    try:
        row = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{task.get('task_id')}: adapter output is not valid JSON: {exc}") from exc
    if not isinstance(row, dict):
        raise SystemExit(f"{task.get('task_id')}: adapter output must be a JSON object")
    return row


def normalize_adapter_row(row: dict[str, Any], task: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    normalized = base_output_for_task(task, args)
    normalized.update(row)
    normalized["task_id"] = str(normalized.get("task_id") or task.get("task_id"))

    modes = normalized.get("detected_failure_modes", [])
    if not isinstance(modes, list) or not all(isinstance(item, str) for item in modes):
        raise SystemExit(f"{task.get('task_id')}: detected_failure_modes must be a list of strings")
    if not isinstance(normalized.get("blocked"), bool):
        raise SystemExit(f"{task.get('task_id')}: blocked must be boolean")
    if "downgraded" in normalized and not isinstance(normalized.get("downgraded"), bool):
        raise SystemExit(f"{task.get('task_id')}: downgraded must be boolean when present")
    return normalized


def adapter_output_for_task(task: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    if not args.adapter_command:
        raise SystemExit("Internal error: adapter_output_for_task called without --adapter-command")
    command = shlex.split(args.adapter_command)
    if not command:
        raise SystemExit("--adapter-command must not be empty")

    task_json = json.dumps(task, sort_keys=True)
    env = os.environ.copy()
    env.update(
        {
            "BMAT_TASK_JSON": task_json,
            "BMAT_TASK_ID": str(task.get("task_id")),
            "BMAT_ALIAS": args.alias,
            "BMAT_RUNTIME": args.runtime,
            "BMAT_MODEL": args.model,
            "BMAT_PLUGIN_VERSION": plugin_version(),
        }
    )
    try:
        result = subprocess.run(
            command,
            input=task_json + "\n",
            text=True,
            capture_output=True,
            check=False,
            timeout=args.adapter_timeout_sec,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        raise SystemExit(
            f"{task.get('task_id')}: adapter timed out after {args.adapter_timeout_sec} seconds"
        ) from exc
    if result.returncode != 0:
        stderr = result.stderr.strip()
        detail = f": {stderr}" if stderr else ""
        raise SystemExit(f"{task.get('task_id')}: adapter exited {result.returncode}{detail}")
    row = parse_adapter_row(result.stdout, task)
    return normalize_adapter_row(row, task, args)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run BMAT model-style golden eval harness.")
    parser.add_argument("--tasks", type=Path, required=True)
    parser.add_argument("--alias", default="evidence-audit-team")
    parser.add_argument("--runtime", default="codex")
    parser.add_argument("--model", default="sample-model")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--sample-mode", action="store_true", help="Generate deterministic sample outputs for CI.")
    parser.add_argument(
        "--adapter-command",
        help=(
            "Command that receives one golden task JSON object on stdin and writes one output "
            "JSON object on stdout. Required for real model/Codex invocation when --sample-mode "
            "is not used."
        ),
    )
    parser.add_argument("--adapter-timeout-sec", type=float, default=120.0)
    parser.add_argument("--then-score", action="store_true")
    parser.add_argument("--gate", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.runtime != "codex":
        raise SystemExit("Only --runtime codex is supported by this harness.")
    if args.sample_mode and args.adapter_command:
        raise SystemExit("Use either --sample-mode or --adapter-command, not both.")
    if not args.sample_mode and not args.adapter_command:
        raise SystemExit("Use --sample-mode for CI or provide --adapter-command for live model/Codex evaluation.")
    tasks = read_jsonl(args.tasks)
    if args.sample_mode:
        outputs = [sample_output_for_task(task, args) for task in tasks]
    else:
        outputs = [adapter_output_for_task(task, args) for task in tasks]
    write_jsonl(args.out, outputs)
    mode = "sample" if args.sample_mode else "adapter"
    print(f"BMAT model golden-eval {mode} outputs written: {args.out}")

    if not args.then_score:
        return 0
    command = [
        sys.executable,
        str(SCORER),
        "--tasks",
        str(args.tasks),
        "--outputs",
        str(args.out),
        "--strict",
    ]
    if args.gate:
        command.append("--gate")
    result = subprocess.run(command, text=True, check=False)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
