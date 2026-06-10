---
description: "Full biomedical research council with protocol lock, hypothesis generation, evidence synthesis, public-omics feasibility, causal/statistical audit, experiment design, translation, central claim ledger, and final validation"
argument-hint: "<research question, hypothesis seed, or project goal> [--mode quick|standard|deep|audit]"
allowed-tools: Read, Glob, Grep, WebSearch, WebFetch, Bash
---

# Biomedical Research Council

User request: $ARGUMENTS

Run a lead-controlled biomedical research council. Default to Korean. Treat the user as an expert in immunology, CAR cell therapy, and public-omics analysis.

## v0.3.5 Spine

1. Run runtime capability preflight first: record active Codex support for web,
   shell/code execution, file read/write, network/database access, spawned
   subagents, sandbox, and downgrade rule.
2. Run `protocol-context-locker` to lock question schema, deliverable, evidence scope, risk/safety/privacy class, depth/budget/stop criteria, and human approval gate.
3. Run preliminary `entity-normalizer` before literature, omics, clinical, or IP expansion.
4. Lock the source corpus for source-backed outputs using stable identifiers,
   retrieval dates/versions, inclusion status, and claim use.
5. Use `life-science-lead-scientist` and `scenario-playbook-router` to build the task graph and select the smallest useful specialist lanes.
6. Lock the execution strategy using `references/hybrid-execution-policy.md`: default inline-first, add selective spawned review or dependency-aware team-level spawned workflows only when they materially improve review quality.
7. If `team_level_selective_dag` is selected, run dependency-aware command-level
   team bundles before final ledger synthesis; Phase 2 teams must wait for
   narrowed candidate claims or designs.
8. Maintain `central-claim-ledger-evidence-graph` throughout. Specialist lanes and spawned teams must hand off atomic claims, sources/artifacts, uncertainty, and contradictions to the ledger.
9. For `deep`, `audit`, translational, manuscript-support, generated-file, or long-running work, maintain workflow-run state and biomedical passport state using `templates/workflow-run-template.md` and `templates/biomedical-passport-template.md` or the same field order.
10. For omics, generated-file, or long-running workflows, run S1-S5 stage evaluation and downgrade or block inference/reporting when S3 Validate does not pass.
11. Run required audit gates before synthesis: claim boundary, causal/confounder, biostats/reproducibility, provenance, risk-of-bias/study quality, safety/ethics/privacy/dual-use, contradiction red-team, and uncertainty/evidence-to-decision.
12. If `inline_first_selective_review` is selected, run spawned reviewer lanes
    after ledger claims exist and merge accepted reviewer findings back to the
    ledger.
13. Run pre-synthesis `claim-level-evidence-verifier` and `citation-verifier`.
14. `scientific-writer-citation-agent` may use only verified claim-ledger material.
15. Apply `references/independent-review-policy.md` before using independent-review wording.
16. Run the integrity gate and `post-write-final-validator` before final output for high-confidence source-backed deliverables.

## Required Preflight Contract

Before literature/database expansion, external tools, file writes, code
execution, spawned-agent claims, or final writing, produce or maintain runtime
capability preflight and then a compact preflight contract:

1. `requested_alias`
2. `selected_mode`: quick / standard / deep / audit
3. `deliverable_type`
4. `evidence_scope`
5. `risk_class`
6. `required_role_outputs`
7. `skipped_role_outputs_with_reason`
8. `external_tools_allowed`
9. `file_write_plan`
10. `stop_criteria`
11. `checkpoint_plan`
12. `execution_strategy`
13. `spawned_review_plan`
14. `team_spawn_plan`
15. `all_role_spawn_avoidance_reason`
16. `nested_spawn_policy`
17. `post_team_audit_plan`

If runtime capability preflight or this contract is absent, the final output
must be labeled as a compact or partial workflow, not as a full Biomedical
Research Council audit.

## Hybrid Execution Policy

Default to a lead-controlled inline workflow. The lead/router keeps protocol
lock, source scope, central claim ledger, workflow-run state, and final
synthesis. Use spawned subagents selectively:

- `inline_first_selective_review`: run the main workflow inline, then spawn
  only reviewer roles needed for independence, such as evidence verification,
  citation checking, contradiction red-team, biostats, provenance, or
  risk-of-bias review.
- `team_level_selective_dag`: when the question has independent decision axes,
  spawn selected command-level teams as workflow bundles. Initial independent
  teams may include `idea-discovery-team`, `omics-analysis-team` in plan or
  feasibility mode, and `translational-scout-team`. Dependent teams such as
  `experiment-design-team` and `evidence-audit-team` usually run after the main
  lead narrows candidate claims or designs.

Do not spawn every role or every team by default. A spawned team runs its own
internal recipe inline and returns one formal team report; nested spawning is
off unless the user explicitly authorizes it. Use
`templates/team-spawn-plan-template.md` for the team dependency graph and
review handoff.

## Routing

First emulate `scenario-playbook-router` and record the lane-selection and
execution-strategy rationale to choose the smallest useful playbook:

- `mechanism-review`
- `public-omics-feasibility`
- `omics-analysis`
- `hypothesis-ranking`
- `evidence-audit`
- `wet-lab-validation`
- `clinical-translation`
- `manuscript-or-grant`

If the request is broad, use `standard`. If the request asks for high-confidence recommendations, use `deep`. If the request asks whether a claim/report is defensible, use `audit`.
For translational requests, use the `clinical-translation` playbook inside
`standard`, `deep`, or `audit`, or route to `translational-scout-team` when the
task is primarily trial, regulatory, IP, or operational scouting.

## Core Team

- `protocol-context-locker` - context-of-use, scope, risk, approval gate.
- `life-science-lead-scientist` - agenda, routing, final synthesis.
- `scenario-playbook-router` - playbook and gate selection.
- `entity-normalizer` - identifiers and scope.
- `life-science-literature-curator` and `scientific-literature-researcher` - literature and full-text evidence.
- `public-omics-analyst` and `omics-data-curator` - public database feasibility.
- `immunology-mechanism-critic` and `pathway-interpreter` - mechanism and pathway interpretation.
- `causal-inference-confounder-analyst` - association/causality boundary.
- `hypothesis-generator` and `hypothesis-ranker` - candidate generation and prioritization.
- `bayesian-decision-modeler` - expected information gain and go/no-go ranking.
- `experimental-design-planner` and `protocol-reagent-logistics-planner` - validation plan and execution constraints.
- `clinical-trial-operations-scout` and `grant-ip-landscape-scout` - translation, competition, strategy.
- `contradiction-red-team` - negative evidence and overclaim review.
- `central-claim-ledger-evidence-graph` - atomic claim ledger and evidence graph.
- `claim-level-evidence-verifier`, `citation-verifier`, `provenance-traceability-architect`, `risk-of-bias-study-quality-auditor`, and `safety-ethics-privacy-dual-use-auditor` - final audit.
- `scientific-writer-citation-agent` - concise final report from verified ledger only.
- `post-write-final-validator` - final unsupported-claim, citation, uncertainty, provenance, and safety check.

Do not involve every agent by default. Involve only the lanes required by the selected playbook.

## Mode Routing

Use the smallest defensible mode:

| Mode | Agent selection |
|---|---|
| `quick` | `protocol-context-locker`, optional `entity-normalizer`, `life-science-lead-scientist`, one specialist lane, compact final validator check. |
| `standard` | Quick set plus the relevant literature / omics / mechanism / experiment / translation lane, compact `central-claim-ledger-evidence-graph`, targeted `claim-level-evidence-verifier` and `citation-verifier`; optionally spawn one selected reviewer or team when independence materially helps. |
| `deep` | Standard set plus required audit gates: causal/confounder, biostats when data are analyzed, provenance, risk-of-bias, contradiction red-team, safety auditor when the trigger criteria are met, and post-write validation; optionally use a 1-3 output selective review or team DAG. |
| `audit` | Treat the request as a defensibility audit: decompose claims, build the fixed-field ledger, verify citations/provenance/statistics/causal language, then return pass / pass-with-revisions / block; use spawned review for independent audit lanes when available. |

Use `templates/claim-ledger-template.md` for `standard`, `deep`, and `audit`.
For quick conceptual answers, preserve claim boundaries without forcing a full
audit bundle unless the user asks for high confidence.

## Minimum Artifacts By Mode

| Mode | Required artifacts before final |
|---|---|
| `quick` | Compact protocol line, entity normalization when relevant, selected lane, explicit claim boundary, compact final validator note. |
| `standard` | Runtime capability preflight, preflight contract, entity normalization table, source corpus lock for source-backed claims, selected lane rationale, compact central claim ledger, targeted claim-level evidence verification, citation metadata checks for cited PMID/DOI/accession, skipped deep/audit gate list. |
| `deep` | All standard artifacts plus workflow-run state, safety auditor output or `safe_mode_note` when triggered, causal/confounder review for causal/mechanistic claims, risk-of-bias/study-quality review for upgraded claims, provenance review for public omics/database conclusions, stage evaluation when relevant, independent-review status, post-write final validator output. |
| `audit` | Runtime capability preflight, workflow-run state, source corpus lock, fixed-field claim ledger, claim verifier output for each atomic claim, citation verifier output for each source, contradiction red-team output, independent-review status, post-write final validator output, pass / pass-with-revisions / block verdict. |

For deep/audit outputs, include biomedical passport status and integrity-gate
verdict. If either is skipped, downgrade the final workflow label.

## Mandatory Gates

1. Lock protocol/context-of-use before specialist work.
2. Record actual runtime capabilities before claiming tool-backed execution.
3. Normalize entities before source expansion.
4. Lock source corpus before source-backed final wording.
5. Keep tumor-intrinsic, TME-intrinsic, product-intrinsic, and CAR-T-intrinsic evidence separate.
6. Distinguish association, mechanism, prognostic biomarker, predictive biomarker, and therapeutic actionability.
7. Before a strong conclusion, update `central-claim-ledger-evidence-graph` and run `claim-level-evidence-verifier` plus `citation-verifier`.
8. Before reporting omics/survival conclusions, run S1-S5 stage evaluation, `provenance-traceability-architect`, `biostats-repro-auditor`, and `risk-of-bias-study-quality-auditor`.
9. Before recommending experiments or translation, run `causal-inference-confounder-analyst`, `contradiction-red-team`, `safety-ethics-privacy-dual-use-auditor`, and `experimental-design-planner`.
10. Before final release, apply independent-review policy, run the integrity gate, and run `post-write-final-validator`.

## Safe Mode Note

If a safety-auditor trigger is present but the task is low-risk and public-only,
produce a one-paragraph `safe_mode_note` before external browsing/database calls
or file writes. State: no private/unpublished data used; no PHI/PII or
controlled-access data sent externally; whether external browsing/database calls
are used; whether files will be written; and whether wet-lab or clinical
guidance is conceptual only.

## Final Output

Return `compact final` for quick or narrow standard answers. Return `audit
bundle final` for deep, audit, translational, omics, manuscript, source-backed,
or high-confidence outputs.

Audit bundle final includes:

1. working conclusion
2. selected playbook, role prompts read, formal role outputs produced, tool calls used, and spawned subagents if any
3. runtime capability preflight, execution strategy, spawn plan, and downgrade rule
4. normalized entities
5. protocol/context lock summary
6. source corpus lock status
7. central claim ledger / evidence graph summary
8. evidence matrix by lane
9. hypothesis ranking, tournament summary, or decision table when relevant
10. stage evaluation status when relevant
11. causal/statistical/provenance/study-quality/safety caveats
12. recommended kill-tests or next analyses
13. clinical/IP/operational implications when relevant
14. claim and citation verification status
15. useful but excluded or not-ledger-verified claims
16. independent-review status
17. spawned review/team output summary and post-team audit status
18. post-write validation verdict
19. workflow-run state, biomedical passport, and integrity-gate status
20. final claim-strength verdict
21. final workflow label and skipped gates with reasons

Final workflow label must be one of:

- `Full protocol followed`
- `Compact standard workflow`
- `Biomedical Agent Teams-informed narrative review`
- `Partial workflow; formal gates skipped`
- `Blocked`

## Post-Write Self-Check

Before final release, answer yes/no internally or visibly:

1. Was runtime capability preflight recorded?
2. Did `protocol-context-locker` produce a lock?
3. Was safety auditor or `safe_mode_note` produced when triggered?
4. Was entity normalization completed before source expansion?
5. Was source corpus locked for source-backed claims?
6. Was lane selection by lead/router recorded?
7. Was a central claim ledger maintained before writing?
8. Were S1-S5 stage checks performed when relevant?
9. Were claim-level evidence and citation checks performed before synthesis?
10. Did final writing use only ledger-approved material?
11. Was independent-review wording used only when justified?
12. Did `post-write-final-validator` run?
13. Are skipped gates explicitly listed?
14. Was workflow-run state and biomedical passport state produced when required?
15. Did the integrity gate check BMAT-specific failure modes when required?
16. Is the final workflow label accurate?
17. Was execution strategy recorded and justified?
18. If spawned reviewers or teams were used, did each return a formal output and
    did the lead map accepted findings back to the central claim ledger?
19. If broad spawning was requested, was all-role/team spawning avoidance or
    nested-spawn authorization documented?

If any answer is "no", downgrade the final workflow label and avoid claiming
full council or audit compliance.
