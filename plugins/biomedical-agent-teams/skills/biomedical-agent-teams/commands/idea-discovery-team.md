---
description: "Biomedical idea-discovery team for CAR cell therapy hypotheses, mechanism critique, public-omics feasibility, causal audit, ranking, red-team review, and experimental planning"
argument-hint: "<research question or idea seed> [--mode quick|standard|deep|audit]"
allowed-tools: Read, Glob, Grep, WebSearch, WebFetch, Bash
---

# Idea Discovery Team

User request: $ARGUMENTS

Run a biomedical idea-discovery workflow. Default to Korean.

## Required Preflight Contract

Before literature/database expansion, external tools, file writes, spawned-agent
claims, or final writing, produce or update runtime capability preflight and a
compact preflight contract with:
`requested_alias`, `selected_mode`, `deliverable_type`, `evidence_scope`,
`risk_class`, `required_role_outputs`, `skipped_role_outputs_with_reason`,
`external_tools_allowed`, `file_write_plan`, `stop_criteria`, and
`checkpoint_plan`, `execution_strategy`, `spawned_review_plan`,
`team_spawn_plan`, `host_os`, `path_style`, `python_invocation`, `shell_family`,
`codex_runtime_capability_surface`, and `compute_budget`;
`all_role_spawn_avoidance_reason`, `nested_spawn_policy`, and
`post_team_audit_plan`. If runtime capability preflight or this contract is absent,
use the strongest downgraded workflow label supported by the produced artifacts
and runtime rather than a full idea-discovery audit.

If shell/code execution is unavailable, or if `scripts/bmat_validate.py` cannot
be run because shell/code execution is unavailable, record
`validator_unavailable_due_to_runtime` in preflight, workflow-run downgrade
reasons, and final skipped gates. Do not claim `Full protocol followed` in that
state.

## 1.0 Release-Gate Artifacts

For `standard`, `deep`, `audit`, generated-file, team-DAG, or source-backed
outputs, keep the 1.1.0 hard-gate artifacts aligned with the narrative:

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

## Spawned Team Bundle Policy

This recipe may run as a selected team-level spawned subagent in the first
parallel phase of a broad BMAT decision workflow. If spawned, run the internal
roles inline, do not spawn child agents unless `nested_spawn_policy` explicitly
allows it, and return one formal idea-discovery team report. The report must
include candidate hypotheses, duplicate collapse, ranking criteria, red-team
downgrades, expected-information-gain logic, useful excluded ideas, confidence,
files changed or `none`, checks run or skipped, and a handoff to the central
claim ledger.

## Use These Agents When Useful

- `protocol-context-locker`
- `life-science-lead-scientist`
- `scenario-playbook-router`
- `entity-normalizer`
- `life-science-literature-curator`
- `scientific-literature-researcher`
- `public-omics-analyst`
- `immunology-mechanism-critic`
- `causal-inference-confounder-analyst`
- `hypothesis-generator`
- `hypothesis-ranker`
- `meta-review-synthesizer`
- `bayesian-decision-modeler`
- `central-claim-ledger-evidence-graph`
- `contradiction-red-team`
- `risk-of-bias-study-quality-auditor`
- `safety-ethics-privacy-dual-use-auditor`
- `experimental-design-planner`
- `protocol-reagent-logistics-planner`
- `claim-level-evidence-verifier`
- `citation-verifier`
- `provenance-traceability-architect`
- `scientific-writer-citation-agent`
- `post-write-final-validator`

## Workflow

1. Start with `protocol-context-locker`: question schema, deliverable, evidence scope, risk/safety/privacy class, depth, stop criteria, and human approval gate.
2. Record runtime capabilities before claiming source-backed, tool-backed, or independent multi-agent work.
3. Run preliminary `entity-normalizer` before literature or public database expansion.
4. Lock source corpus for source-backed idea ranking, including PMID/DOI/accession/database record, version or retrieval date, inclusion status, and claim use.
5. Use a PI agenda gate: assumptions, agenda questions, privacy boundary, and success criteria.
6. Select the smallest useful lane set; do not involve every subagent by default.
7. Maintain `central-claim-ledger-evidence-graph` for all candidate hypotheses and supporting/weakening evidence.
8. Keep tumor-intrinsic, TME-intrinsic, product-intrinsic, and CAR-T-intrinsic evidence separate.
9. Use `public-omics-analyst` for feasibility. Escalate to `omics-analysis-team` only when organism, dataset/cohort, assay, contrast/endpoint, and output are specific.
10. Use `causal-inference-confounder-analyst` before causal or CAR-T-intrinsic claims.
11. Use `bayesian-decision-modeler` before recommending the first experiment.
12. Use `risk-of-bias-study-quality-auditor`, `safety-ethics-privacy-dual-use-auditor`, `contradiction-red-team`, and `claim-level-evidence-verifier` before final ranked recommendations.
13. For `standard` or `deep` candidate discovery, use the hypothesis tournament loop unless the user asked for a compact brainstorm.
14. For `deep` or `audit`, maintain workflow-run state and biomedical passport state and run the integrity gate before final ranked recommendations.
15. Apply `references/independent-review-policy.md` before describing validation as independent.
16. The writer can use only verified ledger material; run `post-write-final-validator` before final output.
17. Do not fabricate PMIDs, DOIs, accessions, reagent details, trial status, or public database records.
18. If this was a spawned team output, provide `spawned_team_output_status`,
    `nested_spawn_used`, and `ledger_handoff_claim_ids` before final ranking.

## Hypothesis Tournament Loop

For `standard` and `deep` idea discovery, use
`templates/hypothesis-tournament-template.md`,
`contracts/hypothesis-tournament.schema.json`, or the same field order:

1. R0 context/entity/source scope lock.
2. Set `iteration_budget`, `max_candidates`, and `max_pairwise_matches` from
   the selected mode unless the user explicitly overrides them.
3. For each iteration, run R1-R7:
   - R1 diverse hypothesis generation or regeneration from prior meta-review guidance, usually n=8-20 when budget allows.
   - R2 proximity clustering and duplicate collapse.
   - R3 novelty/plausibility filter.
   - R4 pairwise debate or tournament.
   - R5 evolution or recombination of surviving candidates.
   - R6 deterministic Elo aggregation when `scripts/bmat_elo.py` and shell/code execution are available; otherwise record qualitative ranking only and downgrade deterministic aggregation claims.
   - R7 contradiction red-team and claim ledger update.
4. Run R7b `meta-review-synthesizer` after each iteration to summarize
   recurring weakness patterns, unsupported-claim patterns, ranking
   sensitivity, and generation guidance for the next iteration.
5. Run R7c stop-criterion check. Continue only when the budget allows and rank
   stability, novelty exhaustion, unresolved blockers, and human stop criteria
   do not require stopping or blocking.
6. R8 final recommendation with kill-tests.

Rank by novelty, evidence strength, mechanistic specificity, assayability,
feasibility, safety/privacy/translational risk, CAR cell therapy relevance, and
expected information gain. Do not select winners by novelty alone.
Elo or Bradley-Terry ratings are prioritization aids only; never describe them
as evidence strength, biological proof, or validation.

Default compute budgets:

| Mode | iteration_budget | max_candidates | max_pairwise_matches |
|---|---:|---:|---:|
| `quick` | 1 | 4-6 | 0-4 |
| `standard` | 2 | 8-12 | 12-24 |
| `deep` | 3 | 12-20 | 24-60 |
| `audit` | 1-2 | supplied list | targeted |

## Mode Routing

| Mode | Agent selection and depth |
|---|---|
| `quick` | Generate a small number of hypotheses with `hypothesis-generator` and a light mechanism sanity check. Use compact final output and mark literature/database status as not source-checked unless verified. |
| `standard` | Add runtime capability preflight, entity normalization, source corpus lock for source-backed claims, targeted literature/public-omics feasibility, mechanism critique, hypothesis tournament/ranking, and compact claim ledger. |
| `deep` | Add workflow-run state, causal/confounder review, Bayesian decision modeling, risk-of-bias, contradiction red-team, safety auditor when triggered, claim/citation verification, independent-review status, and post-write validation. |
| `audit` | Do not generate new ideas first. Audit the supplied idea or ranked list against evidence, provenance, causal language, and feasibility before recommending changes. |

For all ranked recommendations, record useful but unverified ideas as excluded
or not-ledger-verified claims rather than adding them to the final narrative.

## Final Output

1. normalized entities
2. protocol/context lock
3. agenda and assumptions
4. evidence lanes checked
5. central claim ledger summary
6. source corpus status
7. candidate hypotheses
8. hypothesis tournament summary when used
9. ranked matrix with expected information gain
10. red-team and risk-of-bias downgrades
11. causal/confounder and safety/privacy boundary
12. recommended experiments or kill-tests
13. citation/provenance/claim verification status
14. useful but excluded or not-ledger-verified ideas
15. independent-review status
16. post-write validation verdict
17. workflow-run state, biomedical passport, and integrity-gate status
18. final claim-strength verdict
19. spawned team output status and ledger handoff if this recipe was spawned
20. final workflow label and skipped gates with reasons
