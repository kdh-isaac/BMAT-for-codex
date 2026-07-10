---
description: "Domain-neutral biomedical idea discovery with mechanism critique, evidence feasibility, causal audit, ranking, red-team review, and experiment planning"
argument-hint: "<research question or idea seed> [--mode quick|standard|deep|audit] [--domain-pack generic-biomedical|cell-therapy|immuno-oncology]"
allowed-tools: Read, Glob, Grep, WebSearch, WebFetch, Bash
---

# Idea Discovery Team

User request: $ARGUMENTS

Run a domain-neutral biomedical idea-discovery workflow. Default to Korean.
Do not assume a disease, modality, assay, cell type, or therapeutic platform
that the request does not provide.

## Domain-Pack Selection and Lazy Loading

Select exactly one domain pack before idea generation:

1. Use `generic-biomedical` by default. Its ranking axes are mechanism,
   causal identifiability, study quality, assayability, feasibility, safety,
   and expected information gain.
2. Select `cell-therapy` only when the user explicitly requests it or the
   supplied research question is explicitly about adoptive-cell products.
3. Select `immuno-oncology` only when the user explicitly requests it or the
   supplied research question explicitly concerns tumor-immune biology.
4. Do not infer a specialty pack from the user's profile, prior projects, or
   examples in documentation.
5. Load only `domain-packs/<selected_domain_pack>/domain-pack.json`, followed
   by the minimum referenced files needed for the selected lane. Never load all
   packs as a default bundle.

Record the following structured fields in both runtime preflight and run state:

- `selected_domain_pack`
- `domain_pack_version`
- `selection_reason`
- `domain_specific_assumptions`

The four fields must agree across artifacts. For `generic-biomedical`,
`domain_specific_assumptions` is an empty array. Specialty ranking axes and
specialty terminology are active only after the corresponding pack is selected.

## Required Preflight Contract

Complete the runtime capability preflight before literature/database expansion,
external tools, file writes, spawned-agent
claims, or final writing, produce or update runtime capability preflight and a
compact preflight contract with:
`requested_alias`, `selected_mode`, `deliverable_type`, `evidence_scope`,
`risk_class`, `required_role_outputs`, `skipped_role_outputs_with_reason`,
`external_tools_allowed`, `file_write_plan`, `stop_criteria`,
`checkpoint_plan`, `execution_strategy`, `spawned_review_plan`,
`team_spawn_plan`, `host_os`, `path_style`, `python_invocation`, `shell_family`,
`codex_runtime_capability_surface`, `compute_budget`,
`all_role_spawn_avoidance_reason`, `nested_spawn_policy`,
`post_team_audit_plan`, and the four domain-pack fields above.

If runtime capability preflight or this contract is absent, use the strongest
downgraded workflow label supported by the produced artifacts and runtime.
If shell/code execution is unavailable, or if `scripts/bmat_validate.py` cannot
run because of the runtime, record `validator_unavailable_due_to_runtime` in
preflight, workflow-run downgrade reasons, and final skipped gates. Do not claim
`Full protocol followed` in that state.

## 1.2 Release-Gate Artifacts

For `standard`, `deep`, `audit`, generated-file, team-DAG, or source-backed
outputs, keep these structured artifacts aligned with the narrative:

- `lead_decision.json` records alias, mode, tier, execution strategy, selected
  lanes, skipped lanes, review plans, and selected domain pack.
- `workflow_dag.json` records a planned command-to-agent DAG when used.
- `results_integration.json` records every literature, omics, reviewer,
  validator, tool, or human-review change to a claim, ranking, label, or wording.
- `tool_call_ledger.json` is required before saying a database, external
  service, local validator, spawned reviewer, or other tool was used.
- Included source-corpus rows carry resolvable `evidence_spans[]`; claim-ledger
  evidence edges point to those spans.
- Release claims require eligible `source_verification.json` rows and a
  consistent `claim_support_matrix.json`.
- Sample-mode golden-eval output is CI harness evidence only, never live-model
  validation evidence.
- Released review artifacts require stable input/output paths and SHA-256 in
  `review_artifact_manifest.json`.
- Regenerate `bundle_manifest.json` last so final artifact bytes and identities
  are hash-bound to the current run.

## Spawned Team Bundle Policy

This recipe may run as a selected team-level spawned subagent in the first
parallel phase of a broad BMAT workflow. If spawned, run internal roles inline,
do not spawn children unless `nested_spawn_policy` explicitly allows it, and
return one formal team report. Include candidates, duplicate-collapse reasons,
ranking criteria, red-team downgrades, expected-information-gain logic, useful
excluded ideas, confidence, files changed or `none`, checks run or skipped,
selected domain pack, and a central-claim-ledger handoff.

## Role Selection

Use the smallest useful set. Generic roles include:

- `protocol-context-locker`
- `life-science-lead-scientist`
- `scenario-playbook-router`
- `entity-normalizer`
- `life-science-literature-curator`
- `scientific-literature-researcher`
- `public-omics-analyst`
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
- `claim-level-evidence-verifier`
- `citation-verifier`
- `provenance-traceability-architect`
- `scientific-writer-citation-agent`
- `post-write-final-validator`

Load `immunology-mechanism-critic`, specialty interpretation boundaries,
marker panels, and specialty failure modes only when the selected pack calls
for them. A role name or prompt example does not override the selected pack.

## Workflow

1. Lock question, deliverable, evidence scope, risk/safety/privacy class,
   depth, stop criteria, and human approval gate.
2. Select and record one domain pack; lazy-load only its required resources.
3. Record runtime capabilities before claiming source-backed, tool-backed, or
   independent work.
4. Normalize entities without inventing unresolved identifiers.
5. Lock the source corpus for source-backed ranking, including stable IDs,
   version/retrieval date, inclusion status, evidence spans, and claim use.
6. Set the PI agenda: assumptions, questions, privacy boundary, and success criteria.
7. Select the smallest useful evidence and analysis lanes.
8. Maintain a central claim ledger for every candidate and all supporting,
   weakening, contradictory, or not-checked evidence.
9. Use public omics only for a specific organism, dataset/cohort, assay,
   contrast/endpoint, and output. Preserve the biological unit.
10. Run causal/confounder review before causal wording and Bayesian decision
    modeling before recommending the first experiment.
11. Apply only the selected pack's specialty axes and failure modes.
12. Run study-quality, safety, contradiction, and claim-support gates before
    final ranked recommendations.
13. For `standard` or `deep`, use the hypothesis tournament unless the user
    requested a compact brainstorm.
14. For `deep` or `audit`, maintain workflow/run/passport state and run the
    integrity gate.
15. Apply `references/independent-review-policy.md`; do not call same-model
    self-review independent.
16. The writer uses only eligible ledger material; run the post-write validator.
17. Never fabricate identifiers, reagent details, trial status, or database records.

## Hypothesis Tournament

Use `templates/hypothesis-tournament-template.md` and
`contracts/hypothesis-tournament.schema.json` where compatible.

1. Randomize candidate presentation order and use blinded candidate IDs for
   judge input; retain the random seed or deterministic ordering receipt.
2. Preserve every judge's score separately. Report aggregate score and judge
   disagreement as different quantities.
3. Record duplicate-collapse evidence and run an order-sensitivity check.
4. Keep qualitative ranking separate from Elo or Bradley-Terry ranking.
5. When feasible, estimate ranking uncertainty by bootstrap or another stated method.
6. Keep evidence strength and execution priority as separate axes.
7. Record same-model correlated-judgment limitations.
8. Treat any winner as a prioritization result, never biological proof or validation.

Run R0 context/entity/source lock; R1 generation; R2 clustering and duplicate
collapse; R3 novelty/plausibility screen; R4 blinded pairwise judging; R5
evolution/recombination; R6 qualitative and optional deterministic ranking; R7
contradiction red-team; R7b meta-review; R7c stop decision; and R8 recommendation
with kill-tests. Do not select a winner by novelty alone.

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
| `quick` | Generate a small candidate set with a light mechanism sanity check. Mark literature/database status not source-checked unless verified. |
| `standard` | Add runtime preflight, entity normalization, source lock, targeted evidence/omics feasibility, mechanism critique, tournament ranking, and compact claim ledger. |
| `deep` | Add causal/confounder review, decision modeling, study quality, contradiction red-team, safety audit when triggered, claim/citation verification, independent-review status, and post-write validation. |
| `audit` | Audit the supplied idea or ranked list against evidence, provenance, causal language, domain-pack fit, and feasibility before changes. |

## Final Output

1. selected domain pack, version, reason, and explicit assumptions
2. normalized entities and context lock
3. agenda, assumptions, and evidence lanes checked
4. claim ledger and source-corpus status
5. candidate hypotheses and tournament receipts
6. ranking matrix with evidence strength, execution priority, expected
   information gain, disagreement, and uncertainty kept separate
7. red-team, study-quality, causal/confounder, and safety downgrades
8. recommended experiments or kill-tests
9. claim/citation/provenance and independent-review status
10. useful excluded or not-ledger-verified ideas
11. post-write, workflow-state, passport, and integrity-gate status
12. spawned-team/ledger handoff when applicable
13. final workflow label and structured skipped gates
