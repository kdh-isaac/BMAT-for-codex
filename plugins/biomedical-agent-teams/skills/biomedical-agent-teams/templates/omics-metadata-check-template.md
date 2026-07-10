# Omics Metadata Check Template

Use `omics_metadata_check.json` for executable local checks from `bmat_omics_metadata_check.py` or an equivalent review.

```json
{
  "schema_version": "1.0",
  "check_id": "omc-<workflow_run_id>",
  "plugin_version": "1.2.0",
  "workflow_run_id": "<workflow_run_id>",
  "track": "tenx-gex",
  "status": "pass-with-caveats",
  "blocking_issues": [],
  "warnings": ["State any missing optional provenance or local-file caveats."],
  "artifact_refs": ["omics_run_manifest.json"],
  "claim_ids_affected": [],
  "downgrade_recommendations": []
}
```
