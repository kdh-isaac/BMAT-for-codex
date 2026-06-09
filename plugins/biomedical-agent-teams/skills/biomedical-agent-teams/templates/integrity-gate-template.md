# Integrity Gate Template

Use this template before high-confidence final release, manuscript support,
translational scouting, omics reporting, or audit verdicts.

## Gate Verdict

| field | value |
|---|---|
| verdict | pass / pass-with-revisions / block |
| workflow_label_after_gate | Full protocol followed / Compact standard workflow / Biomedical Agent Teams-informed narrative review / Partial workflow; formal gates skipped / Blocked |
| release_ready_claim_strength | supported / partially supported / suggestive / exploratory / conflicting / unsupported / not assessable |

## Claim And Citation Checks

| check | status | issue | correction |
|---|---|---|---|
| unsupported final claims | pass / warn / suspected / not-applicable |  |  |
| citation-context drift | pass / warn / suspected / not-applicable |  |  |
| missing PMID/DOI/accession/version | pass / warn / suspected / not-applicable |  |  |
| provenance gap | pass / warn / suspected / not-applicable |  |  |

## Biomedical Failure Modes

Use `references/biomedical-failure-modes.md`.

| id | status | reason |
|---|---|---|
| FM1 fabricated or unverified identifier | pass / warn / suspected / not-applicable |  |
| FM2 citation-context drift | pass / warn / suspected / not-applicable |  |
| FM3 bulk-to-cell-intrinsic overclaim | pass / warn / suspected / not-applicable |  |
| FM4 sample or metadata leakage | pass / warn / suspected / not-applicable |  |
| FM5 post-hoc endpoint or threshold inflation | pass / warn / suspected / not-applicable |  |
| FM6 missing multiplicity or uncertainty | pass / warn / suspected / not-applicable |  |
| FM7 unsafe/private disclosure | pass / warn / suspected / not-applicable |  |
| FM8 clinical or translational overreach | pass / warn / suspected / not-applicable |  |
| FM9 provenance gap | pass / warn / suspected / not-applicable |  |
| FM10 reviewer/writer self-ratification | pass / warn / suspected / not-applicable |  |

## Required Corrections

| priority | correction | required_before_release |
|---|---|---|
| P0/P1/P2 |  | yes / no |
