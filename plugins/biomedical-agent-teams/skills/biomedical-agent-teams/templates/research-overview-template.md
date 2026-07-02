# Research Overview Template

Use this as the one-page BMAT synthesis after meta-review, results integration,
and ledger update. The overview is a reader-facing summary, not a new analysis
surface.

Do not introduce new claims in the overview. Use only the central claim ledger,
source corpus, results integration rows, workflow-run state, and meta-review
notes. If those surfaces are missing, mark the field as unknown, partial, or
downgraded rather than inferring.

## Header

| field | value |
|---|---|
| overview_id | RO-YYYYMMDD-001 |
| plugin_version | 0.8.8 |
| workflow_run_id |  |
| alias | biomedical-research-council / idea-discovery-team / omics-analysis-team / evidence-audit-team / experiment-design-team / translational-scout-team |
| source_basis | central claim ledger / source corpus / results integration / meta-review / partial |
| final_label | Full protocol followed / Contract-shaped artifact bundle / Compact standard workflow / Biomedical Agent Teams-informed narrative review / Limited capability-downgraded workflow / Partial workflow; formal gates skipped / Blocked |

## One-Page Overview

| section | content |
|---|---|
| Question and decision |  |
| Locked entities and scope |  |
| Data and source surface |  |
| Top supported findings or candidates |  |
| Contradictions, nulls, and QC blockers |  |
| Claim ceiling and downgrade reasons |  |
| Compute budget and execution strategy |  |
| Team DAG or reviewer lanes used |  |
| Next experiment, analysis, or audit step |  |

## Claim-Trace Table

| overview_statement | claim_ids | source_refs | result_rows | meta_review_note | confidence | limitation |
|---|---|---|---|---|---|---|
|  | CL-001 | SC-001 | RI-ROW-001 | MR-001 | high / moderate / low / insufficient |  |

## Output Discipline

- Keep the overview short enough to be pasted into a final answer.
- Prefer concrete claim IDs, source IDs, and result row IDs over narrative
  assertions.
- Exclude material that is plausible but absent from the ledger.
- State unresolved contradictions and source gaps explicitly.
- Do not upgrade the workflow label beyond the validator, reviewer, source, and
  runtime capability evidence.
