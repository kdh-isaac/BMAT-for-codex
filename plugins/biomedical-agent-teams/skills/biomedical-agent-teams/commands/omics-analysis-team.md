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
spawned-agent claims, or final reporting, produce or update runtime capability
preflight and a compact preflight contract with:
`requested_alias`, `selected_mode`, `deliverable_type`, `evidence_scope`,
`risk_class`, `required_role_outputs`, `skipped_role_outputs_with_reason`,
`external_tools_allowed`, `file_write_plan`, `stop_criteria`, and
`checkpoint_plan`. For v0.3.5, also record `execution_strategy`,
`spawned_review_plan`, `team_spawn_plan`,
`all_role_spawn_avoidance_reason`, `nested_spawn_policy`, and
`post_team_audit_plan`. If runtime capability preflight or this contract is absent,
label the result as a compact or partial workflow rather than a full omics
analysis audit.

## Spawned Team Bundle Policy

This recipe may run as a selected team-level spawned subagent when omics
feasibility, plan, run, or audit can proceed independently from other BMAT
decision axes. If spawned, run the internal roles inline, do not spawn child
agents unless `nested_spawn_policy` explicitly allows it, and return one formal
omics team report. For full `run`, require S1-S3 locks before full analysis;
otherwise return plan or feasibility status. The report must include accession
and metadata locks, S1-S5 status, provenance, statistics, result-claim limits,
confidence, files changed or `none`, checks run or skipped, and a central
claim-ledger handoff.

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

1. Run runtime capability preflight: web/database access, shell/code execution,
   file write path, network, sandbox, and spawned-subagent support.
2. Run `protocol-context-locker`: analysis question schema, deliverable, evidence scope, risk/safety/privacy class, output path, budget/depth, stop criteria, and human approval gate.
3. Run preliminary `entity-normalizer` and lock metadata before analysis: accession, organism, assay, genome build/annotation, sample sheet, biological unit, group labels, endpoint/event/censor definitions where relevant.
4. Lock the source corpus for all accessions, database records, local files,
   software versions, and generated artifacts used in final claims.
5. Use `safety-ethics-privacy-dual-use-auditor` before external search, download, private sample handling, or controlled-access discussion.
6. Keep raw data read-only. Write derived outputs only to approved processed/results/reports/output folders.
7. For benchmark tasks such as BioAgentBench, do not expose truth files,
   downloaded `results/`, scoring scripts, reproduction scripts, or task
   Dockerfiles to the solving agent before the final candidate output is frozen.
8. Require a small-fixture, subset, or smoke test before full long-running or high-memory analysis.
9. Maintain S1-S5 stage evaluation using `templates/stage-evaluation-template.md` or `contracts/stage-evaluation.schema.json`.
10. Maintain `central-claim-ledger-evidence-graph` for results, source artifacts, uncertainty, contradictions, and blocked claims.
11. Maintain workflow-run state, an omics run manifest using `contracts/omics-run-manifest.schema.json` or the same field order, plus biomedical passport status for `run` and `audit` modes.
12. Run review gate before final reporting:
   - `omics-code-reviewer` for software/reproducibility/raw-data-safety.
   - `omics-provenance-validator` for design/statistics/provenance/claim proportionality.
   - `causal-inference-confounder-analyst` for association-versus-causality boundary.
   - `biostats-repro-auditor` for statistical validity.
   - `risk-of-bias-study-quality-auditor` for dataset/study quality and applicability.
13. Run `provenance-traceability-architect`, `model-card-dataset-card-writer`, `claim-level-evidence-verifier`, and `citation-verifier` before final deliverables.
14. Apply `references/independent-review-policy.md` before describing validation as independent.
15. `omics-reporter` can report only verified claim-ledger material.
16. Run the integrity gate and `post-write-final-validator` before final release.
17. Calibrate claims as exploratory versus validated, association versus causality, and prognostic versus predictive.
18. If this was a spawned team output, provide `spawned_team_output_status`,
    `nested_spawn_used`, and `ledger_handoff_claim_ids` before final reporting.

## Stage-Gated Run Model

Use S1-S5 for `plan`, `run`, and `audit` modes. A full run cannot advance to
validated S4/S5 claims unless S3 Validate passes or passes with explicit caveats.

| Stage | Required locks and checks | Blocking rule |
|---|---|---|
| S1 Plan | accession/cohort, organism, assay, biological unit, contrast/endpoint, inclusion/exclusion, statistics plan | block if question or metadata needed for analysis is ambiguous |
| S2 Setup | environment, package versions, raw-data read-only rule, fixture/subset or smoke-test path | block long-running run if no smoke-test path exists |
| S3 Validate | sample ID alignment, donor/biological-unit consistency, design matrix, leakage/pseudoreplication, event/censor checks, smoke test | if not pass, S4/S5 claims must be blocked or downgraded |
| S4 Inference | full/subset run, effect size, CI/FDR/event counts, sensitivity analysis | downgrade if uncertainty or multiplicity is missing |
| S5 Submit/Report | source corpus, omics manifest, claim ledger, provenance, final report, post-write validation | block if final claims are not traceable |

## Mode Routing

| Mode | Agent selection and checks |
|---|---|
| `plan` | Do not run full analysis. Lock runtime capabilities, accession/cohort/assay/contrast/endpoints, check public-access feasibility, define metadata/QC/statistics, and list S1-S3 validation and smoke tests. |
| `run` | Execute only after S1 Plan is specific. Require S2 setup and S3 validation/smoke test, write derived outputs only, then run S4 inference and S5 reporting with provenance, biostats, risk-of-bias, claim, citation, independent-review status, and final validation gates. |
| `audit` | Do not rerun full analysis unless explicitly requested. Inspect code/results/provenance/report, score S1-S5, verify sample IDs/statistics/claims, and return pass / pass-with-revisions / block. |

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
4. runtime capability preflight and downgrade rule
5. source corpus status
6. S1-S5 stage evaluation
7. inputs and data provenance
8. metadata and QC decisions
9. analysis commands and software versions
10. statistical methods and uncertainty
11. central claim ledger summary using `templates/claim-ledger-template.md`
12. causal/confounder and risk-of-bias boundary
13. key results and limitations
14. pathway or biological interpretation
15. useful but excluded or not-ledger-verified claims
16. independent-review, validation-gate, and post-write verdicts
17. generated files, manifest, audit bundle, and next step
18. workflow-run state, biomedical passport status, and omics run manifest status
19. spawned team output status and ledger handoff if this recipe was spawned
20. final workflow label and skipped gates with reasons
