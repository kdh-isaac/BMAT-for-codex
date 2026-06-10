---
description: "Clinical and translational scouting team for trial landscape, operational feasibility, safety/regulatory flags, IP/competitive positioning, and actionability boundaries"
argument-hint: "<target, therapy concept, biomarker, indication, or trial/translation question>"
allowed-tools: Read, Glob, Grep, WebSearch, WebFetch, Bash
---

# Translational Scout Team

User request: $ARGUMENTS

Evaluate translational feasibility without turning weak evidence into clinical advice. Default to Korean.

## Required Preflight Contract

Before literature/trial/IP expansion, external tools, file writes,
spawned-agent claims, or final writing, produce or update runtime capability
preflight and a compact preflight contract with:
`requested_alias`, `selected_mode`, `deliverable_type`, `evidence_scope`,
`risk_class`, `required_role_outputs`, `skipped_role_outputs_with_reason`,
`external_tools_allowed`, `file_write_plan`, `stop_criteria`, and
`checkpoint_plan`. For v0.3.5, also record `execution_strategy`,
`spawned_review_plan`, `team_spawn_plan`,
`all_role_spawn_avoidance_reason`, `nested_spawn_policy`, and
`post_team_audit_plan`. If runtime capability preflight or this contract is absent,
label the result as a compact or partial workflow rather than a full
translational audit.

## Spawned Team Bundle Policy

This recipe may run as a selected team-level spawned subagent in the first
parallel phase when clinical, regulatory, IP, competitive, or operational
scouting is independent from mechanism or omics analysis. If spawned, run the
internal roles inline, do not spawn child agents unless `nested_spawn_policy`
explicitly allows it, and return one formal translational-scout team report.
The report must include entity/trial/source locks, translational flags,
clinical-advice boundary, IP/regulatory caveats, contradiction findings,
confidence, files changed or `none`, checks run or skipped, and a central
claim-ledger handoff.

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

1. Run runtime capability preflight to record live literature/trial/IP lookup, file, network, and spawned-subagent support.
2. Run `protocol-context-locker`: translational question, deliverable, clinical/legal/regulatory boundary, evidence scope, risk/safety/privacy class, and approval gate.
3. Normalize disease, target, therapy type, biomarker, trial IDs, and comparator space.
4. Lock source corpus for trial records, PMIDs/DOIs, IP/competitive sources, registry versions, and retrieval dates.
5. Map trial landscape and operational feasibility.
6. Maintain `central-claim-ledger-evidence-graph` for each trial, biomarker, safety, IP, and competitive claim.
7. Check site-level and registry-status caveats when trial matching or recruitment is discussed.
8. Separate efficacy evidence, biomarker association, mechanism, safety, manufacturability, and competitive positioning.
9. Audit study quality/risk of bias, causal language, and evidence-to-decision uncertainty.
10. Run safety/ethics/privacy/dual-use audit for clinical, regulatory, IP, and patient-facing boundaries.
11. Flag regulatory, IP, and publication risks without providing legal or medical advice.
12. Verify claims and source identifiers before final synthesis.
13. For `standard`, `deep`, and `audit`, maintain workflow-run state and biomedical passport state and run the integrity gate before final output.
14. Apply `references/independent-review-policy.md` before describing validation as independent.
15. Writer uses only verified ledger material; run `post-write-final-validator` before final output.
16. If this was a spawned team output, provide `spawned_team_output_status`,
    `nested_spawn_used`, and `ledger_handoff_claim_ids` before final synthesis.

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
2. runtime capability preflight and downgrade rule
3. protocol/context lock
4. normalized entities and scope
5. source corpus status
6. central claim ledger summary
7. trial and competitive landscape
8. operational bottlenecks
9. safety/regulatory/IP flags
10. risk-of-bias and causal boundary
11. evidence strength and claim boundary
12. useful but excluded or not-ledger-verified claims
13. independent-review status
14. post-write validation verdict
15. workflow-run state, biomedical passport, and integrity-gate status
16. recommended next translational action
17. spawned team output status and ledger handoff if this recipe was spawned
18. final workflow label and skipped gates with reasons
