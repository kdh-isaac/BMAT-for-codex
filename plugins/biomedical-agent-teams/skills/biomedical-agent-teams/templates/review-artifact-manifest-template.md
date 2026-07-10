# Review Artifact Manifest Template (v2)

Use `review_artifact_manifest.json` to bind every review claim to the exact
input, prompt, output, runtime identity, and SHA-256 receipts. A spawned task is
not independent by itself. Apply `references/independent-review-policy.md` and
validate the finished JSON against
`contracts/review-artifact-manifest.schema.json`. Validate each referenced
runtime receipt against `contracts/review-runtime-receipt.schema.json`.

```json
{
  "schema_version": "2.0",
  "review_manifest_id": "BMAT-REVIEW-MANIFEST-20260710-001",
  "workflow_run_id": "BMAT-RUN-20260710-001",
  "plugin_version": "1.2.0",
  "created_at": "2026-07-10T09:00:00+09:00",
  "review_instances": [
    {
      "instance_id": "BMAT-REVIEW-001",
      "agent_id": "citation-verifier",
      "actor_type": "model",
      "provider": "<runtime-reported-provider>",
      "model": "<runtime-reported-model>",
      "model_version": "<runtime-reported-model-version>",
      "authoring_provider": "<authoring-runtime-provider>",
      "authoring_model": "<authoring-runtime-model>",
      "authoring_model_version": "<authoring-runtime-model-version>",
      "authoring_execution_session_id": "<authoring-session-id>",
      "authoring_identity_available": true,
      "execution_surface": "spawned_subagent",
      "execution_session_id": "<runtime-session-id>",
      "spawn_event_id": "<spawn-event-id>",
      "input_scope": "Claims CL-001 and CL-002, source corpus rows S-001 and S-002, and the frozen draft",
      "input_artifact_refs": [
        "claim_ledger.json",
        "source_corpus.json",
        "draft/final-candidate.md"
      ],
      "input_artifact_sha256": {
        "claim_ledger.json": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "source_corpus.json": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "draft/final-candidate.md": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
      },
      "prompt_template_ref": "review/prompts/citation-verifier-v2.md",
      "prompt_template_sha256": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
      "output_artifact": "review/outputs/citation-verifier.md",
      "output_sha256": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
      "checks_run": [
        "source identity receipt checked",
        "claim-source and evidence-span linkage checked",
        "allowed final wording checked"
      ],
      "changed_claim_ids": ["CL-002"],
      "ledger_handoff": "CL-001 retained; CL-002 downgraded and routed to RI-ROW-007",
      "results_integration_rows": ["RI-ROW-007"],
      "independence_class": "separate-model",
      "independent_review_eligible": true,
      "fixture_only": false,
      "authoring_context_shared": false,
      "started_at": "2026-07-10T08:45:00+09:00",
      "completed_at": "2026-07-10T08:55:00+09:00",
      "runtime_receipt_ref": "review/receipts/citation-verifier-runtime.json",
      "runtime_receipt_sha256": "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
      "limitations": "Separate-model classification still establishes process independence, not scientific truth."
    }
  ]
}
```

The referenced `review/receipts/citation-verifier-runtime.json` has this shape:

```json
{
  "schema_version": "2.0",
  "receipt_id": "BMAT-RUNTIME-RECEIPT-001",
  "workflow_run_id": "BMAT-RUN-20260710-001",
  "plugin_version": "1.2.0",
  "instance_id": "BMAT-REVIEW-001",
  "actor_type": "model",
  "provider": "<runtime-reported-provider>",
  "model": "<runtime-reported-model>",
  "model_version": "<runtime-reported-model-version>",
  "authoring_provider": "<authoring-runtime-provider>",
  "authoring_model": "<authoring-runtime-model>",
  "authoring_model_version": "<authoring-runtime-model-version>",
  "authoring_execution_session_id": "<authoring-session-id>",
  "authoring_identity_available": true,
  "execution_surface": "spawned_subagent",
  "execution_session_id": "<runtime-session-id>",
  "spawn_event_id": "<spawn-event-id>",
  "authoring_context_shared": false,
  "status": "success",
  "fixture_only": false,
  "receipt_source": "runtime-native",
  "runtime_metadata_available": true,
  "started_at": "2026-07-10T08:45:00+09:00",
  "completed_at": "2026-07-10T08:55:00+09:00",
  "captured_at": "2026-07-10T08:56:00+09:00",
  "capture_method": "runtime-api",
  "limitations": "Runtime identity receipt only; it does not establish scientific correctness."
}
```

Replace every placeholder and example digest with runtime-derived values. For
each input ref, use the same relative path as a key in
`input_artifact_sha256`. Write output and runtime-receipt files first, hash
their exact bytes, then write the manifest. If provider/model/session identity
is unavailable, record `unavailable`, set
`independent_review_eligible=false`, use a non-independent class, and downgrade
the final workflow label; never fabricate metadata.
