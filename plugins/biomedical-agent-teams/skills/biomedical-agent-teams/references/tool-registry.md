# Tool Registry

Use this registry when a BMAT workflow needs external lookup, local validators,
MCP-backed tools, spawned reviewers, or human review. The registry is a
governance surface, not proof that a tool ran.

The machine-readable registry is `references/tool-registry.json`. Release
checks use that JSON file for allowed `tool_id` values; keep this Markdown table
and the JSON registry synchronized.

## Release Rule

Do not report a tool as used unless the workflow has a logged tool-use row, a
source-corpus row when the tool provides evidence, and a results integration row
when the tool changes a claim, ranking, result interpretation, or release label.

If a preferred tool is unavailable, blocked by privacy, outside budget, or not
authorized, record a downgrade reason instead of silently substituting it with
unsupported narrative reasoning.

## Registry Fields

| field | meaning |
|---|---|
| tool_id | Stable local name for the tool, connector, script, validator, or reviewer surface. |
| tool_family | literature, omics, clinical, chemistry, pathway, local-validator, reviewer, human-review, other. |
| workflow_aliases | BMAT aliases where the tool is normally relevant. |
| invocation_surface | Codex tool, MCP tool, browser/web, local script, shell command, spawned reviewer, human review, or unavailable. |
| allowed_data_class | public-only, local-private-approved, deidentified-only, no-PHI, not-applicable. |
| source_corpus_required | Whether evidence from the tool must create or update source corpus rows. |
| results_integration_required | Whether outputs that affect claims must be mapped through results integration. |
| default_downgrade_reason | Short reason to use when the tool cannot be used. |

## Default Registry

| tool_id | tool_family | workflow_aliases | invocation_surface | allowed_data_class | source_corpus_required | results_integration_required | default_downgrade_reason |
|---|---|---|---|---|---|---|---|
| pubmed-ncbi-entrez | literature | biomedical-research-council, idea-discovery-team, evidence-audit-team, experiment-design-team, translational-scout-team | Codex web/MCP/API when available | public-only | yes | yes for claim changes | connector-unavailable |
| doi-crossref | literature | biomedical-research-council, evidence-audit-team, translational-scout-team | Codex web/MCP/API when available | public-only | yes | yes for citation status changes | connector-unavailable |
| geo-sra-ncbi-datasets | omics | omics-analysis-team, idea-discovery-team | Codex web/MCP/API or local script when available | public-only unless approved | yes | yes | connector-unavailable |
| cellxgene-arrayexpress-biostudies | omics | omics-analysis-team | Codex web/MCP/API when available | public-only unless approved | yes | yes | connector-unavailable |
| clinicaltrials-gov | clinical | translational-scout-team, evidence-audit-team | Codex web/MCP/API when available | public-only | yes | yes | connector-unavailable |
| uniprot-reactome-pathway | pathway | biomedical-research-council, idea-discovery-team, evidence-audit-team | Codex web/MCP/API when available | public-only | yes | yes for mechanistic claim changes | connector-unavailable |
| local-bmat-validators | local-validator | all | local script through active Python interpreter | local-private-approved | no unless validating evidence artifacts | yes for release label changes | validator_unavailable_due_to_runtime |
| spawned-reviewer-lane | reviewer | all deep, audit, run workflows | spawned reviewer or tool-backed reviewer instance | public-only or local-private-approved according to role | maybe | yes | reviewer-unavailable |
| human-review | human-review | high-risk, privacy-sensitive, or release-blocked workflows | human review | local-private-approved | no unless evidence reviewed | yes for release decisions | human-review-pending |

## Selection Rules

1. Lock runtime capability preflight before selecting tools.
2. Prefer public unauthenticated sources before private, authenticated, or
   browser-state-dependent connectors.
3. Never send PHI, controlled-access records, private sample identifiers,
   unpublished manuscripts, or patent-sensitive strategy to an external tool
   without explicit human approval.
4. Run selected specialist lanes in parallel only after the lead has locked the
   question, source boundary, compute budget, and dependency graph.
5. Treat tool output as evidence input. Accepted findings must enter the central
   claim ledger before final writing.
6. Map every tool output that changes a claim, result call, ranking, or workflow
   label through `templates/results-integration-template.md` or
   `contracts/results-integration.schema.json`.

## Downgrade Reasons

- `connector-unavailable`: the preferred connector or tool is not available in
  the active runtime.
- `connector-not-authorized`: using the connector would cross the approved
  privacy, data, or human-review boundary.
- `source-lock-incomplete`: tool output was not mapped to source corpus rows.
- `results-integration-missing`: tool output was not mapped to claim/result
  rows before final wording.
- `tool-output-not-reviewed`: relevant reviewer or human review is pending.
- `validator_unavailable_due_to_runtime`: release validator could not be run
  because the active runtime lacks shell/code execution or the required CLI.
