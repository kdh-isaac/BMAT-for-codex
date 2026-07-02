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
import re
from typing import Any


TASK_ID_RE = re.compile(r"^GT-\d{3}$")
MIN_DEFAULT_TASKS = 10
MAX_DEFAULT_TASKS = 30
GATE_TAGS = ("pmid_drift", "contradiction", "overclaim")
CATEGORY_TERMS = {
    "unsupported": ("unsupported",),
    "citation": ("citation", "pmid", "doi", "fabricated_identifier"),
    "fabricated": ("fabricated", "fabrication"),
    "overclaim": (
        "overclaim",
        "causality",
        "clinical_overreach",
        "survival_overclaim",
        "assay_scope_overclaim",
        "species_scope_overclaim",
        "bulk_to_cell_intrinsic_overclaim",
        "evidence_quality_overclaim",
    ),
    "pmid_drift": ("pmid", "citation_drift", "fabricated_identifier"),
    "contradiction": ("contradiction", "negative_evidence"),
}
UTF8_BOM = "\ufeff"


def strip_bom(text: str) -> str:
    if text.startswith(UTF8_BOM):
        return text[len(UTF8_BOM) :]
    return text


def read_text_file(path: Path) -> str:
    return strip_bom(path.read_text(encoding="utf-8-sig"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(read_text_file(path).splitlines(), start=1):
        stripped = strip_bom(line.strip())
        if not stripped:
            continue
        try:
            row = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path}:{line_number}: invalid JSONL: {exc}") from exc
        if not isinstance(row, dict):
            raise SystemExit(f"{path}:{line_number}: JSONL row must be an object")
        rows.append(row)
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


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _list_of_nonempty_strings(value: Any) -> bool:
    return isinstance(value, list) and all(_is_nonempty_string(item) for item in value)


def _validate_task_row(row: dict[str, Any], index: int) -> list[str]:
    prefix = f"tasks[{index}]"
    errors: list[str] = []
    for key in ("task_id", "failure_mode", "prompt", "expected_detection", "expected_block", "tags"):
        if key not in row:
            errors.append(f"{prefix}: missing required field {key!r}")

    task_id = row.get("task_id")
    if not _is_nonempty_string(task_id) or not TASK_ID_RE.match(str(task_id)):
        errors.append(f"{prefix}: task_id must match GT-###")
    for key in ("failure_mode", "prompt"):
        if key in row and not _is_nonempty_string(row.get(key)):
            errors.append(f"{prefix}: {key} must be a non-empty string")
    if "expected_detection" in row and not _list_of_nonempty_strings(row.get("expected_detection")):
        errors.append(f"{prefix}: expected_detection must be a list of non-empty strings")
    if "expected_block" in row and not isinstance(row.get("expected_block"), bool):
        errors.append(f"{prefix}: expected_block must be a boolean")
    if "tags" in row and not _list_of_nonempty_strings(row.get("tags")):
        errors.append(f"{prefix}: tags must be a list of non-empty strings")

    expected = row.get("expected_detection", [])
    tags = row.get("tags", [])
    expected_block = row.get("expected_block")
    if isinstance(expected, list) and expected_block is True and not expected:
        errors.append(f"{prefix}: blocking tasks must declare at least one expected_detection")
    if isinstance(expected, list) and expected_block is False and expected:
        errors.append(f"{prefix}: non-blocking negative controls must not declare expected_detection")
    if isinstance(expected, list) and isinstance(tags, list):
        expected_set = {str(item) for item in expected}
        for tag in GATE_TAGS:
            if tag in tags and not expected_for_category(tag, expected_set):
                errors.append(f"{prefix}: tag {tag!r} requires a matching expected_detection category")
    return errors


def _validate_output_row(row: dict[str, Any], index: int) -> list[str]:
    prefix = f"outputs[{index}]"
    errors: list[str] = []
    for key in ("task_id", "detected_failure_modes", "blocked"):
        if key not in row:
            errors.append(f"{prefix}: missing required field {key!r}")

    task_id = row.get("task_id")
    if not _is_nonempty_string(task_id) or not TASK_ID_RE.match(str(task_id)):
        errors.append(f"{prefix}: task_id must match GT-###")
    if "detected_failure_modes" in row and not _list_of_nonempty_strings(row.get("detected_failure_modes")):
        errors.append(f"{prefix}: detected_failure_modes must be a list of non-empty strings")
    if "blocked" in row and not isinstance(row.get("blocked"), bool):
        errors.append(f"{prefix}: blocked must be a boolean")
    if "downgraded" in row and not isinstance(row.get("downgraded"), bool):
        errors.append(f"{prefix}: downgraded must be a boolean when present")
    if "output_text" in row and not isinstance(row.get("output_text"), str):
        errors.append(f"{prefix}: output_text must be a string when present")
    if "word_count" in row:
        word_count_value = row.get("word_count")
        if not isinstance(word_count_value, int) or word_count_value < 0:
            errors.append(f"{prefix}: word_count must be a non-negative integer when present")
    return errors


def validate_task_rows(rows: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for index, row in enumerate(rows, start=1):
        errors.extend(_validate_task_row(row, index))
        task_id = str(row.get("task_id", ""))
        if task_id in seen:
            errors.append(f"tasks[{index}]: duplicate task_id {task_id!r}")
        if task_id:
            seen.add(task_id)
    return errors


def validate_output_rows(rows: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for index, row in enumerate(rows, start=1):
        errors.extend(_validate_output_row(row, index))
    return errors


def task_passed(expected: set[str], detected: set[str], downgraded: bool) -> bool:
    if expected & detected:
        return True
    return downgraded and any("overclaim" in item for item in expected)


def expected_for_category(category: str, expected: set[str]) -> set[str]:
    terms = CATEGORY_TERMS[category]
    return {
        item
        for item in expected
        if any(term in item for term in terms)
    }


def category_passed(category: str, expected: set[str], detected: set[str], downgraded: bool) -> bool:
    relevant_expected = expected_for_category(category, expected)
    if not relevant_expected:
        return False
    if relevant_expected & detected:
        return True
    return category == "overclaim" and downgraded


def score(tasks: list[dict[str, Any]], outputs: list[dict[str, Any]]) -> dict[str, Any]:
    known_task_ids = {
        str(row["task_id"])
        for row in tasks
        if _is_nonempty_string(row.get("task_id"))
    }
    output_task_ids = [output_task_id(row) for row in outputs]
    output_task_counts = Counter(output_task_ids)
    unknown_output_task_ids = sorted(task_id for task_id in output_task_counts if task_id not in known_task_ids)
    duplicate_output_task_ids = sorted(task_id for task_id, count in output_task_counts.items() if count > 1)
    missing_output_task_ids = sorted(task_id for task_id in known_task_ids if task_id not in output_task_counts)
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
    tag_counts = {tag: {"num": 0, "den": 0} for tag in GATE_TAGS}
    total_words = 0
    output_count = 0

    for task in tasks:
        task_id = str(task.get("task_id", "<missing>"))
        if task_id not in known_task_ids:
            continue
        expected = as_set(task.get("expected_detection"))
        tags = as_set(task.get("tags"))
        output = by_task.get(task_id, {})
        detected = as_set(output.get("detected_failure_modes"))
        blocked = bool(output.get("blocked", False))
        downgraded = bool(output.get("downgraded", False))
        found = task_passed(expected, detected, downgraded) if expected else not blocked
        rows.append(
            {
                "task_id": task_id,
                "failure_mode": task.get("failure_mode"),
                "tags": sorted(tags),
                "expected_detection": sorted(expected),
                "detected_failure_modes": sorted(detected),
                "detected_expected": found,
                "expected_block": bool(task.get("expected_block", False)),
                "blocked": blocked,
                "downgraded": downgraded,
            }
        )

        if expected_for_category("unsupported", expected):
            counts["unsupported_den"] += 1
            counts["unsupported_num"] += int(category_passed("unsupported", expected, detected, downgraded))
        if expected_for_category("citation", expected):
            counts["citation_den"] += 1
            counts["citation_num"] += int(category_passed("citation", expected, detected, downgraded))
        if expected_for_category("fabricated", expected):
            counts["fabricated_den"] += 1
            counts["fabricated_num"] += int(category_passed("fabricated", expected, detected, downgraded))
        if expected_for_category("overclaim", expected):
            counts["overclaim_den"] += 1
            counts["overclaim_num"] += int(category_passed("overclaim", expected, detected, downgraded))
        for tag in GATE_TAGS:
            if tag in tags:
                tag_counts[tag]["den"] += 1
                tag_counts[tag]["num"] += int(category_passed(tag, expected, detected, downgraded))
        if not bool(task.get("expected_block", False)):
            counts["false_block_den"] += 1
            counts["false_block_num"] += int(blocked)
        if output:
            total_words += word_count(output)
            output_count += 1

    tag_rates = {
        tag: rate(values["num"], values["den"])
        for tag, values in tag_counts.items()
    }
    return {
        "task_count": len(tasks),
        "submitted_output_count": len(outputs),
        "output_count": output_count,
        "matched_output_count": output_count,
        "unknown_output_task_ids": unknown_output_task_ids,
        "duplicate_output_task_ids": duplicate_output_task_ids,
        "missing_output_task_ids": missing_output_task_ids,
        "output_integrity_ok": not unknown_output_task_ids and not duplicate_output_task_ids and not missing_output_task_ids,
        "unsupported_claim_detection_rate": rate(counts["unsupported_num"], counts["unsupported_den"]),
        "citation_drift_detection_rate": rate(counts["citation_num"], counts["citation_den"]),
        "fabricated_identifier_detection_rate": rate(counts["fabricated_num"], counts["fabricated_den"]),
        "overclaim_downgrade_rate": rate(counts["overclaim_num"], counts["overclaim_den"]),
        "pmid_drift_detection_rate": tag_rates["pmid_drift"],
        "contradiction_detection_rate": tag_rates["contradiction"],
        "tag_detection_rates": tag_rates,
        "false_positive_block_rate": rate(counts["false_block_num"], counts["false_block_den"]),
        "token_or_word_overhead": {
            "mean_word_count": rate(total_words, output_count),
            "note": "Use word_count as a local proxy unless tokenizer output is supplied.",
        },
        "rows": rows,
    }


def _rate_below(value: float | None, threshold: float) -> bool:
    return value is None or value < threshold


def evaluate_gate(
    result: dict[str, Any],
    *,
    min_task_count: int,
    max_task_count: int,
    min_pmid_drift_rate: float,
    min_contradiction_rate: float,
    min_overclaim_rate: float,
    max_false_positive_block_rate: float,
) -> dict[str, Any]:
    failures: list[str] = []
    task_count = int(result.get("task_count", 0))
    if not result.get("schema_valid", False):
        failures.append("schema validation failed")
    if not result.get("output_integrity_ok", False):
        failures.append("output integrity failed")
    if task_count < min_task_count or task_count > max_task_count:
        failures.append(f"task_count must be between {min_task_count} and {max_task_count}, found {task_count}")
    if _rate_below(result.get("pmid_drift_detection_rate"), min_pmid_drift_rate):
        failures.append("pmid_drift_detection_rate below threshold")
    if _rate_below(result.get("contradiction_detection_rate"), min_contradiction_rate):
        failures.append("contradiction_detection_rate below threshold")
    if _rate_below(result.get("overclaim_downgrade_rate"), min_overclaim_rate):
        failures.append("overclaim_downgrade_rate below threshold")

    false_positive_rate = result.get("false_positive_block_rate")
    if false_positive_rate is None:
        failures.append("false_positive_block_rate missing negative-control denominator")
    elif false_positive_rate > max_false_positive_block_rate:
        failures.append("false_positive_block_rate above threshold")

    return {
        "passed": not failures,
        "failures": failures,
        "thresholds": {
            "min_task_count": min_task_count,
            "max_task_count": max_task_count,
            "min_pmid_drift_detection_rate": min_pmid_drift_rate,
            "min_contradiction_detection_rate": min_contradiction_rate,
            "min_overclaim_downgrade_rate": min_overclaim_rate,
            "max_false_positive_block_rate": max_false_positive_block_rate,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Score offline BMAT golden-task outputs.")
    parser.add_argument("--tasks", type=Path, required=True)
    parser.add_argument("--outputs", type=Path, required=True)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when schema validation or output integrity fails.",
    )
    parser.add_argument(
        "--gate",
        action="store_true",
        help="Exit non-zero when the golden-eval release gate fails.",
    )
    parser.add_argument("--min-task-count", type=int, default=MIN_DEFAULT_TASKS)
    parser.add_argument("--max-task-count", type=int, default=MAX_DEFAULT_TASKS)
    parser.add_argument("--min-pmid-drift-rate", type=float, default=1.0)
    parser.add_argument("--min-contradiction-rate", type=float, default=1.0)
    parser.add_argument("--min-overclaim-rate", type=float, default=1.0)
    parser.add_argument("--max-false-positive-block-rate", type=float, default=0.0)
    args = parser.parse_args()

    tasks = read_jsonl(args.tasks)
    outputs = read_jsonl(args.outputs)
    schema_errors = validate_task_rows(tasks) + validate_output_rows(outputs)
    result = score(tasks, outputs)
    result["schema_valid"] = not schema_errors
    result["schema_errors"] = schema_errors

    if args.gate:
        result["gate"] = evaluate_gate(
            result,
            min_task_count=args.min_task_count,
            max_task_count=args.max_task_count,
            min_pmid_drift_rate=args.min_pmid_drift_rate,
            min_contradiction_rate=args.min_contradiction_rate,
            min_overclaim_rate=args.min_overclaim_rate,
            max_false_positive_block_rate=args.max_false_positive_block_rate,
        )

    print(json.dumps(result, indent=2, sort_keys=True))
    if args.gate and not result["gate"]["passed"]:
        return 1
    if args.strict and (schema_errors or not result["output_integrity_ok"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
