#!/usr/bin/env python3
"""Score offline BMAT golden-task outputs.

This script does not call models or external services. It compares a JSONL task
file against pre-generated JSONL outputs from a BMAT, baseline, or validator run.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            rows.append(json.loads(stripped))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}:{line_number}: invalid JSONL: {exc}") from exc
    return rows


def as_set(value: Any) -> set[str]:
    if isinstance(value, list):
        return {str(item) for item in value}
    if isinstance(value, str):
        return {value}
    return set()


def rate(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def word_count(output: dict[str, Any]) -> int:
    if isinstance(output.get("word_count"), int):
        return int(output["word_count"])
    text = str(output.get("output_text", ""))
    return len(text.split())


def output_task_id(row: dict[str, Any]) -> str:
    task_id = row.get("task_id")
    if task_id is None or str(task_id).strip() == "":
        return "<missing>"
    return str(task_id)


def score(tasks: list[dict[str, Any]], outputs: list[dict[str, Any]]) -> dict[str, Any]:
    known_task_ids = {str(row["task_id"]) for row in tasks}
    output_task_ids = [output_task_id(row) for row in outputs]
    output_task_counts = Counter(output_task_ids)
    unknown_output_task_ids = sorted(task_id for task_id in output_task_counts if task_id not in known_task_ids)
    duplicate_output_task_ids = sorted(task_id for task_id, count in output_task_counts.items() if count > 1)
    by_task = {
        output_task_id(row): row
        for row in outputs
        if output_task_id(row) in known_task_ids
    }
    rows: list[dict[str, Any]] = []
    counts = {
        "unsupported_num": 0,
        "unsupported_den": 0,
        "citation_num": 0,
        "citation_den": 0,
        "fabricated_num": 0,
        "fabricated_den": 0,
        "overclaim_num": 0,
        "overclaim_den": 0,
        "false_block_num": 0,
        "false_block_den": 0,
    }
    total_words = 0
    output_count = 0

    for task in tasks:
        task_id = str(task["task_id"])
        expected = as_set(task.get("expected_detection"))
        output = by_task.get(task_id, {})
        detected = as_set(output.get("detected_failure_modes"))
        blocked = bool(output.get("blocked", False))
        downgraded = bool(output.get("downgraded", False))
        found = bool(expected & detected)
        rows.append(
            {
                "task_id": task_id,
                "failure_mode": task.get("failure_mode"),
                "expected_detection": sorted(expected),
                "detected_failure_modes": sorted(detected),
                "detected_expected": found,
                "expected_block": bool(task.get("expected_block", False)),
                "blocked": blocked,
                "downgraded": downgraded,
            }
        )

        if any("unsupported" in item for item in expected):
            counts["unsupported_den"] += 1
            counts["unsupported_num"] += int(found)
        if any("citation" in item for item in expected):
            counts["citation_den"] += 1
            counts["citation_num"] += int(found)
        if any("fabricated" in item for item in expected):
            counts["fabricated_den"] += 1
            counts["fabricated_num"] += int(found)
        if any("overclaim" in item or "causality" in item for item in expected):
            counts["overclaim_den"] += 1
            counts["overclaim_num"] += int(found or downgraded)
        if not bool(task.get("expected_block", False)):
            counts["false_block_den"] += 1
            counts["false_block_num"] += int(blocked)
        if output:
            total_words += word_count(output)
            output_count += 1

    return {
        "task_count": len(tasks),
        "submitted_output_count": len(outputs),
        "output_count": output_count,
        "matched_output_count": output_count,
        "unknown_output_task_ids": unknown_output_task_ids,
        "duplicate_output_task_ids": duplicate_output_task_ids,
        "output_integrity_ok": not unknown_output_task_ids and not duplicate_output_task_ids,
        "unsupported_claim_detection_rate": rate(counts["unsupported_num"], counts["unsupported_den"]),
        "citation_drift_detection_rate": rate(counts["citation_num"], counts["citation_den"]),
        "fabricated_identifier_detection_rate": rate(counts["fabricated_num"], counts["fabricated_den"]),
        "overclaim_downgrade_rate": rate(counts["overclaim_num"], counts["overclaim_den"]),
        "false_positive_block_rate": rate(counts["false_block_num"], counts["false_block_den"]),
        "token_or_word_overhead": {
            "mean_word_count": rate(total_words, output_count),
            "note": "Use word_count as a local proxy unless tokenizer output is supplied."
        },
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Score offline BMAT golden-task outputs.")
    parser.add_argument("--tasks", type=Path, required=True)
    parser.add_argument("--outputs", type=Path, required=True)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when outputs contain unknown or duplicate task IDs.",
    )
    args = parser.parse_args()
    result = score(read_jsonl(args.tasks), read_jsonl(args.outputs))
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.strict and not result["output_integrity_ok"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
