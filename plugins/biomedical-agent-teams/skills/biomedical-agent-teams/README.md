# Biomedical Agent Teams

Codex biomedical agent-team bundle with a protocol lock, central claim ledger,
audit gates, writer restriction, and post-write final validation.

Codex uses `SKILL.md` as the router and treats `agents/*.md` as role prompts.

## v0.3.5 Updates

- Defines BMAT as lead-controlled and inline-first by default.
- Adds selective spawned review for high-confidence or auditable outputs without
  mechanically spawning every role.
- Adds dependency-aware team-level spawned workflows for broad decisions that
  genuinely benefit from parallel `idea-discovery-team`, `omics-analysis-team`,
  `translational-scout-team`, `experiment-design-team`, or
  `evidence-audit-team` bundles.
- Requires spawned teams to run internal roles inline and return one formal team
  report unless nested spawning is explicitly authorized.
- Adds `references/hybrid-execution-policy.md`,
  `templates/team-spawn-plan-template.md`, and execution-strategy fields in the
  preflight/workflow-run schemas.

## v0.3.2 Updates

- Adds benchmark hygiene guardrails for BioAgentBench-style tasks with hidden
  truth files, result archives, scoring scripts, reproduction scripts, and task
  Dockerfiles.
- Updates omics workflow rules to keep benchmark solve and scoring phases
  separated.

## v0.3.1 Updates

- Makes command-level final output requirements self-contained by adding final
  workflow label and skipped-gate reporting to every command recipe.
- Adds stronger package tests for router resource references, source-manifest
  command and agent roster existence, Markdown file references, and v0.3 schema
  sample payload validation.

## v0.3.0 Updates

- Adds runtime capability preflight with schema/template and Codex capability
  matrix reference.
- Adds workflow-run state with stage DAG and downgrade reasons.
- Promotes source corpus lock to a standalone schema/template.
- Adds hypothesis tournament schema/template/reference for idea discovery.
- Adds S1-S5 stage evaluation schema/template and omics validation failure modes.
- Adds independent-review policy for independent validation versus same-model
  separate-pass validation.
- Adds rollback/resume template for durable workflow artifacts.
- Updates all six command recipes to mention runtime capability, source lock,
  workflow state, stage validation where relevant, and independent-review
  status.

## v0.2.4 Updates

- Adds command-level preflight contract requirements to every alias workflow,
  so command recipes remain self-contained when read directly.
- Adds biomedical passport state to the evidence-audit workflow.
- Updates the source manifest workflow spine to include passport and integrity
  gates explicitly.
- Removes a zero-byte `.Rhistory` packaging artifact from `commands/`.

## v0.2.3 Updates

- Adds `contracts/` JSON schemas for preflight contracts, formal role outputs,
  biomedical passport state, omics run manifests, and post-write validation.
- Adds `templates/biomedical-passport-template.md` and
  `templates/integrity-gate-template.md`.
- Adds `references/contract-gated-workflows.md` and
  `references/biomedical-failure-modes.md`.
- Adds formal return contracts for the lead scientist, final writer, omics
  data curator, bulk/single-cell/pathway workers, omics code/provenance
  reviewers, and omics reporter.
- Requires biomedical passport and integrity-gate status for deep, audit, omics
  run, translational, manuscript-support, and long-running audit-bundle outputs
  when applicable.

## v0.2.1 Updates

- Adds explicit `quick`, `standard`, `deep`, and `audit` mode routing to prevent
  over-loading every agent by default.
- Adds `templates/claim-ledger-template.md` for fixed-field claim ledgers and
  excluded / not-ledger-verified claim tracking.
- Adds track-specific omics checklists for bulk, single-cell, survival, and
  multi-omics workflows.
- Resolves final output paths from the active workspace instead of hard-coding a
  macOS Google Drive path.
- Splits final responses into `compact final` and `audit bundle final` modes.

## Included Commands

- `/biomedical-research-council`: full PI-style research council.
- `/idea-discovery-team`: CAR cell therapy and immunology idea generation, ranking, red-team critique, and experimental planning.
- `/omics-analysis-team`: public-omics dataset curation, bulk/single-cell/survival/pathway workflows, review gates, and provenance reporting.
- `/evidence-audit-team`: claim-level evidence, citation, provenance, statistics, and contradiction audit.
- `/experiment-design-team`: mechanistic validation, controls, sample-size logic, protocol logistics, and decision gates.
- `/translational-scout-team`: trial landscape, operational feasibility, safety/regulatory flags, and IP/competitive positioning.

## Included Agents

- `life-science-lead-scientist`
- `protocol-context-locker`
- `entity-normalizer`
- `central-claim-ledger-evidence-graph`
- `life-science-literature-curator`
- `scientific-literature-researcher`
- `public-omics-analyst`
- `immunology-mechanism-critic`
- `hypothesis-generator`
- `hypothesis-ranker`
- `contradiction-red-team`
- `experimental-design-planner`
- `citation-verifier`
- `scientific-writer-citation-agent`
- `omics-data-curator`
- `omics-code-reviewer`
- `bulk-deg-analyst`
- `scrna-qc-specialist`
- `pathway-interpreter`
- `biostats-repro-auditor`
- `omics-provenance-validator`
- `omics-reporter`
- `scenario-playbook-router`
- `claim-level-evidence-verifier`
- `causal-inference-confounder-analyst`
- `risk-of-bias-study-quality-auditor`
- `safety-ethics-privacy-dual-use-auditor`
- `bayesian-decision-modeler`
- `clinical-trial-operations-scout`
- `grant-ip-landscape-scout`
- `protocol-reagent-logistics-planner`
- `provenance-traceability-architect`
- `figure-schematic-director`
- `model-card-dataset-card-writer`
- `post-write-final-validator`

## Use

```text
/idea-discovery-team TET2 KO + IL-21 armored CAR-T에서 trafficking receptor 조합 아이디어 발굴 --mode deep
/omics-analysis-team GSE248835 axi-cel pretreatment tumor RNA-seq에서 DUSP5 high/low DEG와 pathway 확인 --track bulk --mode plan
/omics-analysis-team TCGA에서 CD3-high solid tumor의 DUSP5 high/low 생존분석 계획 --track survival --mode plan
/experiment-design-team IL-21-STAT3-FOXO1 축이 CAR-T stem-like persistence를 증가시키는지 검증 --mode deep
/biomedical-research-council TET2 KO + IL-21 armored CAR-T persistence hypothesis --mode standard
```

## Safety Boundaries

- Treat raw data as read-only.
- Do not upload private data, PHI/PII, unpublished project text, or patent-sensitive details.
- Do not fabricate PMIDs, DOIs, accessions, reagent details, or database records.
- Separate evidence, inference, hypothesis, and speculation.
- Keep bulk public-omics proxy evidence separate from CAR-T-intrinsic mechanism claims.
- Use only tools available in the active runtime. Optional MCP/database tools must never be reported as used unless actually available and called.
- Final writing must use the verified central claim ledger, and post-write
  validation must block unsupported claims or missing uncertainty.
- Useful but unsupported points must remain in the excluded / not-ledger-verified
  section instead of being blended into the conclusion.
