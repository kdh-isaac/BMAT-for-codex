# Biomedical Agent Teams Codex Marketplace

Local Codex Desktop marketplace package for the Biomedical Agent Teams plugin.

Current plugin version: `0.3.2+codex.20260609`.

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
integrity-gate resources.

## Workflow Structure

```mermaid
flowchart TD
    A["User request or BMAT alias"] --> B["Runtime capability preflight"]
    B --> C["Protocol and context lock"]
    C --> D["Source corpus lock"]
    D --> E["Select workflow recipe"]
    E --> F{"Mode"}
    F -->|"quick"| G["Lead answer with minimal evidence checks"]
    F -->|"standard"| H["Specialist lanes plus claim ledger"]
    F -->|"deep or audit"| I["Specialist lanes plus workflow-run state"]
    I --> J["Biomedical passport"]
    I --> K["Stage S1-S5 evaluation"]
    I --> L["Independent review policy"]
    G --> M["Writer restricted to verified claims"]
    H --> M
    J --> M
    K --> M
    L --> M
    M --> N["Post-write final validation"]
    N --> O["Final workflow label and skipped-gate reasons"]
    O --> P["Compact final or audit-bundle final"]
```

For BioAgentBench-style tasks, the benchmark protocol is locked before solving.
Truth files, result archives, scoring scripts, reproduction scripts, and task
Dockerfiles are scoring-phase materials and are not exposed to the solving
agent before the candidate output is frozen.
