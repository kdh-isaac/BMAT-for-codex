# Runtime Capability Preflight Template

Use before claiming any BMAT workflow depth. This records what the active Codex
runtime can actually do, instead of assuming that frontmatter or upstream
workflow wording grants unavailable tools.

| field | value |
|---|---|
| runtime_id | RCP-YYYYMMDD-001 |
| codex_client |  |
| plugin_version | 0.3.0 |
| workspace_root |  |
| web_search_available | yes / no / unknown / not-applicable |
| shell_available | yes / no / unknown / not-applicable |
| file_read_available | yes / no / unknown / not-applicable |
| file_write_available | yes / no / unknown / not-applicable |
| network_available | yes / no / unknown / not-applicable |
| spawned_subagents_supported | yes / no / unknown / not-applicable |
| sandbox_profile | none / read-only / workspace-write / unrestricted / unknown |
| downgrade_rule |  |

## External Biomedical Tools

| tool_or_database | availability | note |
|---|---|---|
| PubMed / NCBI Entrez | yes / no / unknown / not-applicable |  |
| ClinicalTrials.gov | yes / no / unknown / not-applicable |  |
| GEO / SRA | yes / no / unknown / not-applicable |  |
| UniProt | yes / no / unknown / not-applicable |  |
| ChEMBL / PubChem | yes / no / unknown / not-applicable |  |
| Other | yes / no / unknown / not-applicable |  |

## Downgrade Rule

If a required tool, spawned subagent, database, file-write path, or network
capability is unavailable, mark the affected gate as `skipped` or `block` in the
workflow run state and do not label the output `Full protocol followed`.
