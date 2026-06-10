# Workflow Run Template

Use for deep, audit, omics run, translational, manuscript-support,
generated-file, or long-running BMAT workflows. Keep the run state compact
enough to paste into a final answer or save as a local artifact.

| field | value |
|---|---|
| run_id | BMAT-RUN-YYYYMMDD-001 |
| alias | biomedical-research-council / idea-discovery-team / omics-analysis-team / evidence-audit-team / experiment-design-team / translational-scout-team |
| mode | quick / standard / deep / audit / plan / run |
| plugin_version | 0.3.5 |
| artifacts_root |  |
| resume_pointer |  |
| execution_strategy | inline_only / inline_first_selective_review / team_level_selective_dag / user_requested_full_spawn / blocked |
| nested_spawn_allowed | false / true-with-explicit-approval |
| final_label | Full protocol followed / Compact standard workflow / Biomedical Agent Teams-informed narrative review / Partial workflow; formal gates skipped / Blocked |

## Spawned Review Lanes

| reviewer_role | status | rationale | ledger_handoff |
|---|---|---|---|
| claim-level-evidence-verifier | planned / running / complete / skipped / blocked |  |  |
| citation-verifier | planned / running / complete / skipped / blocked |  |  |
| contradiction-red-team | planned / running / complete / skipped / blocked |  |  |
| biostats-repro-auditor | planned / running / complete / skipped / blocked |  |  |

## Team Spawn Lanes

| team | phase | depends_on | status | nested_spawn_used | ledger_handoff |
|---|---|---|---|---|---|
| idea-discovery-team | 1 | phase 0 | planned / running / complete / skipped / blocked | false |  |
| omics-analysis-team | 1 | phase 0 | planned / running / complete / skipped / blocked | false |  |
| translational-scout-team | 1 | phase 0 | planned / running / complete / skipped / blocked | false |  |
| experiment-design-team | 2 | narrowed candidate claims | planned / running / complete / skipped / blocked | false |  |
| evidence-audit-team | 2 | draft claims or results | planned / running / complete / skipped / blocked | false |  |

## Stage DAG

| stage_id | required | status | depends_on | evidence | block_condition |
|---|---|---|---|---|---|
| runtime_capability_preflight | yes | pass / pass-with-caveats / skipped / block / not-applicable | none |  | unavailable required runtime capability |
| context_lock | yes | pass / pass-with-caveats / skipped / block / not-applicable | runtime_capability_preflight |  | unclear question or unsafe scope |
| entity_normalization | context-dependent | pass / pass-with-caveats / skipped / block / not-applicable | context_lock |  | unresolved identifiers needed for source expansion |
| source_corpus_lock | source-backed outputs | pass / pass-with-caveats / skipped / block / not-applicable | entity_normalization |  | missing source identifiers or retrieval dates |
| selected_playbook | yes | pass / pass-with-caveats / skipped / block / not-applicable | context_lock |  | no bounded workflow route |
| execution_strategy_lock | yes | pass / pass-with-caveats / skipped / block / not-applicable | selected_playbook |  | spawn strategy unsupported or unjustified |
| team_spawn_outputs | selected team DAG workflows | pass / pass-with-caveats / skipped / block / not-applicable | execution_strategy_lock |  | missing formal team output or ledger handoff |
| claim_ledger_update | standard/deep/audit | pass / pass-with-caveats / skipped / block / not-applicable | selected_playbook; team_spawn_outputs when used |  | unchecked claims before writing |
| stage_evaluation | omics/generated-file/long-running | pass / pass-with-caveats / skipped / block / not-applicable | selected_playbook |  | validation stage blocks inference/reporting |
| audit_gates | deep/audit/source-backed | pass / pass-with-caveats / skipped / block / not-applicable | claim_ledger_update |  | required gate has suspected failure |
| selective_review_outputs | selected review workflows | pass / pass-with-caveats / skipped / block / not-applicable | audit_gates |  | missing formal reviewer output or ledger handoff |
| writer | final outputs | pass / pass-with-caveats / skipped / block / not-applicable | claim_ledger_update; selective_review_outputs when used |  | writer uses non-ledger material |
| post_write_validation | final outputs | pass / pass-with-caveats / skipped / block / not-applicable | writer |  | unsupported final claim |

## Downgrade Reasons

| reason_id | reason |
|---|---|
| DR-001 |  |
