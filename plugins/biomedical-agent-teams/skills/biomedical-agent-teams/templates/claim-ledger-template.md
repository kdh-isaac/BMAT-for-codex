# Claim Ledger Template

Use this template for source-backed biomedical outputs, omics reports,
evidence audits, translational scans, manuscript support, and deep research
council runs. Keep rows atomic: one claim per row.

| claim_id | claim_profile | atomic_claim | claim_type | context | source_ids | tool_ids | result_ids | evidence_relation | entailment_verdict | scope_match | uncertainty | audit_status | allowed_final_wording | block_reason |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CL-001 | source_backed | _(example)_ IL-21 sustains STAT3 phosphorylation in human CD8 CAR-T over 14 d | mechanistic | human; CD8 CAR-T; in vitro; pSTAT3 flow; biological unit = donor | S-001 |  |  | direct | supports | species=match; cell_type=match; assay=match; endpoint=match | moderate + single cohort, n=4 donors | pass-with-caveats | IL-21 maintained STAT3 activation in CD8 CAR-T across 14 days in vitro (n=4 donors) |  |
| CL-002 | draft / source_backed / tool_backed / analysis_backed / high_confidence / blocked |  | descriptive / mechanistic / causal / prognostic / predictive / therapeutic / translational / feasibility / safety / IP-strategy / method / limitation | species; cell type; disease/model; assay; endpoint; cohort/dataset; perturbation; biological unit | source IDs from source_corpus.json | successful tool IDs when tool_backed | result IDs when analysis_backed | direct / indirect / proxy / contradictory / missing / not checked | supports / weakly_supports / contradicts / irrelevant / not_checked | species/cell_type/assay/endpoint = match / partial / mismatch / not-applicable | low / moderate / high + reason | unchecked / needs audit / pass / pass-with-caveats / block | final-safe wording or empty if blocked | reason required when claim_profile=blocked |

For JSON ledgers, use `claim_profile` values exactly as defined by
`contracts/claim-ledger.schema.json`: `draft`, `source_backed`, `tool_backed`,
`analysis_backed`, `high_confidence`, or `blocked`. In release mode,
`source_backed` and `high_confidence` rows also need source IDs, entailment,
scope, uncertainty, audit status, and final-safe wording. `tool_backed` and
`analysis_backed` rows need matching `tool_call_ledger.json` and/or
`results_integration.json` evidence. `blocked` rows must not appear in
`final.md`.

## Excluded Or Not Verified Claims

Use this section for useful ideas, interpretations, or claims that should not
enter the final conclusion yet.

| item_id | excluded_or_not_verified_claim | reason_excluded | minimum_evidence_needed |
|---|---|---|---|
| EX-001 |  | not source-checked / unsupported / proxy-only / contradicted / provenance gap / unsafe to disclose |  |

## Writer Rule

The final writer may use only `allowed_final_wording` from rows with
`audit_status` of `pass` or `pass-with-caveats`. Any other useful point stays in
`Excluded Or Not Verified Claims`.
