# Connector Binding Matrix

Use this matrix before external browsing, database lookup, recurring loops, or
source-backed final wording. A connector listed here is a preferred source of
tool-backed corroboration only when the active Codex runtime exposes it and the
preflight contract allows that external use.

Do not report a connector as used unless it was actually called. If a preferred
connector is unavailable, record the downgrade reason and keep dependent claims
out of high-confidence final wording.

## Default Rules

- Use public unauthenticated sources before browser-authenticated or private
  connectors.
- Never send PHI/PII, controlled-access data, private sample IDs, unpublished
  project text, or patent-sensitive detail to external connectors without an
  explicit human gate.
- Lock retrieval date, identifier, inclusion status, and claim use in the
  source corpus for every source-backed final claim.
- Treat connector output as evidence input, not final truth. Map accepted facts
  into the central claim ledger before writing.

## Workflow Matrix

| workflow | primary connectors | optional connectors | required lock before use | reviewer lane |
|---|---|---|---|---|
| `biomedical-research-council` | PubMed/NCBI Entrez, DOI/Crossref | BioMCP, UniProt, Reactome, ClinicalTrials.gov, GEO/SRA | protocol/context, entity normalization, source-corpus plan | claim-level evidence, citation, contradiction |
| `idea-discovery-team` | PubMed/NCBI Entrez, public omics repository search | Reactome, UniProt, Open Targets, ChEMBL/PubChem | hypothesis scope, entity normalization, public-only or approved private boundary | contradiction, risk-of-bias, claim verifier |
| `omics-analysis-team --mode plan` | GEO/SRA/NCBI Datasets, ArrayExpress/BioStudies, CELLxGENE, TCGA/GDC | HPA, DepMap, cBioPortal | S1 plan fields and repository scope | omics provenance |
| `omics-analysis-team --mode run` | local files and repository APIs already locked in S1-S3 | package registries for version metadata | S1 Plan, S2 Setup, S3 Validate, raw-data read-only rule | code reviewer, omics provenance, biostats |
| `evidence-audit-team` | PubMed/NCBI Entrez, DOI/Crossref | ClinicalTrials.gov, repository APIs matching cited accessions | audit object, source IDs, claim split | claim verifier, citation verifier, contradiction |
| `experiment-design-team` | PubMed/NCBI Entrez, verified reagent or protocol sources when needed | Addgene, vendor pages only as fallback and marked lower-confidence | safety boundary, operational-detail gate, source-corpus plan | safety, biostats, risk-of-bias |
| `translational-scout-team` | ClinicalTrials.gov, PubMed/NCBI Entrez | regulatory/public pipeline pages, patent/prior-art search, company pages as lower-confidence | clinical/IP boundary, entity normalization, source date/version lock | safety, citation, contradiction, risk-of-bias |

## Recurring Loop Matrix

| loop | allowed default connectors | must not include | release gate |
|---|---|---|---|
| weekly literature watch | PubMed/NCBI Entrez, bioRxiv/medRxiv, DOI/Crossref, Europe PMC | unpublished project details, patent-sensitive queries, PHI/PII | `bmat_loop_check.py` plus citation/claim verification |
| public omics dataset watch | GEO/SRA, NCBI Datasets, ArrayExpress/BioStudies, CELLxGENE, TCGA/GDC, HPA | private sample IDs, controlled-access data | S1-S3 feasibility and omics provenance review |
| claim audit inbox | connectors matching attached source IDs | unapproved private drafts in external queries | source delta processed and reviewer objections resolved |
| hypothesis triage | PubMed, public omics repositories, pathway databases | proprietary strategy text unless approved | contradiction/risk objection resolution |

## Downgrade Labels

Use these short downgrade reasons in workflow-run or loop-state artifacts:

- `connector-unavailable`: a preferred connector was not available in runtime.
- `connector-not-authorized`: connector use would cross the privacy or human gate.
- `source-lock-incomplete`: connector output was not mapped to source corpus rows.
- `tool-corroboration-missing`: high-confidence wording lacks tool-backed or independent corroboration.
- `connector-output-not-reviewed`: connector evidence has not passed the relevant reviewer lane.
