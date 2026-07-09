# Claim Support Matrix Template

Use `claim_support_matrix.json` to separate source identity verification from claim-level entailment, scope, and allowed final wording.

```json
{
  "schema_version": "1.0",
  "support_matrix_id": "csm-<workflow_run_id>",
  "plugin_version": "1.1.1",
  "workflow_run_id": "<workflow_run_id>",
  "rows": [
    {
      "claim_id": "CL-001",
      "source_id": "S-001",
      "evidence_span_ref": "S-001-span-001",
      "support_verdict": "supports",
      "scope_match": {
        "species": "match",
        "cell_type": "match",
        "assay": "match",
        "endpoint": "match"
      },
      "overclaim_risk": "low",
      "allowed_in_final": true,
      "allowed_final_wording": "Conservative, ledger-approved final wording.",
      "review_surface": "citation-verifier",
      "independent_review_required": true,
      "limitations": "Record scope and evidence limits."
    }
  ]
}
```
