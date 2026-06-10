# Biomedical Passport Template

Use this template for deep, audit, omics run, translational, manuscript-support,
or long-running BMAT workflows. Keep it concise enough to paste into a final
answer or save as a local artifact when file output is requested.

## Passport Header

| field | value |
|---|---|
| passport_id | BP-YYYYMMDD-001 |
| workflow_alias | biomedical-research-council / omics-analysis-team / evidence-audit-team / experiment-design-team / translational-scout-team |
| workflow_version | 0.3.5 |
| created_at |  |
| updated_at |  |
| current_stage |  |
| next_action |  |

## Context Lock

| field | value |
|---|---|
| question_schema |  |
| deliverable_type |  |
| evidence_scope |  |
| risk_safety_privacy_class |  |
| depth_budget_stop_criteria |  |
| human_approval_gate |  |

## Normalized Entities

| entity | normalized_id_or_name | ambiguity | downstream_note |
|---|---|---|---|
|  |  |  |  |

## Source Corpus

| source_id | type | identifier | version_or_retrieval_date | status | claim_use |
|---|---|---|---|---|---|
| S-001 | PMID/DOI/accession/NCT/file/tool |  |  | checked / not checked / excluded |  |

## Workflow Run State

| field | value |
|---|---|
| workflow_run_id |  |
| workflow_run_location_or_summary |  |
| current_stage_status |  |

## Stage Evaluation

| stage | status | reason |
|---|---|---|
| S1 Plan | pass / pass-with-caveats / skipped / block / not-applicable |  |
| S2 Setup | pass / pass-with-caveats / skipped / block / not-applicable |  |
| S3 Validate | pass / pass-with-caveats / skipped / block / not-applicable |  |
| S4 Inference/Synthesis | pass / pass-with-caveats / skipped / block / not-applicable |  |
| S5 Submit/Report | pass / pass-with-caveats / skipped / block / not-applicable |  |

## Gate Status

| gate | status | reason |
|---|---|---|
| context lock | pass / pass-with-caveats / skipped / block / not-applicable |  |
| entity normalization | pass / pass-with-caveats / skipped / block / not-applicable |  |
| safety/privacy | pass / pass-with-caveats / skipped / block / not-applicable |  |
| claim ledger | pass / pass-with-caveats / skipped / block / not-applicable |  |
| citation/provenance | pass / pass-with-caveats / skipped / block / not-applicable |  |
| biostats/reproducibility | pass / pass-with-caveats / skipped / block / not-applicable |  |
| contradiction red-team | pass / pass-with-caveats / skipped / block / not-applicable |  |
| post-write validation | pass / pass-with-caveats / skipped / block / not-applicable |  |

## Outputs

| output_id | path_or_summary | producer_role | verification_status |
|---|---|---|---|
| O-001 |  |  | verified / unverified / stale |

## Resume State

- Current stage:
- Next action:
- Open questions:
- Skipped gates requiring later review:
