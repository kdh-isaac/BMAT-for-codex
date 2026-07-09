---
description: "Public-omics analysis team for dataset curation, 10x/bulk/survival/pathway analysis, causal/statistical review, provenance traceability, and reporting"
argument-hint: "<public omics analysis goal> [--track bulk-rnaseq|tenx-gex|tenx-cellplex|tenx-citeseq|tenx-vdj|tenx-multiome|single-cell-other|survival|multi-omics] [--mode plan|run|audit] [--tier compact|full]"
allowed-tools: Read, Glob, Grep, WebSearch, WebFetch, Bash
---

# Omics Analysis Team

User request: $ARGUMENTS

Run a supervisor-worker-review-gate workflow for public omics. Default to Korean.
When a BMAT request requires substantive omics feasibility assessment, public
cohort analysis, code-bearing omics execution, or omics result audit, treat this
recipe as the primary omics workflow or the omics axis of a broader team DAG.

## Required Preflight Contract

Before external search, dataset access/download, code execution, file writes,
spawned-agent claims, or final reporting, produce or update runtime capability
preflight and a compact preflight contract with:
`requested_alias`, `selected_mode`, `deliverable_type`, `evidence_scope`,
`risk_class`, `required_role_outputs`, `skipped_role_outputs_with_reason`,
`external_tools_allowed`, `file_write_plan`, `stop_criteria`,
`checkpoint_plan`, `execution_strategy`, `spawned_review_plan`, `team_spawn_plan`,
`all_role_spawn_avoidance_reason`, `nested_spawn_policy`, and
`post_team_audit_plan`. If runtime capability preflight or this contract is absent,
use the strongest downgraded workflow label supported by the produced artifacts
and runtime rather than a full omics analysis audit.

If shell/code execution is unavailable, or if `scripts/bmat_validate.py` cannot
be run because shell/code execution is unavailable, record
`validator_unavailable_due_to_runtime` in preflight, workflow-run downgrade
reasons, and final skipped gates. Do not claim `Full protocol followed` in that
state.

## 1.1 Release-Gate Artifacts

For `standard`, `deep`, `audit`, generated-file, team-DAG, or source-backed
outputs, keep the 1.1.0 hard-gate artifacts aligned with the narrative:

- Use `lead_decision.json` for source-backed `standard`, `deep`, `audit`,
  team-DAG, or full-protocol runs before release; it must match the selected
  alias, mode, tier, execution strategy, selected lanes, skipped lanes, and
  review plans.
- Use `workflow_dag.json` when `execution_strategy=team_level_selective_dag`,
  when `scripts/bmat_run.py` scaffolds the run, or when the final answer claims
  a planned command-to-agent DAG.
- Use `results_integration.json` when literature, omics, reviewer, validator,
  tool, or human-review output changes a claim, ranking, label, or final wording.
- Use `tool_call_ledger.json` before saying a database, external service, local
  validator, spawned reviewer, or other tool was used; skipped, unavailable,
  blocked, or failed tools need an explicit downgrade reason.
- For included source-corpus rows, record `evidence_spans[]`; when possible,
  claim-ledger `evidence_edges[]` should point back to those spans.
- For release or full-protocol claims, maintain `source_verification.json` with
  pass/verified rows for every source-backed claim source and
  `claim_support_matrix.json` for high-confidence, tool-backed,
  analysis-backed, or blocked claims.
- Use claim-ledger `claim_profile` values only when the profile is supported by
  matching source, tool, analysis, or block evidence. Sample-mode golden eval
  output is CI harness evidence only, not live model validation evidence.
- Use `review_artifact_manifest.json` for released review artifacts so every
  reviewer or report artifact has a stable path, size, SHA-256, and claim link.

For `run` mode, do not silently set `spawned_review_plan.allowed=false` or
`budget=0` after S1-S3 locks. Default to `inline_first_selective_review` with a
minimum reviewer budget of 1 when the runtime supports spawned subagents or
tool-backed reviewer instances. Start that reviewer lane alongside S4
inference/S5 reporting when practical, after S1-S3 locks exist, so code,
provenance, and statistics findings can be merged before final wording. Select
at least one core reviewer from `omics-code-reviewer`,
`omics-provenance-validator`, and `biostats-repro-auditor`. If the run writes,
modifies, or materially depends on analysis scripts, notebooks, shell commands,
statistical code, or workflow configs, `omics-code-reviewer` is the default
required reviewer. Use two or more reviewers for donor-aware single-cell
contrasts, survival analyses, multi-omics integration, large generated scripts,
or manuscript-grade interpretation. If reviewer spawning or tool-backed review
is unavailable, privacy-blocked, explicitly out of scope, or the user requests a
compact inline-only run, record the skipped reviewer role, concrete reason, and
downgrade label in preflight, workflow-run state, and final reporting.

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
    For `tenx-*` and `bulk-rnaseq` tracks, the omics manifest is a v2 contract:
    record Cell Ranger/CellPlex provenance, raw/filtered matrix artifacts,
    `molecule_info.h5`, ambient/doublet/empty-droplet decisions, donor/sample
    mapping, pseudobulk policy, bulk quantifier/reference provenance, design
    formula, design-matrix rank check, count model, and multiplicity method as
    applicable.
    For release-bound omics runs, write `omics_metadata_check.json` using
    `contracts/omics-metadata-check.schema.json` and run
    `scripts/bmat_omics_metadata_check.py` against the selected track.
12. Run review gate before final reporting. In `run` mode, at least one core
   reviewer must be a spawned reviewer or tool-backed reviewer instance when
   runtime support is available, with the lane started alongside S4/S5 when
   practical:
   - `omics-code-reviewer` for software/reproducibility/raw-data-safety; default
     required reviewer for code-bearing omics runs.
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
| `run` | Execute only after S1 Plan is specific. Require S2 setup and S3 validation/smoke test, write derived outputs only, then run S4 inference and S5 reporting with provenance, biostats, risk-of-bias, claim, citation, independent-review status, and final validation gates. Default to at least one spawned or tool-backed core reviewer after S1-S3 and alongside S4/S5 when practical; select `omics-code-reviewer` by default for code-bearing runs. If unavailable or deliberately skipped, record a downgrade reason rather than treating inline review as equivalent. |
| `audit` | Do not rerun full analysis unless explicitly requested. Inspect code/results/provenance/report, score S1-S5, verify sample IDs/statistics/claims, and return pass / pass-with-revisions / block. |

## Track Checklists

Use the matching track checklist before analysis or reporting:

| Track | Required locks before run | Required review focus |
|---|---|---|
| `bulk-rnaseq` | FASTQ/count source, sample sheet, organism, genome build/annotation, quantifier, transcriptome reference, tx-to-gene method, biological unit, batch/covariates, design formula, design-rank check, contrast, multiple-testing plan | Count provenance, FastQC/MultiQC surface, tximport/tximeta or count import trace, design matrix validity, batch/confounding, count-model assumptions, effect size and FDR reporting |
| `tenx-gex` | Cell Ranger command/version, chemistry, raw/filtered matrix, `molecule_info.h5`, `web_summary.html`, donor/sample barcode mapping, biological unit, annotation release, QC thresholds, empty-droplet, ambient RNA, doublet, batch/integration, pseudobulk policy | Sample leakage, donor-aware pseudobulk for cross-sample DE, pseudo-replication, ambient marker contamination, doublets, mito/ribo thresholds, marker and GSEA interpretation boundaries |
| `tenx-cellplex` | `tenx-gex` locks plus multiplexing method, CMO/sample barcode mapping, demultiplexing confidence, singlet/multiplet policy | Donor/sample mismatch, cell hashing/CellPlex demultiplexing errors, multiplet carryover, pseudobulk unit correctness |
| `tenx-citeseq` | `tenx-gex` locks plus feature reference, ADT/protein feature handling, antibody panel provenance | ADT normalization/QC, feature barcode provenance, RNA-protein interpretation boundaries |
| `tenx-vdj` | Cell Ranger V(D)J command/version, contig annotations, clonotype calls, GEX linkage key when integrated | Clonotype overclaim, chain-pairing ambiguity, expansion versus function boundary |
| `tenx-multiome` | Cell Ranger ARC/multiome command/version, GEX/ATAC linkage, fragment and matrix artifacts, modality-specific QC | Cross-modality sample leakage, peak/gene linkage overclaim, modality batch handling |
| `single-cell-other` | Accession/files, platform, cell/sample mapping, donor/biological unit, cell type labels, QC thresholds, batch correction plan, cluster/DE contrast | Sample leakage, pseudo-replication, doublets, donor-aware statistics, marker and GSEA interpretation boundaries |
| `survival` | Cohort source/version, endpoint, event/censor definitions, follow-up time unit, inclusion/exclusion, covariates, grouping rule, event counts | Prognostic vs predictive boundary, censoring, proportional hazards, multiplicity, median survival/CI, number-at-risk feasibility |
| `multi-omics` | Matched sample IDs, modality versions, genome build consistency, missingness, integration method, biological unit, primary endpoint | Cross-modality leakage, batch/source mixing, dimensionality reduction overclaim, validation and sensitivity analyses |

If the requested track is unspecified, infer it only when the data type is clear
and record the reason. Otherwise, plan mode must record `track_ambiguous` and a
track ambiguity note, while run mode is blocked with
`OMICS_RUN_TRACK_REQUIRED`; never silently default to `single-cell-other`.

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
20. spawned reviewer status, including actual `spawned_agent_instances` or
    explicit skipped-core-reviewer downgrade reason
21. final workflow label and skipped gates with reasons
