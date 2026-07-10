#!/usr/bin/env python3
"""Generate a hash-bound BMAT v2 release bundle manifest.

The manifest excludes itself to avoid a recursive hash.  All paths are emitted
relative to the bundle root, and the write is atomic.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXCLUDED_PARTS = {"__pycache__", ".pytest_cache", ".git"}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return payload


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate bundle_manifest.json for a BMAT v2 bundle.")
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    bundle = args.bundle.resolve()
    if not bundle.is_dir():
        raise SystemExit(f"bundle directory does not exist: {bundle}")
    out = (args.out or (bundle / "bundle_manifest.json")).resolve()
    try:
        out.relative_to(bundle)
    except ValueError as exc:
        raise SystemExit("manifest output must stay inside the bundle") from exc

    run_state = read_json(bundle / "run_state.json")
    workflow_run_id = str(run_state.get("run_id", "")).strip()
    plugin_version = str(run_state.get("plugin_version", "")).strip()
    if not workflow_run_id or not plugin_version:
        raise SystemExit("run_state.json requires non-empty run_id and plugin_version")

    generated_at = utc_now()
    entries: list[dict[str, Any]] = []
    for path in sorted(bundle.rglob("*")):
        if not path.is_file() or path.resolve() == out or any(part in EXCLUDED_PARTS for part in path.parts):
            continue
        relative = path.relative_to(bundle).as_posix()
        schema_version = "not-applicable"
        if path.suffix.lower() == ".json":
            try:
                payload = read_json(path)
            except (json.JSONDecodeError, UnicodeDecodeError):
                payload = {}
            schema_version = str(payload.get("schema_version", "not-applicable"))
        entries.append(
            {
                "artifact_type": path.stem.replace("-", "_"),
                "path": relative,
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
                "schema_version": schema_version,
                "plugin_version": plugin_version,
                "workflow_run_id": workflow_run_id,
                "required_for_release": path.name in {
                    "run_state.json",
                    "runtime_capability_preflight.json",
                    "source_corpus.json",
                    "claim_ledger.json",
                    "stage_evaluation.json",
                    "post_write_validation.json",
                    "final.md",
                },
                "generated_at": generated_at,
            }
        )

    manifest = {
        "schema_version": "2.0",
        "manifest_id": f"bundle-{workflow_run_id}",
        "plugin_version": plugin_version,
        "workflow_run_id": workflow_run_id,
        "generated_at": generated_at,
        "entries": entries,
    }
    atomic_write_json(out, manifest)
    print(f"BMAT bundle manifest written: {out} ({len(entries)} entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
