#!/usr/bin/env python3
"""Run deterministic local BMAT omics metadata checks."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TENX_TRACKS = {"tenx-gex", "tenx-cellplex", "tenx-citeseq", "tenx-vdj", "tenx-multiome"}
TRACKS = (
    "bulk-rnaseq",
    "tenx-gex",
    "tenx-cellplex",
    "tenx-citeseq",
    "tenx-vdj",
    "tenx-multiome",
    "single-cell-other",
    "survival",
    "multi-omics",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check BMAT omics metadata completeness.")
    parser.add_argument("--track", choices=TRACKS, required=True)
    parser.add_argument("--omics-run-manifest", type=Path, required=True)
    parser.add_argument("--sample-sheet", type=Path)
    parser.add_argument("--count-matrix", type=Path)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def plugin_version() -> str:
    version_path = Path(__file__).resolve().parents[1] / "VERSION"
    try:
        return version_path.read_text(encoding="utf-8-sig").strip()
    except FileNotFoundError:
        return "unknown"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def has_text(mapping: dict[str, Any], key: str) -> bool:
    value = mapping.get(key)
    return isinstance(value, str) and bool(value.strip()) and not value.strip().startswith("TODO")


def check_manifest(track: str, manifest: dict[str, Any]) -> tuple[list[str], list[str], list[str]]:
    blocking: list[str] = []
    warnings: list[str] = []
    artifact_refs: list[str] = ["omics_run_manifest.json"]
    assay = manifest.get("assay_metadata", {}) if isinstance(manifest.get("assay_metadata"), dict) else {}
    bio = manifest.get("biological_unit_policy", {}) if isinstance(manifest.get("biological_unit_policy"), dict) else {}
    de = manifest.get("de_strategy", {}) if isinstance(manifest.get("de_strategy"), dict) else {}
    qc = manifest.get("qc_decisions", {}) if isinstance(manifest.get("qc_decisions"), dict) else {}
    artifacts = manifest.get("generated_artifacts", {}) if isinstance(manifest.get("generated_artifacts"), dict) else {}

    for field in ("organism", "genome_build", "annotation_release"):
        if not has_text(assay, field):
            blocking.append(f"assay_metadata.{field} missing")
    if not has_text(manifest, "sample_sheet"):
        blocking.append("sample_sheet missing")
    if not has_text(manifest, "contrast_or_endpoint"):
        blocking.append("contrast_or_endpoint missing")
    if not has_text(bio, "replicate_key"):
        blocking.append("biological_unit_policy.replicate_key missing")

    if track == "bulk-rnaseq":
        for field in ("design_formula", "count_model", "multiplicity_method", "effect_size_report"):
            if not has_text(de, field):
                blocking.append(f"de_strategy.{field} missing")
        if de.get("design_matrix_rank_checked") is not True:
            blocking.append("design_matrix_rank_checked must be true or explicitly blocked before release")
        for field in ("count_matrix", "design_matrix", "de_results_table"):
            if not has_text(artifacts, field):
                blocking.append(f"generated_artifacts.{field} missing")
    if track in TENX_TRACKS:
        for field in ("cellranger_version", "cellranger_command"):
            if not has_text(assay, field):
                blocking.append(f"assay_metadata.{field} missing")
        for field in ("cell_calling_method", "ambient_rna_method", "doublet_method", "empty_droplet_method"):
            if not has_text(qc, field):
                blocking.append(f"qc_decisions.{field} missing")
        for field in ("web_summary_html", "filtered_feature_bc_matrix", "raw_feature_bc_matrix", "molecule_info_h5"):
            if not has_text(artifacts, field):
                blocking.append(f"generated_artifacts.{field} missing")
        if bio.get("pseudobulk_required") is not True or not has_text(bio, "pseudobulk_policy"):
            blocking.append("donor/sample-aware pseudobulk policy required for cross-sample 10x inference")
    if bio.get("unit") in {"cell", "spot"} and "descriptive" not in str(bio.get("cell_level_tests_limited_to", "")).lower():
        warnings.append("cell-level inferential testing should be limited to descriptive claims unless justified")

    for value in artifacts.values():
        if isinstance(value, str) and value.strip():
            artifact_refs.append(value)
    return blocking, warnings, artifact_refs


def main() -> int:
    args = parse_args()
    manifest = read_json(args.omics_run_manifest)
    blocking, warnings, artifact_refs = check_manifest(args.track, manifest)
    for label, path in (("sample_sheet", args.sample_sheet), ("count_matrix", args.count_matrix), ("metadata", args.metadata)):
        if path is not None and not path.exists():
            blocking.append(f"{label} path does not exist: {path}")
    payload = {
        "schema_version": "1.0",
        "check_id": f"omc-{manifest.get('workflow_run_id', 'manual')}",
        "plugin_version": plugin_version(),
        "workflow_run_id": manifest.get("workflow_run_id", ""),
        "track": args.track,
        "checked_at": utc_now(),
        "status": "block" if blocking else ("pass-with-caveats" if warnings else "pass"),
        "blocking_issues": blocking,
        "warnings": warnings,
        "artifact_refs": artifact_refs,
        "claim_ids_affected": [],
        "downgrade_recommendations": ["Downgrade high-confidence omics claims until blocking issues are resolved"] if blocking else [],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"omics_metadata_check written: {args.out}")
        for issue in blocking:
            print(f"ERROR OMICS_METADATA_BLOCK: {issue}")
        for warning in warnings:
            print(f"WARN OMICS_METADATA_WARNING: {warning}")
    return 1 if blocking else 0


if __name__ == "__main__":
    raise SystemExit(main())
