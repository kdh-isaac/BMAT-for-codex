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
`checkpoint_plan`. For v0.3.5, also record `execution_strategy`,
`spawned_review_plan`, `team_spawn_plan`,
`all_role_spawn_avoidance_reason`, `nested_spawn_policy`, and
`post_team_audit_plan`. If runtime capability preflight or this contract is absent,
label the result as a compact or partial workflow rather than a full
idea-discovery audit.

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

## Operating Rules

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
2. R1 diverse hypothesis generation, usually n=8-20 when budget allows.
3. R2 proximity clustering and duplicate collapse.
4. R3 novelty/plausibility filter.
5. R4 pairwise debate or tournament.
6. R5 evolution or recombination of surviving candidates.
7. R6 Bayesian expected information gain ranking.
8. R7 contradiction red-team and claim ledger update.
9. R8 final recommendation with kill-tests.

Rank by novelty, evidence strength, mechanistic specificity, assayability,
feasibility, safety/privacy/translational risk, CAR cell therapy relevance, and
expected information gain. Do not select winners by novelty alone.

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
