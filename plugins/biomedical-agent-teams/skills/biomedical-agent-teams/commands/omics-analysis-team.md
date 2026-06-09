---
description: "Public-omics analysis team for dataset curation, bulk/single-cell/survival/pathway analysis, causal/statistical review, provenance traceability, and reporting"
argument-hint: "<public omics analysis goal> [--track bulk|single-cell|survival|multi-omics] [--mode plan|run|audit]"
allowed-tools: Read, Glob, Grep, WebSearch, WebFetch, Bash
---

# Omics Analysis Team

User request: $ARGUMENTS

Run a supervisor-worker-review-gate workflow for public omics. Default to Korean.

## Required Preflight Contract

Before external search, dataset access/download, code execution, file writes,
or final reporting, produce or update a compact preflight contract with:
`requested_alias`, `selected_mode`, `deliverable_type`, `evidence_scope`,
`risk_class`, `required_role_outputs`, `skipped_role_outputs_with_reason`,
`external_tools_allowed`, `file_write_plan`, `stop_criteria`, and
`checkpoint_plan`. If this contract is absent, label the result as a compact or
partial workflow rather than a full omics analysis audit.

## Team

- `protocol-context-locker`
- `entity-normalizer`
- `omics-data-curator`
- `public-omics-analyst`
- `omics-code-reviewer`
- `bulk-deg-analyst`
- `scrna-qc-specialist`
- `pathway-interpreter`
- `causal-inference-confounder-analyst`
- `biostats-repro-auditor`
- `risk-of-bias-study-quality-auditor`
- `omics-provenance-validator`
- `provenance-traceability-architect`
- `model-card-dataset-card-writer`
- `central-claim-ledger-evidence-graph`
- `claim-level-evidence-verifier`
- `contradiction-red-team`
- `safety-ethics-privacy-dual-use-auditor`
- `citation-verifier`
- `omics-reporter`
- `post-write-final-validator`

## Workflow

1. Run `protocol-context-locker`: analysis question schema, deliverable, evidence scope, risk/safety/privacy class, output path, budget/depth, stop criteria, and human approval gate.
2. Run preliminary `entity-normalizer` and lock metadata before analysis: accession, organism, assay, genome build/annotation, sample sheet, biological unit, group labels, endpoint/event/censor definitions where relevant.
3. Use `safety-ethics-privacy-dual-use-auditor` before external search, download, private sample handling, or controlled-access discussion.
4. Keep raw data read-only. Write derived outputs only to approved processed/results/reports/output folders.
5. Require a small-fixture, subset, or smoke test before full long-running or high-memory analysis.
6. Maintain `central-claim-ledger-evidence-graph` for results, source artifacts, uncertainty, contradictions, and blocked claims.
7. Maintain an omics run manifest using `contracts/omics-run-manifest.schema.json` or the same field order, plus biomedical passport status for `run` and `audit` modes.
8. Run review gate before final reporting:
   - `omics-code-reviewer` for software/reproducibility/raw-data-safety.
   - `omics-provenance-validator` for design/statistics/provenance/claim proportionality.
   - `causal-inference-confounder-analyst` for association-versus-causality boundary.
   - `biostats-repro-auditor` for statistical validity.
   - `risk-of-bias-study-quality-auditor` for dataset/study quality and applicability.
9. Run `provenance-traceability-architect`, `model-card-dataset-card-writer`, `claim-level-evidence-verifier`, and `citation-verifier` before final deliverables.
10. `omics-reporter` can report only verified claim-ledger material.
11. Run the integrity gate and `post-write-final-validator` before final release.
12. Calibrate claims as exploratory versus validated, association versus causality, and prognostic versus predictive.

## Mode Routing

| Mode | Agent selection and checks |
|---|---|
| `plan` | Do not run full analysis. Lock accession/cohort/assay/contrast/endpoints, check public-access feasibility, define metadata/QC/statistics, and list smoke tests. |
| `run` | Execute only after the plan is specific. Require a small fixture/subset/smoke test, write derived outputs only, then run code, provenance, biostats, risk-of-bias, claim, citation, and final validation gates. |
| `audit` | Do not rerun full analysis unless explicitly requested. Inspect code/results/provenance/report, verify sample IDs/statistics/claims, and return pass / pass-with-revisions / block. |

## Track Checklists

Use the matching track checklist before analysis or reporting:

| Track | Required locks before run | Required review focus |
|---|---|---|
| `bulk` | Organism, assay platform, count vs normalized matrix, genome build/annotation, sample sheet, biological unit, batch/covariates, contrast, multiple-testing plan | Design matrix validity, batch/confounding, count-model assumptions, independent validation, effect size and FDR reporting |
| `single-cell` | Accession/files, chemistry/platform, cell barcode/sample mapping, donor/biological unit, cell type labels, QC thresholds, batch correction plan, cluster/DE contrast | Sample leakage, pseudo-replication, doublets, mito/ribo thresholds, donor-aware statistics, marker and GSEA interpretation boundaries |
| `survival` | Cohort source/version, endpoint, event/censor definitions, follow-up time unit, inclusion/exclusion, covariates, grouping rule, event counts | Prognostic vs predictive boundary, censoring, proportional hazards, multiplicity, median survival/CI, number-at-risk feasibility |
| `multi-omics` | Matched sample IDs, modality versions, genome build consistency, missingness, integration method, biological unit, primary endpoint | Cross-modality leakage, batch/source mixing, dimensionality reduction overclaim, validation and sensitivity analyses |

If the requested track is unspecified, infer it only when the data type is clear;
otherwise return a plan-mode ambiguity note instead of running.

## Final Output

For `plan`, return a compact plan with locked inputs, required metadata,
analysis steps, smoke test, and stop criteria. For `run` or `audit`, return an
audit bundle:

1. bottom-line conclusion
2. protocol/context lock and approvals
3. track checklist status
4. inputs and data provenance
5. metadata and QC decisions
6. analysis commands and software versions
7. statistical methods and uncertainty
8. central claim ledger summary using `templates/claim-ledger-template.md`
9. causal/confounder and risk-of-bias boundary
10. key results and limitations
11. pathway or biological interpretation
12. useful but excluded or not-ledger-verified claims
13. validation-gate and post-write verdicts
14. generated files, manifest, audit bundle, and next step
15. biomedical passport status and omics run manifest status
