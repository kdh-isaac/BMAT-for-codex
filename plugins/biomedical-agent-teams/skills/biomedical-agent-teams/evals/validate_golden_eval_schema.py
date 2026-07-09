#!/usr/bin/env python3
"""Validate BMAT golden-task and output JSONL shape.

This wrapper is intentionally dependency-free and reuses the local golden eval
schema checks from run_golden_eval.py.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from run_golden_eval import read_jsonl, validate_output_rows, validate_task_rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate BMAT golden eval JSONL schema.")
    parser.add_argument("--tasks", type=Path, required=True)
    parser.add_argument("--outputs", type=Path)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable validation output.")
    args = parser.parse_args()

    errors = validate_task_rows(read_jsonl(args.tasks))
    if args.outputs is not None:
        errors.extend(validate_output_rows(read_jsonl(args.outputs)))

    payload = {"schema_valid": not errors, "schema_errors": errors}
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif errors:
        for error in errors:
            print(f"ERROR: {error}")
    else:
        print("Golden eval schema validation passed.")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
