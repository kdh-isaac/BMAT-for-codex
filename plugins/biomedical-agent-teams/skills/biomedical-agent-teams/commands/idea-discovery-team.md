---
description: "Biomedical idea-discovery team for CAR cell therapy hypotheses, mechanism critique, public-omics feasibility, causal audit, ranking, red-team review, and experimental planning"
argument-hint: "<research question or idea seed> [--mode quick|standard|deep|audit]"
allowed-tools: Read, Glob, Grep, WebSearch, WebFetch, Bash
---

# Idea Discovery Team

User request: $ARGUMENTS

Run a biomedical idea-discovery workflow. Default to Korean.

## Required Preflight Contract

Before literature/database expansion, external tools, file writes, or final
writing, produce or update a compact preflight contract with:
`requested_alias`, `selected_mode`, `deliverable_type`, `evidence_scope`,
`risk_class`, `required_role_outputs`, `skipped_role_outputs_with_reason`,
`external_tools_allowed`, `file_write_plan`, `stop_criteria`, and
`checkpoint_plan`. If this contract is absent, label the result as a compact or
partial workflow rather than a full idea-discovery audit.

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
2. Run preliminary `entity-normalizer` before literature or public database expansion.
3. Use a PI agenda gate: assumptions, agenda questions, privacy boundary, and success criteria.
4. Select the smallest useful lane set; do not involve every subagent by default.
5. Maintain `central-claim-ledger-evidence-graph` for all candidate hypotheses and supporting/weakening evidence.
6. Keep tumor-intrinsic, TME-intrinsic, product-intrinsic, and CAR-T-intrinsic evidence separate.
7. Use `public-omics-analyst` for feasibility. Escalate to `omics-analysis-team` only when organism, dataset/cohort, assay, contrast/endpoint, and output are specific.
8. Use `causal-inference-confounder-analyst` before causal or CAR-T-intrinsic claims.
9. Use `bayesian-decision-modeler` before recommending the first experiment.
10. Use `risk-of-bias-study-quality-auditor`, `safety-ethics-privacy-dual-use-auditor`, `contradiction-red-team`, and `claim-level-evidence-verifier` before final ranked recommendations.
11. For `deep` or `audit`, maintain biomedical passport state and run the integrity gate before final ranked recommendations.
12. The writer can use only verified ledger material; run `post-write-final-validator` before final output.
13. Do not fabricate PMIDs, DOIs, accessions, reagent details, trial status, or public database records.

## Mode Routing

| Mode | Agent selection and depth |
|---|---|
| `quick` | Generate a small number of hypotheses with `hypothesis-generator` and a light mechanism sanity check. Use compact final output and mark literature/database status as not source-checked unless verified. |
| `standard` | Add entity normalization, targeted literature/public-omics feasibility, mechanism critique, and hypothesis ranking. Maintain a compact claim ledger. |
| `deep` | Add causal/confounder review, Bayesian decision modeling, risk-of-bias, contradiction red-team, safety auditor when triggered, claim/citation verification, and post-write validation. |
| `audit` | Do not generate new ideas first. Audit the supplied idea or ranked list against evidence, provenance, causal language, and feasibility before recommending changes. |

For all ranked recommendations, record useful but unverified ideas as excluded
or not-ledger-verified claims rather than adding them to the final narrative.

## Final Output

1. normalized entities
2. protocol/context lock
3. agenda and assumptions
4. evidence lanes checked
5. central claim ledger summary
6. candidate hypotheses
7. ranked matrix with expected information gain
8. red-team and risk-of-bias downgrades
9. causal/confounder and safety/privacy boundary
10. recommended experiments or kill-tests
11. citation/provenance/claim verification status
12. useful but excluded or not-ledger-verified ideas
13. post-write validation verdict
14. biomedical passport and integrity-gate status
15. final claim-strength verdict
