#!/usr/bin/env python3
"""Local Codex adapter for BMAT workflow bundles.

This adapter is intentionally conservative. It creates a validator-visible
bundle, optionally runs a user-provided Codex command, then validates the
collected artifacts. It never calls external services unless the caller passes a
command with --codex-command.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

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
    parser.add_argument("--dry-run", action="store_true", help="Create and validate scaffold artifacts only.")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def run(command: list[str], cwd: Path | None = None) -> int:
    return subprocess.run(command, cwd=cwd, text=True, check=False).returncode


def main() -> int:
    args = parse_args()
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

    if args.codex_command and not args.dry_run:
        status = run(args.codex_command, cwd=args.out)
        if status:
            return status
    elif args.codex_command and args.dry_run:
        print("Dry run: codex-command was recorded but not executed.")

    return run([sys.executable, str(VALIDATOR), "--bundle", str(args.out), "--check-tool-ledger"])


if __name__ == "__main__":
    raise SystemExit(main())
