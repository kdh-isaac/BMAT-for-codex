# Biomedical Agent Teams Codex Marketplace

Local Codex Desktop marketplace package for the Biomedical Agent Teams plugin.

Current plugin version: `0.3.5+codex.20260610`.

## Install

```powershell
codex plugin marketplace add "G:\내 드라이브\work\codex\work\plugins\biomedical-agent-teams-codex-marketplace"
codex plugin add biomedical-agent-teams@biomedical-agent-teams-marketplace
```

The plugin body is in `plugins/biomedical-agent-teams/` and exposes the
`biomedical-agent-teams` skill with 35 agent prompts, 6 command recipes, a
fixed-field claim-ledger template, contract schemas, biomedical passport state,
runtime capability preflight, source corpus lock, workflow-run state, stage
evaluation, hypothesis tournament, independent-review policy, and
inline-first hybrid execution, selective spawned review, team-level spawned
workflow DAGs, and integrity-gate resources.

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

For BioAgentBench-style tasks, the benchmark protocol is locked before solving.
Truth files, result archives, scoring scripts, reproduction scripts, and task
Dockerfiles are scoring-phase materials and are not exposed to the solving
agent before the candidate output is frozen.
