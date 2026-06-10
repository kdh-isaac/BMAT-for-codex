---
description: "Biomedical evidence-audit team for claim-level verification, citation checks, provenance traceability, statistical audit, contradiction review, and safer claim rewriting"
argument-hint: "<claim, report path, draft paragraph, manuscript section, or agent output to audit>"
allowed-tools: Read, Glob, Grep, WebSearch, WebFetch, Bash
---

# Evidence Audit Team

User request: $ARGUMENTS

Audit the supplied biomedical claim, report, manuscript section, or agent output. Default to Korean.

## Required Preflight Contract

Before literature/database expansion, external tools, file writes, spawned-agent
claims, or final rewriting, produce or update runtime capability preflight and a
compact preflight contract with:
`requested_alias`, `selected_mode`, `deliverable_type`, `evidence_scope`,
`risk_class`, `required_role_outputs`, `skipped_role_outputs_with_reason`,
`external_tools_allowed`, `file_write_plan`, `stop_criteria`, and
`checkpoint_plan`. For v0.3.5, also record `execution_strategy`,
`spawned_review_plan`, `team_spawn_plan`,
`all_role_spawn_avoidance_reason`, `nested_spawn_policy`, and
`post_team_audit_plan`. If runtime capability preflight or this contract is absent,
label the result as a compact or partial workflow rather than a full audit.

## Spawned Team Bundle Policy

This recipe may run as a selected team-level spawned subagent when the main BMAT
lead needs an independent defensibility audit. If spawned, run the internal
roles inline, do not spawn child agents unless `nested_spawn_policy` explicitly
allows it, and return one formal evidence-audit team report. The report must
include audited claim IDs, source/provenance/statistical checks, contradiction
findings, confidence, files changed or `none`, checks run or skipped, and a
handoff for the main lead to merge into the central claim ledger.

## Team

- `protocol-context-locker`
- `entity-normalizer`
- `central-claim-ledger-evidence-graph`
- `claim-level-evidence-verifier`
- `citation-verifier`
- `provenance-traceability-architect`
- `biostats-repro-auditor`
- `risk-of-bias-study-quality-auditor`
- `causal-inference-confounder-analyst`
- `safety-ethics-privacy-dual-use-auditor`
- `contradiction-red-team`
- `scientific-writer-citation-agent`
- `post-write-final-validator`

## Workflow

1. Run runtime capability preflight to record source-check, file, shell, network, and spawned-subagent support.
2. Run `protocol-context-locker` to define audit object, evidence scope, risk/safety/privacy class, and stop criteria.
3. Run `entity-normalizer` if entities, datasets, cohorts, trials, or assays are present.
4. Lock the source corpus for citations, PMIDs, DOIs, accessions, registry IDs, database records, software versions, local files, and retrieval dates.
5. Split the audit object into atomic claims and build `central-claim-ledger-evidence-graph`.
6. Maintain workflow-run state and biomedical passport state for the audit object, selected claims,
   source/provenance/statistics/citation gate status, skipped gates, and resume
   checkpoints.
7. Check citations, PMIDs, DOIs, accessions, database records, software versions, and retrieval dates.
8. Map each claim to source evidence, local artifact, or missing provenance.
9. Audit statistical validity, experimental unit, multiple testing, survival endpoints, uncertainty, and reproducibility.
10. Audit causal language and confounding.
11. Audit study quality/risk of bias and applicability.
12. Audit safety, privacy, clinical-advice, dual-use, and patent-sensitive boundaries when relevant.
13. Red-team contradictions, negative evidence, and scope drift.
14. Apply `references/independent-review-policy.md`; do not call same-model validation independent.
15. Produce safer rewritten claims only from verified ledger material.
16. Run the integrity gate and `post-write-final-validator` on the rewritten/audited final text.
17. If this was a spawned team output, provide `spawned_team_output_status`,
    `nested_spawn_used`, and `ledger_handoff_claim_ids` before final wording.

## Audit Scope

Always use the fixed-field ledger template for this recipe. If the supplied
object is long, audit the highest-impact claims first and state the claim
selection rule. Do not rewrite or add claims that are not represented in the
ledger. Put useful but unsupported statements in `excluded_or_not_verified_claims`
with the minimum evidence needed to upgrade them.

Run `safety-ethics-privacy-dual-use-auditor` only when the audit object touches
private data, clinical advice, patent-sensitive strategy, controlled-access
datasets, wet-lab operational detail, external disclosure, or dual-use concerns;
otherwise state that no safety auditor trigger was present.

## Final Output

1. audit verdict: pass / pass-with-revisions / block
2. runtime capability preflight and downgrade rule
3. protocol/context lock
4. source corpus lock
5. atomic claim ledger / evidence graph
6. unsupported or contradicted claims
7. citation and provenance gaps
8. statistical/causal/risk-of-bias/safety issues
9. corrected wording
10. useful but excluded or not-ledger-verified claims
11. independent-review status
12. post-write validation verdict
13. workflow-run state, biomedical passport status, and integrity-gate failure-mode checklist status
14. unresolved checks
15. recommended next evidence needed
16. spawned team output status and ledger handoff if this recipe was spawned
17. final workflow label and skipped gates with reasons
