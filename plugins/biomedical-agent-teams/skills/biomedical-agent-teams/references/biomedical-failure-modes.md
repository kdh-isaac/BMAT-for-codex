# Biomedical Failure Modes

Use this reference during post-write validation, evidence audit, omics reporting,
and translational scouting. A `suspected` status in a high-confidence deliverable
requires `block` or `pass-with-revisions` until corrected or explicitly
downgraded.

| id | failure mode | typical trigger | required response |
|---|---|---|---|
| FM1 | fabricated or unverified identifier | PMID, DOI, accession, NCT, reagent, catalog number, software behavior cannot be verified | remove, verify, or mark as not checked |
| FM2 | citation-context drift | source exists but does not support the exact species, model, endpoint, cell type, or causal scope | rewrite the claim or downgrade evidence relation |
| FM3 | bulk-to-cell-intrinsic overclaim | tumor bulk, TME proxy, or public cohort signal is presented as CAR-T-intrinsic mechanism | separate proxy evidence from cell-intrinsic claims |
| FM4 | sample or metadata leakage | sample IDs, donors, batches, endpoints, censoring, or biological units are ambiguous or mixed | block analysis claims until metadata is reconciled |
| FM5 | post-hoc endpoint or threshold inflation | grouping, endpoint, contrast, or exclusion rule chosen after seeing results | label exploratory and require validation |
| FM6 | missing multiplicity or uncertainty | multiple testing, pairwise comparisons, CI, event counts, or sample sizes omitted | add corrected statistics or downgrade |
| FM7 | unsafe/private disclosure | PHI/PII, private sample IDs, unpublished data, patent-sensitive details, or controlled-access data are sent externally or exposed | redact, stop external use, and require approval |
| FM8 | clinical or translational overreach | research evidence becomes patient-facing advice, actionability, or trial recommendation | restate as research support and add clinician/regulatory boundary |
| FM9 | provenance gap | final claim, figure, table, or recommendation cannot be traced to source/tool/file/artifact | add traceability or exclude the claim |
| FM10 | reviewer/writer self-ratification | the same pass writes the claim and validates it without criteria or dissent preservation | require independent audit section or downgrade workflow label |

## Status Vocabulary

- `pass`: no material issue found.
- `warn`: issue is present but does not change the main conclusion after
  correction or caveat.
- `suspected`: evidence is insufficient to trust the claim as written.
- `not-applicable`: failure mode does not apply to the current deliverable.
