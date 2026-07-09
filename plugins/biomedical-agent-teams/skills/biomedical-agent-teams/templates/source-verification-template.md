# Source Verification Template

Use this artifact as `source_verification.json` after running `bmat_source_check.py` or an equivalent local/manual verification pass.

```json
{
  "schema_version": "1.0",
  "verification_id": "sv-<workflow_run_id>",
  "plugin_version": "1.1.1",
  "workflow_run_id": "<workflow_run_id>",
  "checked_at": "YYYY-MM-DDTHH:MM:SSZ",
  "rows": [
    {
      "source_id": "S-001",
      "source_type": "PMID",
      "identifier": "12345678",
      "identifier_status": "verified",
      "metadata_match": "pass",
      "canonical_title": "Verified source title",
      "canonical_date": "YYYY-MM-DD",
      "retrieval_surface": "offline-fixture-or-tool",
      "tool_id": "pubmed",
      "tool_call_id": "TC-001",
      "source_corpus_row_status": "included",
      "claim_ids_checked": ["CL-001"],
      "verification_limitations": "State fixture, network, metadata, or ambiguity limits."
    }
  ]
}
```
