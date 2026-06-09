---
description: "Biomedical evidence-audit team for claim-level verification, citation checks, provenance traceability, statistical audit, contradiction review, and safer claim rewriting"
argument-hint: "<claim, report path, draft paragraph, manuscript section, or agent output to audit>"
allowed-tools: Read, Glob, Grep, WebSearch, WebFetch, Bash
---

# Evidence Audit Team

User request: $ARGUMENTS

Audit the supplied biomedical claim, report, manuscript section, or agent output. Default to Korean.

## Required Preflight Contract

Before literature/database expansion, external tools, file writes, or final
rewriting, produce or update a compact preflight contract with:
`requested_alias`, `selected_mode`, `deliverable_type`, `evidence_scope`,
`risk_class`, `required_role_outputs`, `skipped_role_outputs_with_reason`,
`external_tools_allowed`, `file_write_plan`, `stop_criteria`, and
`checkpoint_plan`. If this contract is absent, label the result as a compact or
partial workflow rather than a full audit.

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

1. Run `protocol-context-locker` to define audit object, evidence scope, risk/safety/privacy class, and stop criteria.
2. Run `entity-normalizer` if entities, datasets, cohorts, trials, or assays are present.
3. Split the audit object into atomic claims and build `central-claim-ledger-evidence-graph`.
4. Maintain biomedical passport state for the audit object, selected claims,
   source/provenance/statistics/citation gate status, skipped gates, and resume
   checkpoints.
5. Check citations, PMIDs, DOIs, accessions, database records, software versions, and retrieval dates.
6. Map each claim to source evidence, local artifact, or missing provenance.
7. Audit statistical validity, experimental unit, multiple testing, survival endpoints, uncertainty, and reproducibility.
8. Audit causal language and confounding.
9. Audit study quality/risk of bias and applicability.
10. Audit safety, privacy, clinical-advice, dual-use, and patent-sensitive boundaries when relevant.
11. Red-team contradictions, negative evidence, and scope drift.
12. Produce safer rewritten claims only from verified ledger material.
13. Run the integrity gate and `post-write-final-validator` on the rewritten/audited final text.

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
2. protocol/context lock
3. atomic claim ledger / evidence graph
4. unsupported or contradicted claims
5. citation and provenance gaps
6. statistical/causal/risk-of-bias/safety issues
7. corrected wording
8. useful but excluded or not-ledger-verified claims
9. post-write validation verdict
10. biomedical passport status and integrity-gate failure-mode checklist status
11. unresolved checks
12. recommended next evidence needed
