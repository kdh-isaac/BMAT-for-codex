# Codex Runtime Capability Matrix

Use this reference during runtime capability preflight. It maps common upstream
workflow wording to actual Codex surfaces.

| requested capability | acceptable Codex evidence | downgrade if unavailable |
|---|---|---|
| read local files | successful file read or listed resource | skip file-backed claims or ask user for content |
| write local artifacts | approved path and successful write capability | inline-only output or partial workflow |
| shell/code execution | successful narrow command or known active shell tool | plan-only or no-run audit |
| web search/database lookup | browser/web/database tool actually called | mark external evidence not checked |
| spawned subagent | actual subagent/thread/tool-backed agent created | role prompt read only; no independent-agent wording |
| public biomedical database | actual database/API/tool query or verified web source | cite as not checked or use source-corpus gap |
| durable resume state | artifact path plus workflow_run/passport/ledger saved | compact inline state only |

## Preflight Rule

Frontmatter `allowed-tools` and upstream phrases such as `dispatch`, `Task`,
`agent`, or `handoff` are capability hints. They do not prove the capability was
available or used in the active Codex runtime.

## Downgrade Rule

If a workflow requires a capability that is unavailable, mark the related gate
as `skipped` or `block`, state the reason, and avoid `Full protocol followed`
unless the missing capability is not required for the requested deliverable.
