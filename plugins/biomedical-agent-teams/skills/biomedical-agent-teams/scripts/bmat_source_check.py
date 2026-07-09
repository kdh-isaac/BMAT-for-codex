#!/usr/bin/env python3
"""Create and validate BMAT source_verification.json artifacts.

This checker is deterministic and offline by default. It verifies consistency
between source_corpus.json, claim_ledger.json, tool_call_ledger.json, and the
generated source_verification.json contract. It does not call external
databases; callers that use real tools must record those calls in
tool_call_ledger.json.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Finding:
    level: str
    code: str
    message: str
    path: str = ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate/check BMAT source_verification.json.")
    parser.add_argument("--source-corpus", type=Path, required=True)
    parser.add_argument("--claim-ledger", type=Path, required=True)
    parser.add_argument("--tool-call-ledger", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--offline-fixture", action="store_true", help="Mark included sources as verified/pass for deterministic fixture mode.")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def read_json(path: Path, findings: list[Finding]) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        findings.append(Finding("ERROR", "FILE_MISSING", "input JSON file missing", str(path)))
    except json.JSONDecodeError as exc:
        findings.append(Finding("ERROR", "INVALID_JSON", f"invalid JSON: {exc}", str(path)))
    return None


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def plugin_version() -> str:
    version_path = Path(__file__).resolve().parents[1] / "VERSION"
    try:
        return version_path.read_text(encoding="utf-8-sig").strip()
    except FileNotFoundError:
        return "unknown"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def iter_claims(claim_ledger: Any) -> list[dict[str, Any]]:
    if isinstance(claim_ledger, dict):
        for key in ("claims", "claim_ledger", "rows"):
            value = claim_ledger.get(key)
            if isinstance(value, list):
                return [claim for claim in value if isinstance(claim, dict)]
    if isinstance(claim_ledger, list):
        return [claim for claim in claim_ledger if isinstance(claim, dict)]
    return []


def value_as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [part.strip() for part in value.replace(";", ",").split(",") if part.strip()]
    return []


def claim_source_ids(claim: dict[str, Any]) -> list[str]:
    ids = value_as_list(claim.get("source_ids")) + value_as_list(claim.get("source_id"))
    evidence_items = claim.get("evidence_items", claim.get("evidence", []))
    if isinstance(evidence_items, list):
        for item in evidence_items:
            if isinstance(item, str):
                ids.append(item)
            elif isinstance(item, dict):
                ids.extend(value_as_list(item.get("source_id")))
    return list(dict.fromkeys(ids))


def claim_id(claim: dict[str, Any]) -> str:
    return str(claim.get("claim_id", "unknown")).strip() or "unknown"


def included_sources(source_corpus: Any) -> list[dict[str, Any]]:
    if not isinstance(source_corpus, dict):
        return []
    return [
        source for source in source_corpus.get("sources", [])
        if isinstance(source, dict) and source.get("inclusion_status") == "included"
    ]


def successful_tool_call_ids(tool_call_ledger: Any) -> set[str]:
    if not isinstance(tool_call_ledger, dict):
        return set()
    calls = tool_call_ledger.get("calls", [])
    if not isinstance(calls, list):
        return set()
    return {
        str(call.get("call_id", "")).strip()
        for call in calls
        if isinstance(call, dict) and call.get("status") == "success" and str(call.get("call_id", "")).strip()
    }


def build_source_claim_map(claims: list[dict[str, Any]]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for claim in claims:
        for source_id in claim_source_ids(claim):
            out.setdefault(source_id, []).append(claim_id(claim))
    return out


def main() -> int:
    args = parse_args()
    findings: list[Finding] = []
    source_corpus = read_json(args.source_corpus, findings)
    claim_ledger = read_json(args.claim_ledger, findings)
    tool_call_ledger = read_json(args.tool_call_ledger, findings) if args.tool_call_ledger else None

    claims = iter_claims(claim_ledger)
    source_claims = build_source_claim_map(claims)
    corpus_ids = {str(source.get("source_id", "")).strip() for source in included_sources(source_corpus)}
    for claim in claims:
        for source_id in claim_source_ids(claim):
            if source_id not in corpus_ids:
                findings.append(
                    Finding(
                        "ERROR",
                        "CLAIM_SOURCE_NOT_INCLUDED",
                        f"{claim_id(claim)} references {source_id}, which is absent or not included in source_corpus",
                        str(args.claim_ledger),
                    )
                )

    success_call_ids = successful_tool_call_ids(tool_call_ledger)
    rows: list[dict[str, Any]] = []
    for source in included_sources(source_corpus):
        source_id = str(source.get("source_id", "")).strip()
        identifier_status = "verified" if args.offline_fixture else "not-checked"
        metadata_match = "pass" if args.offline_fixture else "not-checked"
        tool_call_id = ""
        if str(source.get("checked_by", "")).strip() not in {"", "manual", "not-checked"} and success_call_ids:
            tool_call_id = sorted(success_call_ids)[0]
        rows.append(
            {
                "source_id": source_id,
                "source_type": source.get("source_type", "other"),
                "identifier": source.get("identifier", ""),
                "identifier_status": identifier_status,
                "metadata_match": metadata_match,
                "canonical_title": source.get("title_or_name", ""),
                "canonical_date": source.get("version_or_retrieval_date", ""),
                "retrieval_surface": "offline-fixture" if args.offline_fixture else "not-checked",
                "tool_id": source.get("checked_by", ""),
                "tool_call_id": tool_call_id,
                "source_corpus_row_status": source.get("inclusion_status", ""),
                "claim_ids_checked": source_claims.get(source_id, []),
                "verification_limitations": "offline fixture mode" if args.offline_fixture else "identifier metadata not externally checked",
            }
        )
        if tool_call_id and tool_call_id not in success_call_ids:
            findings.append(
                Finding("ERROR", "SOURCE_VERIFICATION_TOOL_CALL_NOT_SUCCESSFUL", f"{source_id} references unsuccessful tool_call_id {tool_call_id}", str(args.out))
            )

    workflow_run_id = ""
    if isinstance(tool_call_ledger, dict):
        workflow_run_id = str(tool_call_ledger.get("workflow_run_id", ""))
    payload = {
        "schema_version": "1.0",
        "verification_id": f"sv-{workflow_run_id or 'manual'}",
        "plugin_version": plugin_version(),
        "workflow_run_id": workflow_run_id,
        "checked_at": utc_now(),
        "rows": rows,
    }
    write_json(args.out, payload)

    if args.json:
        print(json.dumps({"findings": [asdict(finding) for finding in findings], "out": str(args.out)}, indent=2))
    else:
        for finding in findings:
            print(f"{finding.level} {finding.code}: {finding.message}")
        print(f"source_verification written: {args.out}")
    return 1 if any(finding.level == "ERROR" for finding in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
