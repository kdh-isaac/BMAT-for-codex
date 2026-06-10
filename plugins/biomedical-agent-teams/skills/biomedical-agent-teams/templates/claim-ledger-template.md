# Claim Ledger Template

Use this template for source-backed biomedical outputs, omics reports,
evidence audits, translational scans, manuscript support, and deep research
council runs. Keep rows atomic: one claim per row.

| claim_id | atomic_claim | claim_type | context | evidence_items | evidence_relation | uncertainty | audit_status | allowed_final_wording |
|---|---|---|---|---|---|---|---|---|
| CL-001 | _(example)_ IL-21 sustains STAT3 phosphorylation in human CD8 CAR-T over 14 d | mechanistic | human; CD8 CAR-T; in vitro; pSTAT3 flow; biological unit = donor | PMID 34567890 (retr. 2026-06-10); GSE190000 | direct | moderate + single cohort, n=4 donors | pass-with-caveats | IL-21 maintained STAT3 activation in CD8 CAR-T across 14 days in vitro (n=4 donors) |
| CL-002 |  | descriptive / mechanistic / causal / prognostic / predictive / therapeutic / translational / feasibility / safety / IP-strategy / method / limitation | species; cell type; disease/model; assay; endpoint; cohort/dataset; perturbation; biological unit | PMID/DOI/accession/NCT/file/artifact/retrieval date | direct / indirect / proxy / contradictory / missing / not checked | low / moderate / high + reason | unchecked / needs audit / pass / pass-with-caveats / block | final-safe wording or empty if blocked |

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
