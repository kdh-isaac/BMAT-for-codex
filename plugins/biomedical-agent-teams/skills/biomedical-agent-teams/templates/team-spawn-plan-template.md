# Team Spawn Plan Template

Use this for selective spawned review or dependency-aware command-team work.
This artifact records intent and routing only. It is never proof of independent
execution; completed review evidence belongs in the v2
`review_artifact_manifest.json` with runtime metadata and verified hashes.

| field | value |
|---|---|
| plan_id | BMAT-SPAWN-YYYYMMDD-001 |
| workflow_alias | biomedical-research-council / idea-discovery-team / omics-analysis-team / evidence-audit-team / experiment-design-team / translational-scout-team |
| mode | quick / standard / deep / audit / plan / run |
| execution_strategy | inline_only / inline_first_selective_review / team_level_selective_dag / user_requested_full_spawn / blocked |
| spawned_subagents_supported | yes / no / unknown / not-applicable |
| spawn_budget | 0 / 1 / 2 / 3 / 4 / user-approved |
| nested_spawn_allowed | false / true-with-explicit-approval |
| all_role_spawn_avoidance_reason |  |
| privacy_and_safety_boundary |  |
| central_claim_ledger_owner | main lead |
| review_contract | contracts/review-artifact-manifest.schema.json v2 |
| runtime_receipt_contract | contracts/review-runtime-receipt.schema.json v2 |
| independence_policy | references/independent-review-policy.md |
| Full-eligible classes | separate-model / external-tool / human |
| supplementary-only classes | same-model-separate-context |
| non-independent classes | same-model-self-review |
| authoring identity comparison | required for same-model / separate-model classification |
| post_team_audit_plan |  |

## Selected Spawned Reviewers

`planned_independence_class` is a routing hypothesis, not a verdict. Confirm it
from provider/model/session/runtime receipts after execution. A spawn event
alone does not establish independence.

| reviewer_role | reason_selected | input_scope | required_input_refs_and_hashes | planned_independence_class | required_output | status |
|---|---|---|---|---|---|---|
| claim-level-evidence-verifier |  | claim IDs / draft section | refs plus SHA-256 map | same-model-self-review / same-model-separate-context / separate-model / external-tool / human | v2 reviewer output plus runtime receipt | planned / running / complete / skipped |
| citation-verifier |  | source corpus rows | refs plus SHA-256 map |  | v2 reviewer output plus runtime receipt | planned / running / complete / skipped |
| contradiction-red-team |  | candidate claims | refs plus SHA-256 map |  | v2 reviewer output plus runtime receipt | planned / running / complete / skipped |
| biostats-repro-auditor |  | methods/results | refs plus SHA-256 map |  | v2 reviewer output plus runtime receipt | planned / running / complete / skipped |
| omics-provenance-validator |  | omics artifacts | refs plus SHA-256 map |  | v2 reviewer output plus runtime receipt | planned / running / complete / skipped |
| risk-of-bias-study-quality-auditor |  | evidence set | refs plus SHA-256 map |  | v2 reviewer output plus runtime receipt | planned / running / complete / skipped |

## Team-Level Dependency DAG

Command-team outputs can contribute analysis, but team separation does not
make them independent review receipts. Record any actual reviewer instance
separately.

| phase | spawned_team | mode | depends_on | input_scope | required_output | nested_spawn_allowed | status |
|---|---|---|---|---|---|---|---|
| 0 | main lead inline |  | none | protocol/context/source scope | lock and dispatch plan | false | planned / complete |
| 1 | idea-discovery-team | quick / standard / deep / audit | phase 0 | idea seed / decision context | formal idea team report | false | planned / running / complete / skipped |
| 1 | omics-analysis-team | plan / audit / run | phase 0 | accession/cohort/assay/contrast | formal omics team report | false | planned / running / complete / skipped |
| 1 | translational-scout-team | quick / standard / deep / audit | phase 0 | target/indication/therapy concept | formal translational team report | false | planned / running / complete / skipped |
| 2 | experiment-design-team | quick / standard / deep / audit | narrowed candidate claims | selected hypothesis/design | formal experiment-design team report | false | planned / running / complete / skipped |
| 2 | evidence-audit-team | standard / deep / audit | draft claims or results | claim ledger / draft text / report | formal evidence-audit team report | false | planned / running / complete / skipped |
| 3 | main lead inline |  | completed spawned outputs | accepted team outputs | ledger merge and final synthesis | false | planned / complete |

## Receipt And Ledger Handoff

| spawned_output_id | review_instance_id | runtime_receipt_ref_and_sha256 | accepted_findings | rejected_or_downgraded_findings | affected_claim_ids | changed_claim_ids | results_integration_rows | lead_action |
|---|---|---|---|---|---|---|---|---|
| SO-001 | REV-001 | review/receipts/REV-001.json + SHA-256 |  |  |  |  |  | accept / revise / downgrade / exclude |

## Structured Skipped Spawn Reasons

Free-text alone is not a gate input. Use one supported `reason_code` and a
non-Full `downgrade_label`.

| skipped_role_or_team | reason_code | reason_detail | affected_roles | downgrade_label | approved_by | recorded_at |
|---|---|---|---|---|---|---|
|  | RUNTIME_NO_SPAWN_SUPPORT / TOOL_REVIEW_UNAVAILABLE / PRIVACY_BLOCKED / USER_COMPACT_INLINE_ONLY / EXPLICITLY_OUT_OF_SCOPE / BUDGET_BLOCKED / HUMAN_GATE_BLOCKED |  |  |  | actor ID / not-applicable | RFC 3339 date-time |
