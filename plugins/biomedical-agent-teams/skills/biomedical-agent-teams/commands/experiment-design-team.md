---
description: "Biomedical experiment-design team for mechanistic validation, CAR cell therapy assays, controls, sample size, causal kill-tests, protocol logistics, and decision gates"
argument-hint: "<hypothesis or experimental objective>"
allowed-tools: Read, Glob, Grep, WebSearch, WebFetch, Bash
---

# Experiment Design Team

User request: $ARGUMENTS

Design a defensible validation plan. Default to Korean. Assume expert-level immunology and CAR cell therapy context.

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
experiment-design audit.

## Spawned Team Bundle Policy

This recipe may run as a selected team-level spawned subagent after the main
BMAT lead has narrowed the candidate hypothesis, claim, or design objective.
If spawned, run the internal roles inline, do not spawn child agents unless
`nested_spawn_policy` explicitly allows it, and return one formal
experiment-design team report. The report must include objective, experimental
unit, controls, readouts, sample-size logic, confounders, kill-tests,
feasibility gates, safety boundaries, confidence, files changed or `none`,
checks run or skipped, and a handoff for the central claim ledger.

## Team

- `protocol-context-locker`
- `life-science-lead-scientist`
- `entity-normalizer`
- `immunology-mechanism-critic`
- `causal-inference-confounder-analyst`
- `experimental-design-planner`
- `protocol-reagent-logistics-planner`
- `bayesian-decision-modeler`
- `biostats-repro-auditor`
- `risk-of-bias-study-quality-auditor`
- `safety-ethics-privacy-dual-use-auditor`
- `central-claim-ledger-evidence-graph`
- `contradiction-red-team`
- `figure-schematic-director`
- `claim-level-evidence-verifier`
- `citation-verifier`
- `scientific-writer-citation-agent`
- `post-write-final-validator`

## Workflow

1. Run runtime capability preflight to record browsing/database, file-write, shell, and spawned-subagent support.
2. Run `protocol-context-locker`: experimental objective, deliverable, safety/privacy class, feasibility boundary, approval gate, and stop criteria.
3. Run preliminary `entity-normalizer`.
4. Lock source corpus for source-backed rationale, methods, reagents, and prior-art claims.
5. Restate the hypothesis, mechanism, experimental unit, and success/failure criteria.
6. Build/update `central-claim-ledger-evidence-graph` for rationale, assumptions, and evidence gaps.
7. Identify the strongest causal kill-test and the most likely confounders.
8. Specify controls, biological replicates, technical replicates, donor/model considerations, randomization/blinding where feasible, and exclusion criteria.
9. Define readouts, timing, expected outcomes, alternative interpretations, and follow-up branches.
10. Add reagent/protocol/QC/logistics checks without inventing unknown reagent details.
11. Run safety/ethics/privacy/dual-use audit before operational details or external disclosure.
12. Use Bayesian decision modeling to prioritize the first experiment or staged validation route.
13. Run biostats, risk-of-bias/study-quality, red-team, claim, and citation gates before final recommendation.
14. For `deep` or `audit`, maintain workflow-run state and biomedical passport state and run the integrity gate before final recommendation.
15. Apply `references/independent-review-policy.md` before describing validation as independent.
16. Writer uses only verified ledger material; run `post-write-final-validator` before final output.
17. If this was a spawned team output, provide `spawned_team_output_status`,
    `nested_spawn_used`, and `ledger_handoff_claim_ids` before final wording.

## Mode Routing

| Mode | Agent selection and depth |
|---|---|
| `quick` | Restate hypothesis, experimental unit, core control, primary readout, and one strongest kill-test. Use compact final output. |
| `standard` | Add mechanism critic, causal/confounder review, design planner, sample-size logic, confounders, and staged go/no-go gates. Maintain compact claim ledger. |
| `deep` | Add protocol/reagent logistics, Bayesian decision model, biostats, risk-of-bias, contradiction red-team, safety auditor, claim/citation verification, figure plan, and post-write validation. |
| `audit` | Audit an existing plan for controls, biological unit, sample size, feasibility, safety/privacy, confounding, and claim strength before rewriting. |

Safety auditor is mandatory for operational wet-lab details, biosafety,
animal/human material, private project context, patent-sensitive strategy, or
external disclosure. Keep reagent/catalog specifics as unknown unless verified.

## Final Output

1. experimental objective
2. runtime capability preflight and downgrade rule
3. protocol/context lock and safety boundary
4. source corpus status
5. mechanistic rationale and claim boundary
6. central claim ledger summary
7. design overview
8. controls and sample size considerations
9. readouts and statistics
10. confounders and failure modes
11. protocol/reagent/QC logistics
12. expected outcomes and alternative interpretations
13. go/no-go gates
14. useful but excluded or not-ledger-verified claims
15. independent-review status
16. post-write validation verdict
17. workflow-run state, biomedical passport, and integrity-gate status
18. figure or panel plan if useful
19. spawned team output status and ledger handoff if this recipe was spawned
20. final workflow label and skipped gates with reasons
