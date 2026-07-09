# Review Artifact Manifest Template

Use `review_artifact_manifest.json` to bind independent review claims to concrete output files and hashes.

```json
{
  "schema_version": "1.0",
  "workflow_run_id": "<workflow_run_id>",
  "plugin_version": "1.1.0",
  "review_instances": [
    {
      "instance_id": "BMAT-SPAWN-001",
      "agent_id": "citation-verifier",
      "execution_surface": "tool_backed_validator",
      "input_scope": "Claim CL-001 and source S-001",
      "input_digest": "sha256-or-short-digest-of-input",
      "output_artifact": "review/citation-verifier.md",
      "output_sha256": "<sha256>",
      "checks_run": ["source identity checked", "allowed wording checked"],
      "ledger_handoff": "CL-001 checked against S-001",
      "results_integration_rows": ["RI-ROW-001"],
      "changed_claim_ids": ["CL-001"],
      "limitations": "Synthetic fixture, same-model, or tool-bound limitations."
    }
  ]
}
```
