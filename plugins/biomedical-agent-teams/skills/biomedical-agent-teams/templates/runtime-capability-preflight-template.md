# Runtime Capability Preflight Template

Use before claiming any BMAT workflow depth. This records what the active Codex
runtime can actually do, instead of assuming that frontmatter or upstream
workflow wording grants unavailable tools.

| field | value |
|---|---|
| runtime_id | RCP-YYYYMMDD-001 |
| codex_client |  |
| plugin_version | 0.8.0 |
| workspace_root |  |
| host_os | macOS / Windows / Linux / unknown |
| path_style | posix / windows / mixed / unknown / not-applicable |
| python_invocation | `python3` / `py -3` / `python` / unknown |
| shell_family | bash / zsh / powershell / cmd / none / unknown / not-applicable |
| codex_runtime_capability_surface | file, shell, web, MCP, apps, spawned reviewer, unknown |
| web_search_available | yes / no / unknown / not-applicable |
| shell_available | yes / no / unknown / not-applicable |
| file_read_available | yes / no / unknown / not-applicable |
| file_write_available | yes / no / unknown / not-applicable |
| network_available | yes / no / unknown / not-applicable |
| validator_cli_available | yes / no / unknown / not-applicable |
| validator_unavailable_reason | none / validator_unavailable_due_to_runtime / missing_bundle / missing_jsonschema / not-applicable |
| pairwise_ranking_script_available | yes / no / unknown / not-applicable |
| tool_registry_available | yes / no / unknown / not-applicable |
| results_integration_available | yes / no / unknown / not-applicable |
| iteration_budget_available | yes / no / unknown / not-applicable |
| spawned_subagents_supported | yes / no / unknown / not-applicable |
| spawned_review_supported | yes / no / unknown / not-applicable |
| team_level_spawn_supported | yes / no / unknown / not-applicable |
| sandbox_profile | none / read-only / workspace-write / unrestricted / unknown |
| label_ceiling_due_to_runtime | Full protocol followed / Contract-shaped artifact bundle / Compact standard workflow / Limited capability-downgraded workflow / Blocked |
| downgrade_rule |  |

## Cross-Platform Execution Note

For Codex plugin maintenance, prefer Python entrypoints invoked through the
active interpreter on both macOS/zsh and Windows/PowerShell. Inside package
scripts, call child Python processes with `sys.executable` and list-style
`subprocess.run(..., shell=False)`. Do not require Unix shebang execution or
Bash-only shell features for release-critical validators.

| field | value |
|---|---|
| path_portability_checked | yes / no / unknown / not-applicable |
| unicode_or_space_path_checked | yes / no / unknown / not-applicable |
| windows_powershell_command_available | yes / no / unknown / not-applicable |
| macos_zsh_command_available | yes / no / unknown / not-applicable |

## Compute Budget

| field | value |
|---|---|
| mode | quick / standard / deep / audit |
| iteration_budget |  |
| max_candidates |  |
| max_pairwise_matches |  |
| max_spawned_reviewers |  |
| max_external_queries |  |

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
If shell/code execution is unavailable, or if `scripts/bmat_validate.py` cannot
be run because shell/code execution is unavailable, record
`validator_unavailable_due_to_runtime` and set the runtime label ceiling below
`Full protocol followed`.
If spawned subagents are unavailable, downgrade `inline_first_selective_review`
or `team_level_selective_dag` to `inline_only` or label the independent-review
claim as not performed.
