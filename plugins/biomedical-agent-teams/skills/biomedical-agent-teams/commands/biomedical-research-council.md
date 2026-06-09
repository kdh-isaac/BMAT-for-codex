---
description: "Full biomedical research council with protocol lock, hypothesis generation, evidence synthesis, public-omics feasibility, causal/statistical audit, experiment design, translation, central claim ledger, and final validation"
argument-hint: "<research question, hypothesis seed, or project goal> [--mode quick|standard|deep|audit|translation]"
allowed-tools: Read, Glob, Grep, WebSearch, WebFetch, Bash
---

# Biomedical Research Council

User request: $ARGUMENTS

Run a lead-controlled biomedical research council. Default to Korean. Treat the user as an expert in immunology, CAR cell therapy, and public-omics analysis.

## v0.2.3 Spine

1. Run `protocol-context-locker` first to lock question schema, deliverable, evidence scope, risk/safety/privacy class, depth/budget/stop criteria, and human approval gate.
2. Run preliminary `entity-normalizer` before literature, omics, clinical, or IP expansion.
3. Use `life-science-lead-scientist` and `scenario-playbook-router` to build the task graph and select the smallest useful specialist lanes.
4. Maintain `central-claim-ledger-evidence-graph` throughout. Specialist lanes must hand off atomic claims, sources/artifacts, uncertainty, and contradictions to the ledger.
5. For `deep`, `audit`, translational, manuscript-support, generated-file, or long-running work, maintain a biomedical passport using `templates/biomedical-passport-template.md` or the same field order.
6. Run required audit gates before synthesis: claim boundary, causal/confounder, biostats/reproducibility, provenance, risk-of-bias/study quality, safety/ethics/privacy/dual-use, contradiction red-team, and uncertainty/evidence-to-decision.
7. Run pre-synthesis `claim-level-evidence-verifier` and `citation-verifier`.
8. `scientific-writer-citation-agent` may use only verified claim-ledger material.
9. Run the integrity gate and `post-write-final-validator` before final output for high-confidence source-backed deliverables.

## Required Preflight Contract

Before literature/database expansion, external tools, file writes, or final
writing, produce or maintain a compact preflight contract:

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

If this contract is absent, the final output must be labeled as a compact or
partial workflow, not as a full Biomedical Research Council audit.

## Routing

First emulate `scenario-playbook-router` and record the lane-selection rationale
to choose the smallest useful playbook:

- `mechanism-review`
- `public-omics-feasibility`
- `omics-analysis`
- `hypothesis-ranking`
- `evidence-audit`
- `wet-lab-validation`
- `clinical-translation`
- `manuscript-or-grant`

If the request is broad, use `standard`. If the request asks for high-confidence recommendations, use `deep`. If the request asks whether a claim/report is defensible, use `audit`.

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
| `standard` | Quick set plus the relevant literature / omics / mechanism / experiment / translation lane, compact `central-claim-ledger-evidence-graph`, targeted `claim-level-evidence-verifier` and `citation-verifier`. |
| `deep` | Standard set plus required audit gates: causal/confounder, biostats when data are analyzed, provenance, risk-of-bias, contradiction red-team, safety auditor when the trigger criteria are met, and post-write validation. |
| `audit` | Treat the request as a defensibility audit: decompose claims, build the fixed-field ledger, verify citations/provenance/statistics/causal language, then return pass / pass-with-revisions / block. |

Use `templates/claim-ledger-template.md` for `standard`, `deep`, and `audit`.
For quick conceptual answers, preserve claim boundaries without forcing a full
audit bundle unless the user asks for high confidence.

## Minimum Artifacts By Mode

| Mode | Required artifacts before final |
|---|---|
| `quick` | Compact protocol line, entity normalization when relevant, selected lane, explicit claim boundary, compact final validator note. |
| `standard` | Preflight contract, entity normalization table, selected lane rationale, compact central claim ledger, targeted claim-level evidence verification, citation metadata checks for cited PMID/DOI/accession, skipped deep/audit gate list. |
| `deep` | All standard artifacts plus safety auditor output or `safe_mode_note` when triggered, causal/confounder review for causal/mechanistic claims, risk-of-bias/study-quality review for upgraded claims, provenance review for public omics/database conclusions, post-write final validator output. |
| `audit` | Fixed-field claim ledger, claim verifier output for each atomic claim, citation verifier output for each source, contradiction red-team output, post-write final validator output, pass / pass-with-revisions / block verdict. |

For deep/audit outputs, include biomedical passport status and integrity-gate
verdict. If either is skipped, downgrade the final workflow label.

## Mandatory Gates

1. Lock protocol/context-of-use before specialist work.
2. Normalize entities before source expansion.
3. Keep tumor-intrinsic, TME-intrinsic, product-intrinsic, and CAR-T-intrinsic evidence separate.
4. Distinguish association, mechanism, prognostic biomarker, predictive biomarker, and therapeutic actionability.
5. Before a strong conclusion, update `central-claim-ledger-evidence-graph` and run `claim-level-evidence-verifier` plus `citation-verifier`.
6. Before reporting omics/survival conclusions, run `provenance-traceability-architect`, `biostats-repro-auditor`, and `risk-of-bias-study-quality-auditor`.
7. Before recommending experiments or translation, run `causal-inference-confounder-analyst`, `contradiction-red-team`, `safety-ethics-privacy-dual-use-auditor`, and `experimental-design-planner`.
8. Before final release, run the integrity gate and `post-write-final-validator`.

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
3. normalized entities
4. protocol/context lock summary
5. central claim ledger / evidence graph summary
6. evidence matrix by lane
7. hypothesis ranking or decision table
8. causal/statistical/provenance/study-quality/safety caveats
9. recommended kill-tests or next analyses
10. clinical/IP/operational implications when relevant
11. claim and citation verification status
12. useful but excluded or not-ledger-verified claims
13. post-write validation verdict
14. biomedical passport and integrity-gate status
15. final claim-strength verdict
16. final workflow label and skipped gates with reasons

Final workflow label must be one of:

- `Full protocol followed`
- `Compact standard workflow`
- `Biomedical Agent Teams-informed narrative review`
- `Partial workflow; formal gates skipped`
- `Blocked`

## Post-Write Self-Check

Before final release, answer yes/no internally or visibly:

1. Did `protocol-context-locker` produce a lock?
2. Was safety auditor or `safe_mode_note` produced when triggered?
3. Was entity normalization completed before source expansion?
4. Was lane selection by lead/router recorded?
5. Was a central claim ledger maintained before writing?
6. Were claim-level evidence and citation checks performed before synthesis?
7. Did final writing use only ledger-approved material?
8. Did `post-write-final-validator` run?
9. Are skipped gates explicitly listed?
10. Was biomedical passport state produced when required?
11. Did the integrity gate check BMAT-specific failure modes when required?
12. Is the final workflow label accurate?

If any answer is "no", downgrade the final workflow label and avoid claiming
full council or audit compliance.
