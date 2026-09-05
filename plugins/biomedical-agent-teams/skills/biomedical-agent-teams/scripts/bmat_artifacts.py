"""Canonical bundle keys, filenames and schemas; no runtime dependencies."""

BUNDLE_FILES = {
    "run_state": "run_state.json",
    "preflight": "runtime_capability_preflight.json",
    "source_corpus": "source_corpus.json",
    "claim_ledger": "claim_ledger.json",
    "stage_evaluation": "stage_evaluation.json",
    "post_write_validation": "post_write_validation.json",
    "final_text": "final.md",
}

BUNDLE_FILE_ALIASES = {
    "preflight": ("preflight.json",),
}

OPTIONAL_BUNDLE_FILES = {
    "lead_decision": "lead_decision.json",
    "results_integration": "results_integration.json",
    "tool_call_ledger": "tool_call_ledger.json",
    "workflow_dag": "workflow_dag.json",
    "omics_run_manifest": "omics_run_manifest.json",
    "source_verification": "source_verification.json",
    "claim_support_matrix": "claim_support_matrix.json",
    "omics_metadata_check": "omics_metadata_check.json",
    "experiment_design": "experiment_design.json",
    "review_artifact_manifest": "review_artifact_manifest.json",
    "bundle_manifest": "bundle_manifest.json",
    "hypothesis_tournament": "hypothesis_tournament.json",
}

SCHEMA_FILES = {
    "run_state": "workflow-run.schema.json",
    "preflight": "preflight-contract.schema.json",
    "lead_decision": "lead-decision.schema.json",
    "source_corpus": "source-corpus.schema.json",
    "claim_ledger": "claim-ledger.schema.json",
    "results_integration": "results-integration.schema.json",
    "tool_call_ledger": "tool-call-ledger.schema.json",
    "workflow_dag": "workflow-dag.schema.json",
    "omics_run_manifest": "omics-run-manifest.schema.json",
    "source_verification": "source-verification.schema.json",
    "claim_support_matrix": "claim-support-matrix.schema.json",
    "omics_metadata_check": "omics-metadata-check.schema.json",
    "experiment_design": "experiment-design.schema.json",
    "review_artifact_manifest": "review-artifact-manifest.schema.json",
    "bundle_manifest": "bundle-manifest.schema.json",
    "hypothesis_tournament": "hypothesis-tournament.schema.json",
    "stage_evaluation": "stage-evaluation.schema.json",
    "post_write_validation": "post-write-validation.schema.json",
}

ARTIFACT_FILES = {**BUNDLE_FILES, **OPTIONAL_BUNDLE_FILES}
