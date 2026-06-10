# Runtime Capability Preflight Template

Use before claiming any BMAT workflow depth. This records what the active Codex
runtime can actually do, instead of assuming that frontmatter or upstream
workflow wording grants unavailable tools.

| field | value |
|---|---|
| runtime_id | RCP-YYYYMMDD-001 |
| codex_client |  |
| plugin_version | 0.3.5 |
| workspace_root |  |
| web_search_available | yes / no / unknown / not-applicable |
| shell_available | yes / no / unknown / not-applicable |
| file_read_available | yes / no / unknown / not-applicable |
| file_write_available | yes / no / unknown / not-applicable |
| network_available | yes / no / unknown / not-applicable |
| spawned_subagents_supported | yes / no / unknown / not-applicable |
| spawned_review_supported | yes / no / unknown / not-applicable |
| team_level_spawn_supported | yes / no / unknown / not-applicable |
| sandbox_profile | none / read-only / workspace-write / unrestricted / unknown |
| downgrade_rule |  |

## Execution Strategy Capability

| field | value |
|---|---|
| execution_strategy | inline_only / inline_first_selective_review / team_level_selective_dag / user_requested_full_spawn / blocked |
| spawned_review_budget | 0 / 1 / 2 / 3 / 4 / user-approved |
| team_spawn_budget | 0 / 1 / 2 / 3 / 4 / user-approved |
| nested_spawn_allowed | false / true-with-explicit-approval |
| all_role_spawn_avoidance_reason |  |
| post_team_audit_plan |  |

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
If spawned subagents are unavailable, downgrade `inline_first_selective_review`
or `team_level_selective_dag` to `inline_only` or label the independent-review
claim as not performed.
