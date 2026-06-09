# Workflow Run Template

Use for deep, audit, omics run, translational, manuscript-support,
generated-file, or long-running BMAT workflows. Keep the run state compact
enough to paste into a final answer or save as a local artifact.

| field | value |
|---|---|
| run_id | BMAT-RUN-YYYYMMDD-001 |
| alias | biomedical-research-council / idea-discovery-team / omics-analysis-team / evidence-audit-team / experiment-design-team / translational-scout-team |
| mode | quick / standard / deep / audit / plan / run |
| plugin_version | 0.3.0 |
| artifacts_root |  |
| resume_pointer |  |
| final_label | Full protocol followed / Compact standard workflow / Biomedical Agent Teams-informed narrative review / Partial workflow; formal gates skipped / Blocked |

## Stage DAG

| stage_id | required | status | depends_on | evidence | block_condition |
|---|---|---|---|---|---|
| runtime_capability_preflight | yes | pass / pass-with-caveats / skipped / block / not-applicable | none |  | unavailable required runtime capability |
| context_lock | yes | pass / pass-with-caveats / skipped / block / not-applicable | runtime_capability_preflight |  | unclear question or unsafe scope |
| entity_normalization | context-dependent | pass / pass-with-caveats / skipped / block / not-applicable | context_lock |  | unresolved identifiers needed for source expansion |
| source_corpus_lock | source-backed outputs | pass / pass-with-caveats / skipped / block / not-applicable | entity_normalization |  | missing source identifiers or retrieval dates |
| selected_playbook | yes | pass / pass-with-caveats / skipped / block / not-applicable | context_lock |  | no bounded workflow route |
| claim_ledger_update | standard/deep/audit | pass / pass-with-caveats / skipped / block / not-applicable | selected_playbook |  | unchecked claims before writing |
| stage_evaluation | omics/generated-file/long-running | pass / pass-with-caveats / skipped / block / not-applicable | selected_playbook |  | validation stage blocks inference/reporting |
| audit_gates | deep/audit/source-backed | pass / pass-with-caveats / skipped / block / not-applicable | claim_ledger_update |  | required gate has suspected failure |
| writer | final outputs | pass / pass-with-caveats / skipped / block / not-applicable | claim_ledger_update |  | writer uses non-ledger material |
| post_write_validation | final outputs | pass / pass-with-caveats / skipped / block / not-applicable | writer |  | unsupported final claim |

## Downgrade Reasons

| reason_id | reason |
|---|---|
| DR-001 |  |
