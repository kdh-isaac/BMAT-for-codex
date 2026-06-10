# Source Corpus Template

Use before source-backed claims, evidence audits, omics reports, translational
scans, manuscript support, or high-confidence recommendations. Lock source
identity and retrieval context before the final claim ledger is written.

| source_id | source_type | identifier | title_or_name | version_or_retrieval_date | query_or_origin | inclusion_status | claim_use | checked_by | limitations |
|---|---|---|---|---|---|---|---|---|---|
| S-001 | _(example)_ PMID | 34567890 | IL-21 reprograms CAR-T metabolism | retr. 2026-06-10 | PubMed MCP get_article_metadata | included | supports CL-001 | citation-verifier (tool-corroborated) | single cohort, in vitro only |
| S-002 | PMID / DOI / accession / NCT / database-record / local-file / analysis-artifact / software / other |  |  |  |  | included / excluded / not-checked / blocked |  |  |  |

## Source Lock Rules

- Use stable identifiers whenever possible: PMID, DOI, accession, NCT, database
  record URL, software version, file path, or artifact checksum.
- Record retrieval date or version for current, clinical, database, package, and
  public-omics claims.
- Mark sources as `not-checked` rather than implying verification when browsing
  or database access was unavailable.
- Excluded sources may inform uncertainty but must not support
  `allowed_final_wording` unless rechecked and included.
