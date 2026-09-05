#!/usr/bin/env python3
"""Run dependency-free BMAT package smoke checks."""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Check:
    name: str
    command: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run BMAT smoke checks without pytest.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="BMAT skill root, plugin root, marketplace root, or installed cache root.",
    )
    parser.add_argument("--skip-golden", action="store_true", help="Skip offline golden-task sample scoring.")
    parser.add_argument("--release", action="store_true", help="Require schema dependencies and release-grade fixture validation.")
    return parser.parse_args()


def resolve_skill_root(root: Path) -> Path:
    root = root.resolve()
    candidates = [
        root,
        root / "skills" / "biomedical-agent-teams",
        root / "plugins" / "biomedical-agent-teams" / "skills" / "biomedical-agent-teams",
    ]
    for candidate in candidates:
        if (candidate / "SKILL.md").exists() and (candidate / "VERSION").exists():
            return candidate
    raise SystemExit(f"ERROR: could not resolve BMAT skill root from {root}")


def run_check(check: Check) -> bool:
    print(f"\n## {check.name}")
    result = subprocess.run(check.command, text=True, capture_output=True)
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip(), file=sys.stderr)
    if result.returncode == 0:
        print(f"PASS: {check.name}")
        return True
    print(f"FAIL: {check.name} exited {result.returncode}", file=sys.stderr)
    return False


def checks_for(skill_root: Path, skip_golden: bool, release: bool = False) -> list[Check]:
    scripts = skill_root / "scripts"
    fixtures = skill_root / "tests" / "fixtures"
    evals = skill_root / "evals"
    checks = [
        Check(
            "package layout",
            [sys.executable, str(scripts / "bmat_package_check.py"), "--root", str(skill_root)],
        ),
        Check(
            "valid loop policy fixture",
            [
                sys.executable,
                str(scripts / "bmat_loop_check.py"),
                "--loop-state",
                str(fixtures / "loop_check_valid" / "loop_state.json"),
            ],
        ),
        Check(
            "valid full-protocol bundle fixture",
            [
                sys.executable,
                str(scripts / "bmat_validate.py"),
                "--bundle",
                str(fixtures / "valid_full_protocol_bundle"),
                *(["--release"] if release else []),
            ],
        ),
    ]
    if not skip_golden:
        checks.append(
            Check(
                "offline golden eval sample",
                [
                    sys.executable,
                    str(evals / "run_golden_eval.py"),
                    "--tasks",
                    str(evals / "golden_tasks.jsonl"),
                    "--outputs",
                    str(evals / "sample_outputs.jsonl"),
                    "--strict",
                    *(["--gate"] if release else []),
                ],
            )
        )
    if release:
        checks.insert(0, Check("release schema dependency", [sys.executable, "-c", "import jsonschema"]))
    return checks


def main() -> int:
    args = parse_args()
    skill_root = resolve_skill_root(args.root)
    results = [run_check(check) for check in checks_for(skill_root, args.skip_golden, args.release)]
    if all(results):
        print("\nBMAT self-test passed: release_passed." if args.release else "\nBMAT self-test passed: smoke_passed; release gates were not requested.")
        return 0
    print("\nBMAT self-test failed.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
