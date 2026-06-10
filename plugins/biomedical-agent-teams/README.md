# Biomedical Agent Teams Codex Plugin

Codex Desktop compatible plugin wrapper for the `biomedical-agent-teams` skill.

## Contents

- `.agents/plugins/marketplace.json`: local marketplace metadata.
- `skills/biomedical-agent-teams/`: Codex-native biomedical agent-team skill,
  including 35 agent prompts, 6 workflow recipes, 10 contract schemas, 10
  templates, 7 references, a fixed-field claim ledger, biomedical passport,
  runtime capability preflight, source corpus lock, workflow-run state, stage
  evaluation, hypothesis tournament, independent-review policy, inline-first
  hybrid execution, selective spawned review, team-level spawned workflow DAGs,
  and integrity-gate resources.

## v0.3.5 Updates

- Makes BMAT explicitly lead-controlled and inline-first by default.
- Adds `inline_first_selective_review` for professional/auditable workflows:
  the main workflow runs inline while only selected reviewer roles are spawned
  for independent evidence, citation, contradiction, biostats, provenance, or
  risk-of-bias review.
- Adds `team_level_selective_dag` for broad decisions: selected command-level
  teams can be spawned as workflow bundles in dependency-aware phases.
- Disables nested spawning by default. A spawned team runs its internal recipe
  inline and returns one formal team report unless explicit nested-spawn
  approval is recorded.
- Adds `references/hybrid-execution-policy.md`,
  `templates/team-spawn-plan-template.md`, and execution-strategy fields to the
  preflight and workflow-run contracts.

## Workflow Structure

```mermaid
flowchart TD
    accTitle: BMAT Hybrid Workflow Structure
    accDescr: Lead-controlled BMAT workflow showing the inline spine, optional team-level spawned DAG before final ledger synthesis, and optional selective spawned review after audit gates.

    subgraph lead_controlled_inline_spine["Lead-controlled inline spine"]
        user_request["User request or BMAT alias"]
        runtime_preflight["Runtime capability preflight"]
        protocol_lock["Protocol and context lock"]
        entity_normalization["Entity normalization"]
        source_corpus_lock["Source corpus lock"]
        playbook_route["Lead scientist and playbook router"]
        strategy_lock{"Execution strategy lock"}
        inline_lanes["Selected specialist lanes inline"]
        claim_ledger["Central claim ledger and evidence graph"]
        workflow_state["Workflow-run state and biomedical passport"]
        stage_evaluation["Stage S1-S5 evaluation when applicable"]
        audit_gates["Audit gates"]
        claim_citation_check["Pre-synthesis claim and citation verification"]
        ledger_only_writer["Ledger-only scientific writer"]
        post_write_validator["Post-write final validator"]
        final_output["Final label, downgrade reasons, and audit summary"]
    end

    subgraph team_level_spawned_dag["Optional team-level spawned subagent DAG"]
        phase_zero["Phase 0: main lead locks scope and team graph"]
        phase_one["Phase 1: idea, omics, translational teams"]
        phase_two["Phase 2: experiment design and evidence audit teams"]
        team_handoff["Formal team outputs and ledger handoff"]
    end

    subgraph selective_spawned_review["Optional selective spawned review"]
        review_decision{"Independent review needed?"}
        reviewer_lanes["Claim, citation, stats, provenance, contradiction, bias reviewers"]
        reviewer_handoff["Accepted findings merged into ledger"]
    end

    user_request --> runtime_preflight --> protocol_lock --> entity_normalization
    entity_normalization --> source_corpus_lock --> playbook_route --> strategy_lock
    strategy_lock -->|"inline_only or inline_first_selective_review"| inline_lanes
    strategy_lock -->|"team_level_selective_dag"| phase_zero
    strategy_lock -->|"blocked"| final_output
    phase_zero --> phase_one --> phase_two --> team_handoff --> claim_ledger
    inline_lanes --> claim_ledger
    claim_ledger --> workflow_state --> stage_evaluation --> audit_gates
    audit_gates --> review_decision
    review_decision -->|"yes"| reviewer_lanes --> reviewer_handoff --> claim_citation_check
    review_decision -->|"no"| claim_citation_check
    claim_citation_check --> ledger_only_writer --> post_write_validator --> final_output
```

The main lead owns the protocol lock, source scope, central claim ledger,
workflow-run state, and final synthesis. Team-level spawned subagents are used
only for separable decision axes; selective spawned reviewers are used only
after ledger claims exist. Nested spawning is disabled by default.

## v0.3.2 Updates

- Adds benchmark hygiene rules for BioAgentBench-style hidden truth/result
  files, scoring scripts, reproduction scripts, and task Dockerfiles.
- Clarifies that truth/result materials are scoring-phase only and must not be
  exposed to the solving agent before final candidate output is frozen.

## v0.3.1 Updates

- Ensures every command recipe final output requires a final workflow label and
  skipped-gate reasons.
- Strengthens smoke tests for router-advertised bundled resources, source
  manifest command/agent existence, Markdown resource references, and v0.3
  schema sample payload validation.

## v0.3.0 Updates

- Adds runtime capability preflight so workflows record actual Codex support for
  web/search, shell/code execution, file writes, network/database access,
  spawned subagents, sandbox, and downgrade rules.
- Adds workflow-run stage DAG state for deep, audit, omics run, translational,
  manuscript-support, generated-file, and long-running workflows.
- Promotes source corpus handling into a standalone source lock with schema and
  template.
- Adds hypothesis tournament resources for idea-discovery and research-council
  ideation workflows.
- Adds S1-S5 stage evaluation for omics run/audit and generated-file workflows,
  with a blocking rule when S3 Validate fails.
- Adds independent-review policy distinguishing spawned/tool-backed validation
  from same-model separate-pass validation.
- Adds rollback/resume artifact convention for durable `.bmat/run-*` style
  state.

## v0.2.4 Updates

- Adds command-level preflight contract requirements to all six workflow
  recipes.
- Adds biomedical passport state tracking to the evidence-audit recipe.
- Updates the workflow-spine manifest to include passport and integrity gates.
- Removes a zero-byte `.Rhistory` packaging artifact from the commands folder.

## v0.2.3 Updates

- Adds validator-friendly contract schemas for preflight, role outputs,
  biomedical passport state, omics run manifests, and post-write validation.
- Adds biomedical passport and integrity-gate templates.
- Adds a BMAT-specific failure-mode taxonomy for fabricated identifiers,
  citation-context drift, bulk-to-cell-intrinsic overclaim, metadata leakage,
  post-hoc endpoint inflation, missing uncertainty, unsafe/private disclosure,
  clinical overreach, provenance gaps, and writer/reviewer self-ratification.
- Adds formal return contracts for the lead scientist, final writer, omics
  curator, analysis workers, pathway interpreter, omics reviewers, and reporter.
- Requires passport and integrity-gate status in deep/audit/omics/translational
  audit-bundle outputs when applicable.

## v0.2.2 Updates

- Adds a mandatory preflight compliance contract for aliased workflows.
- Distinguishes role prompts read inline, formal role outputs, tool calls, and
  spawned subagents.
- Defines mode-specific minimum artifacts and final workflow labels.
- Adds `safe_mode_note` handling for low-risk public-only workflows with safety
  triggers.
- Adds a post-write self-check to `biomedical-research-council`.

## v0.2.1 Updates

- Adds explicit `quick`, `standard`, `deep`, and `audit` mode routing.
- Adds `templates/claim-ledger-template.md` for central claim ledgers and
  excluded / not-ledger-verified claim tracking.
- Adds bulk, single-cell, survival, and multi-omics track checklists.
- Resolves report output paths from the active workspace instead of a hard-coded
  OS-specific path.
- Splits final responses into `compact final` and `audit bundle final`.

## Install

From any shell:

```bash
codex plugin marketplace add "G:\내 드라이브\work\codex\work\plugins\biomedical-agent-teams-codex-marketplace"
codex plugin add biomedical-agent-teams@biomedical-agent-teams-marketplace
```

Then restart Codex Desktop if the plugin list does not refresh immediately.

## Primary Aliases

- `biomedical-research-council`
- `idea-discovery-team`
- `omics-analysis-team`
- `evidence-audit-team`
- `experiment-design-team`
- `translational-scout-team`

Slash-prefixed aliases may be reserved by some Codex clients. If that happens,
use the plain alias form.
