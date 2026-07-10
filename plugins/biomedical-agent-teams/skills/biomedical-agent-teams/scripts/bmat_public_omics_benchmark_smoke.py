#!/usr/bin/env python3
"""Run metadata-only public-omics benchmark smokes for BMAT.

This harness intentionally does not download raw public data. It locks official
dataset URLs/accessions into the source corpus and omics manifest, then runs the
local bundle validator. Use it as a lightweight release gate for the public
benchmark cases maintained for the BMAT v1.2.0 release gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = SKILL_ROOT / "evals" / "public_omics_benchmark_cases.jsonl"
RUNNER = SKILL_ROOT / "scripts" / "bmat_run.py"
VALIDATOR = SKILL_ROOT / "scripts" / "bmat_validate.py"
BUNDLE_MANIFEST = SKILL_ROOT / "scripts" / "bmat_bundle_manifest.py"


def local_date() -> str:
    return datetime.now().astimezone().date().isoformat()


def load_cases(path: Path = CASES_PATH) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        case = json.loads(line)
        if "case_id" not in case or "track" not in case:
            raise ValueError(f"{path}:{line_number} missing case_id or track")
        cases.append(case)
    return cases


def select_cases(all_cases: list[dict[str, Any]], requested: list[str]) -> list[dict[str, Any]]:
    if not requested:
        return all_cases
    by_id = {str(case["case_id"]): case for case in all_cases}
    missing = [case_id for case_id in requested if case_id not in by_id]
    if missing:
        available = ", ".join(sorted(by_id))
        raise ValueError(f"unknown benchmark case(s): {', '.join(missing)}; available: {available}")
    return [by_id[case_id] for case_id in requested]


def deep_update(target: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            deep_update(target[key], value)
        else:
            target[key] = value
    return target


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_corpus_for_case(
    case: dict[str, Any],
    retrieval_date: str,
    run_state: dict[str, Any],
    snapshot_ref: str,
    snapshot_sha256: str,
) -> dict[str, Any]:
    case_id = str(case["case_id"])
    created_at = str(run_state.get("created_at", f"{retrieval_date}T00:00:00Z"))
    excerpt = str(case.get("scope_note", "Official public metadata record."))
    return {
        "schema_version": "2.0",
        "corpus_id": f"corpus-public-benchmark-{case_id}",
        "plugin_version": str(run_state.get("plugin_version", "unknown")),
        "workflow_run_id": str(run_state.get("run_id", "unknown")),
        "created_at": created_at,
        "query_or_origin": str(case["question"]),
        "sources": [
            {
                "source_id": case_id,
                "source_type": str(case.get("source_type", "accession")),
                "identifier": str(case.get("identifier", case_id)),
                "title_or_name": str(case.get("title", case_id)),
                "version_or_retrieval_date": retrieval_date,
                "retrieved_at": created_at,
                "query_or_origin": str(case.get("official_url", "")),
                "inclusion_status": "included",
                "claim_use": "public benchmark metadata lock; raw data not downloaded",
                "checked_by": "bmat_public_omics_benchmark_smoke",
                "limitations": str(case.get("limitations", "Metadata-only smoke.")),
                "evidence_spans": [
                    {
                        "span_id": f"{case_id}-official-record",
                        "source_id": case_id,
                        "source_snapshot_ref": snapshot_ref,
                        "source_snapshot_sha256": snapshot_sha256,
                        "locator": str(case.get("official_url", "")),
                        "section": "recorded public metadata",
                        "paragraph_or_table": "metadata record",
                        "sentence_or_cell": "scope_note",
                        "evidence_text_sha256": hashlib.sha256(excerpt.encode("utf-8")).hexdigest(),
                        "short_evidence_excerpt": excerpt,
                        "retrieved_at": created_at,
                        "extraction_actor": "bmat_public_omics_benchmark_smoke",
                        "limitations": str(case.get("limitations", "Metadata-only smoke.")),
                    }
                ],
            }
        ],
    }


def final_text_for_case(case: dict[str, Any]) -> str:
    checks = "\n".join(f"- {item}" for item in case.get("expected_checks", []))
    return (
        "# BMAT public omics benchmark smoke\n\n"
        f"- case_id: `{case['case_id']}`\n"
        f"- track: `{case['track']}`\n"
        "- raw_data_downloaded: `false`\n"
        "- label: `Contract-shaped artifact bundle`\n\n"
        "## Contract Locks\n\n"
        f"{checks}\n\n"
        "This smoke records public metadata in source_corpus.json and omics_run_manifest.json only. "
        "It does not perform biological interpretation or raw-data analysis.\n"
    )


def apply_case_metadata(bundle: Path, case: dict[str, Any], retrieval_date: str) -> None:
    run_state = read_json(bundle / "run_state.json")
    manifest = read_json(bundle / "omics_run_manifest.json")
    deep_update(manifest, case.get("manifest_overlay", {}))
    manifest["workflow_run_id"] = run_state.get("run_id", manifest.get("workflow_run_id", ""))
    write_json(bundle / "omics_run_manifest.json", manifest)

    case_id = str(case["case_id"])
    snapshot_ref = f"evidence/{case_id}-official-metadata.json"
    snapshot_path = bundle / snapshot_ref
    snapshot = {
        "case_id": case_id,
        "title": case.get("title", case_id),
        "identifier": case.get("identifier", case_id),
        "official_url": case.get("official_url", ""),
        "retrieval_date": retrieval_date,
        "scope_note": case.get("scope_note", "Official public metadata record."),
        "limitations": case.get("limitations", "Metadata-only smoke."),
        "expected_checks": case.get("expected_checks", []),
        "raw_data_downloaded": False,
    }
    write_json(snapshot_path, snapshot)
    write_json(
        bundle / "source_corpus.json",
        source_corpus_for_case(case, retrieval_date, run_state, snapshot_ref, sha256_file(snapshot_path)),
    )
    write_text(bundle / "final.md", final_text_for_case(case))


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False)


def run_case(case: dict[str, Any], out_root: Path, validate: bool, force: bool, retrieval_date: str) -> dict[str, Any]:
    case_id = str(case["case_id"])
    bundle = out_root / case_id
    command = [
        sys.executable,
        str(RUNNER),
        "--alias",
        "omics-analysis-team",
        "--mode",
        "run",
        "--tier",
        "full",
        "--track",
        str(case["track"]),
        "--question",
        str(case["question"]),
        "--out",
        str(bundle),
        "--dry-run",
    ]
    if force:
        command.append("--force")

    runner_result = run_command(command)
    bundle.mkdir(parents=True, exist_ok=True)
    write_text(bundle / "benchmark_runner_stdout.log", runner_result.stdout)
    write_text(bundle / "benchmark_runner_stderr.log", runner_result.stderr)

    validator_exit: int | None = None
    manifest_exit: int | None = None
    validator_stdout = ""
    validator_stderr = ""
    if runner_result.returncode == 0:
        apply_case_metadata(bundle, case, retrieval_date)
        manifest_result = run_command([sys.executable, str(BUNDLE_MANIFEST), "--bundle", str(bundle)])
        manifest_exit = manifest_result.returncode
        if manifest_result.returncode != 0:
            validator_exit = manifest_result.returncode
            validator_stdout = manifest_result.stdout
            validator_stderr = manifest_result.stderr
        elif validate:
            validator_result = run_command(
                [sys.executable, str(VALIDATOR), "--bundle", str(bundle), "--check-tool-ledger", "--json"]
            )
            validator_exit = validator_result.returncode
            validator_stdout = validator_result.stdout
            validator_stderr = validator_result.stderr
            write_text(bundle / "benchmark_validator_stdout.json", validator_stdout)
            write_text(bundle / "benchmark_validator_stderr.log", validator_stderr)

    status = "pass"
    if runner_result.returncode != 0:
        status = "runner-failed"
    elif manifest_exit != 0:
        status = "manifest-failed"
    elif validate and validator_exit != 0:
        status = "validator-failed"

    return {
        "case_id": case_id,
        "track": case["track"],
        "bundle": str(bundle.resolve()),
        "official_url": case.get("official_url", ""),
        "raw_data_downloaded": False,
        "runner_exit": runner_result.returncode,
        "manifest_exit": manifest_exit,
        "validator_exit": validator_exit,
        "status": status,
        "expected_checks": case.get("expected_checks", []),
        "validator_stdout_bytes": len(validator_stdout.encode("utf-8")),
        "validator_stderr_bytes": len(validator_stderr.encode("utf-8")),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run BMAT metadata-only public omics benchmark smokes.")
    parser.add_argument("--cases", type=Path, default=CASES_PATH, help="JSONL benchmark case file.")
    parser.add_argument("--case", action="append", default=[], help="Case ID to run; repeatable. Defaults to all.")
    parser.add_argument("--out", type=Path, required=True, help="Output directory for benchmark bundles and summary.")
    parser.add_argument("--retrieval-date", default=local_date(), help="Retrieval date written to source corpus.")
    parser.add_argument("--validate", action="store_true", help="Run bmat_validate.py after metadata overlay.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing bundle scaffold files.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    all_cases = load_cases(args.cases)
    cases = select_cases(all_cases, args.case)
    args.out.mkdir(parents=True, exist_ok=True)

    results = [
        run_case(case, args.out, validate=args.validate, force=args.force, retrieval_date=args.retrieval_date)
        for case in cases
    ]
    summary = {
        "schema_version": "1.0",
        "benchmark_type": "metadata-only-public-omics-smoke",
        "retrieval_date": args.retrieval_date,
        "case_count": len(results),
        "validated": bool(args.validate),
        "raw_data_downloaded": False,
        "results": results,
    }
    summary_path = args.out / "public_omics_benchmark_summary.json"
    write_json(summary_path, summary)
    print(f"BMAT public omics benchmark summary: {summary_path.resolve()}")
    failed = [result for result in results if result["status"] != "pass"]
    if failed:
        print(json.dumps({"failed": failed}, indent=2), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
