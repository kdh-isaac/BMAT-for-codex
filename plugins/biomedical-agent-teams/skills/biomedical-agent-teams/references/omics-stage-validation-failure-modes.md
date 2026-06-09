# Omics Stage Validation Failure Modes

Use this reference with `omics-analysis-team`, omics audits, and public-data
research-council workflows.

## S1 Plan

Block or downgrade when:

- Accession, cohort version, assay, organism, or genome build is ambiguous.
- Biological unit is not defined.
- Contrast, endpoint, event/censor rule, grouping rule, or exclusion rule is
  missing.
- Confirmatory claims are requested after exploratory endpoint selection.

## S2 Setup

Block or downgrade when:

- Environment, package versions, or input file layout are not captured.
- Raw-data read-only rule is not enforceable.
- No small fixture, subset, or smoke-test path exists for high-memory work.

## S3 Validate

Block or downgrade when:

- Sample IDs, donors, batches, endpoints, censoring, or biological units do not
  align.
- Design matrix is singular or confounded with the main contrast.
- Single-cell analysis uses cells as independent replicates when donor-level
  inference is required.
- Survival analysis lacks event counts, censor definitions, or follow-up units.
- Smoke test fails or is skipped without explicit caveat.

## S4 Inference

Block or downgrade when:

- Multiple testing, effect size, confidence interval, event counts, or sample
  sizes are missing.
- Sensitivity analysis contradicts the primary conclusion.
- Model assumptions are not checked when they affect the conclusion.

## S5 Submit/Report

Block or downgrade when:

- Final claims are not traceable to source corpus, code, tables, or figures.
- Claim ledger is missing or stale.
- Report wording upgrades exploratory or proxy evidence into validated mechanism,
  predictive biomarker, clinical actionability, or CAR-T-intrinsic biology.

## Core Rule

If S3 Validate does not pass, S4/S5 results must be blocked, downgraded, or
explicitly labeled exploratory/not assessable.
