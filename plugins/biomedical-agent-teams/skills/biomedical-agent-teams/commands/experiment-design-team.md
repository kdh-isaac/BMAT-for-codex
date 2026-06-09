---
description: "Biomedical experiment-design team for mechanistic validation, CAR cell therapy assays, controls, sample size, causal kill-tests, protocol logistics, and decision gates"
argument-hint: "<hypothesis or experimental objective>"
allowed-tools: Read, Glob, Grep, WebSearch, WebFetch, Bash
---

# Experiment Design Team

User request: $ARGUMENTS

Design a defensible validation plan. Default to Korean. Assume expert-level immunology and CAR cell therapy context.

## Required Preflight Contract

Before literature/database expansion, external tools, file writes, or final
writing, produce or update a compact preflight contract with:
`requested_alias`, `selected_mode`, `deliverable_type`, `evidence_scope`,
`risk_class`, `required_role_outputs`, `skipped_role_outputs_with_reason`,
`external_tools_allowed`, `file_write_plan`, `stop_criteria`, and
`checkpoint_plan`. If this contract is absent, label the result as a compact or
partial workflow rather than a full experiment-design audit.

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

1. Run `protocol-context-locker`: experimental objective, deliverable, safety/privacy class, feasibility boundary, approval gate, and stop criteria.
2. Run preliminary `entity-normalizer`.
3. Restate the hypothesis, mechanism, experimental unit, and success/failure criteria.
4. Build/update `central-claim-ledger-evidence-graph` for rationale, assumptions, and evidence gaps.
5. Identify the strongest causal kill-test and the most likely confounders.
6. Specify controls, biological replicates, technical replicates, donor/model considerations, randomization/blinding where feasible, and exclusion criteria.
7. Define readouts, timing, expected outcomes, alternative interpretations, and follow-up branches.
8. Add reagent/protocol/QC/logistics checks without inventing unknown reagent details.
9. Run safety/ethics/privacy/dual-use audit before operational details or external disclosure.
10. Use Bayesian decision modeling to prioritize the first experiment or staged validation route.
11. Run biostats, risk-of-bias/study-quality, red-team, claim, and citation gates before final recommendation.
12. For `deep` or `audit`, maintain biomedical passport state and run the integrity gate before final recommendation.
13. Writer uses only verified ledger material; run `post-write-final-validator` before final output.

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
2. protocol/context lock and safety boundary
3. mechanistic rationale and claim boundary
4. central claim ledger summary
5. design overview
6. controls and sample size considerations
7. readouts and statistics
8. confounders and failure modes
9. protocol/reagent/QC logistics
10. expected outcomes and alternative interpretations
11. go/no-go gates
12. useful but excluded or not-ledger-verified claims
13. post-write validation verdict
14. biomedical passport and integrity-gate status
15. figure or panel plan if useful
