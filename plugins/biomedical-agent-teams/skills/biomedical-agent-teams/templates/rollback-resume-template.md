# Rollback And Resume Template

Use for long-running BMAT workflows when a durable artifact directory is
requested or useful for resumption. This template does not perform filesystem
rollback by itself; it records what can be inspected, resumed, or manually
discarded.

## Durable Artifact Convention

Recommended location inside the active workspace or user-approved output path:

```text
.bmat/
  run-YYYYMMDD-001/
    passport.json
    preflight.json
    runtime_capability_preflight.json
    source_corpus.jsonl
    claim_ledger.jsonl
    workflow_run.json
    role_outputs/
    artifacts/
    validation/
```

## Resume State

| field | value |
|---|---|
| run_id |  |
| current_stage |  |
| last_verified_artifact |  |
| next_action |  |
| open_questions |  |
| skipped_gates_requiring_later_review |  |

## Review Before Resume

- Reopen `workflow_run.json` or the compact workflow run table.
- Reopen the biomedical passport and claim ledger before writing new final text.
- Treat final prose as stale if the claim ledger or source corpus changed after
  the prior post-write validation.
- Do not call a manual deletion or filesystem reset a BMAT rollback unless the
  user explicitly requested that destructive operation.
