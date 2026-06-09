# Stage Evaluation Template

Use for omics run/audit, generated-file, long-running, or benchmark-like BMAT
workflows. The S1-S5 model is inspired by medical autoresearch stage evaluation
but is adapted for biomedical provenance and claim governance.

| field | value |
|---|---|
| evaluation_id | SE-YYYYMMDD-001 |
| workflow_alias |  |
| overall_verdict | pass / pass-with-caveats / block / not-assessable |
| downgrade_rule_applied |  |

| stage_id | stage_name | status | score | evidence | blocking_issues |
|---|---|---|---|---|---|
| S1 | Plan | pass / pass-with-caveats / skipped / block / not-applicable | 0-1 or blank | question, cohort, endpoint, biological unit, exclusion rules locked |  |
| S2 | Setup | pass / pass-with-caveats / skipped / block / not-applicable | 0-1 or blank | environment, package versions, fixture/subset, raw-data read-only rule |  |
| S3 | Validate | pass / pass-with-caveats / skipped / block / not-applicable | 0-1 or blank | sample metadata, design matrix, no leakage, smoke test |  |
| S4 | Inference | pass / pass-with-caveats / skipped / block / not-applicable | 0-1 or blank | full/subset run, effect sizes, CI/FDR/event counts, sensitivity |  |
| S5 | Submit/Report | pass / pass-with-caveats / skipped / block / not-applicable | 0-1 or blank | claim ledger, provenance, final report, post-write validation |  |

## Blocking Rule

If S3 Validate does not pass or pass with explicit caveats, S4 and S5 claims
must be blocked, downgraded to exploratory/not assessable, or explicitly marked
as not run.
