---
description: "Clinical and translational scouting team for trial landscape, operational feasibility, safety/regulatory flags, IP/competitive positioning, and actionability boundaries"
argument-hint: "<target, therapy concept, biomarker, indication, or trial/translation question>"
allowed-tools: Read, Glob, Grep, WebSearch, WebFetch, Bash
---

# Translational Scout Team

User request: $ARGUMENTS

Evaluate translational feasibility without turning weak evidence into clinical advice. Default to Korean.

## Required Preflight Contract

Before literature/trial/IP expansion, external tools, file writes, or final
writing, produce or update a compact preflight contract with:
`requested_alias`, `selected_mode`, `deliverable_type`, `evidence_scope`,
`risk_class`, `required_role_outputs`, `skipped_role_outputs_with_reason`,
`external_tools_allowed`, `file_write_plan`, `stop_criteria`, and
`checkpoint_plan`. If this contract is absent, label the result as a compact or
partial workflow rather than a full translational audit.

## Team

- `protocol-context-locker`
- `entity-normalizer`
- `clinical-trial-operations-scout`
- `grant-ip-landscape-scout`
- `life-science-literature-curator`
- `central-claim-ledger-evidence-graph`
- `risk-of-bias-study-quality-auditor`
- `safety-ethics-privacy-dual-use-auditor`
- `causal-inference-confounder-analyst`
- `claim-level-evidence-verifier`
- `citation-verifier`
- `contradiction-red-team`
- `scientific-writer-citation-agent`
- `post-write-final-validator`

## Workflow

1. Run `protocol-context-locker`: translational question, deliverable, clinical/legal/regulatory boundary, evidence scope, risk/safety/privacy class, and approval gate.
2. Normalize disease, target, therapy type, biomarker, trial IDs, and comparator space.
3. Map trial landscape and operational feasibility.
4. Maintain `central-claim-ledger-evidence-graph` for each trial, biomarker, safety, IP, and competitive claim.
5. Check site-level and registry-status caveats when trial matching or recruitment is discussed.
6. Separate efficacy evidence, biomarker association, mechanism, safety, manufacturability, and competitive positioning.
7. Audit study quality/risk of bias, causal language, and evidence-to-decision uncertainty.
8. Run safety/ethics/privacy/dual-use audit for clinical, regulatory, IP, and patient-facing boundaries.
9. Flag regulatory, IP, and publication risks without providing legal or medical advice.
10. Verify claims and source identifiers before final synthesis.
11. For `standard`, `deep`, and `audit`, maintain biomedical passport state and run the integrity gate before final output.
12. Writer uses only verified ledger material; run `post-write-final-validator` before final output.

## Mode Routing

| Mode | Agent selection and depth |
|---|---|
| `quick` | Normalize target/indication/therapy concept, give non-advisory feasibility scan with explicit not-source-checked caveats if live verification was not done. |
| `standard` | Add literature/trial/IP landscape checks, central claim ledger, risk-of-bias, causal boundary, and claim/citation verification for key claims. |
| `deep` | Add full trial landscape, comparator space, operational bottlenecks, manufacturability/safety/regulatory/IP flags, contradiction red-team, safety auditor, and post-write validation. |
| `audit` | Audit an existing translational claim, deck, or strategy for source support, trial status, actionability overclaim, safety/regulatory/IP caveats, and clinical-advice boundaries. |

Safety auditor is mandatory for clinical, patient-facing, regulatory, patent/IP,
private project, controlled-access, or external-disclosure claims. Do not present
legal, regulatory, or medical advice; frame outputs as research support.

## Final Output

1. translational question
2. protocol/context lock
3. normalized entities and scope
4. central claim ledger summary
5. trial and competitive landscape
6. operational bottlenecks
7. safety/regulatory/IP flags
8. risk-of-bias and causal boundary
9. evidence strength and claim boundary
10. useful but excluded or not-ledger-verified claims
11. post-write validation verdict
12. biomedical passport and integrity-gate status
13. recommended next translational action
