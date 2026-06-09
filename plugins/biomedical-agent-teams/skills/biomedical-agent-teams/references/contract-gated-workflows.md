# Contract-Gated Workflows

Use this reference for `deep`, `audit`, omics `run`, translational, manuscript,
and long-running biomedical workflows.

## Purpose

BMAT role prompts are usually read and applied inline in Codex. Contract gating
keeps those inline roles auditable by requiring the lead to preserve each role's
scope, inputs, methods, findings, limitations, handoff, and verdict before the
final writer synthesizes the answer.

## Required Flow

1. Produce runtime capability preflight before external source expansion, file
   writes, code execution, spawned-agent claims, or final writing.
2. Produce the workflow preflight contract before external source expansion,
   file writes, code execution, or final writing.
3. Lock source corpus identity, retrieval date/version, inclusion status, and
   claim use before source-backed final wording.
4. For audit/reviewer roles, emit evaluation criteria before reviewing the final
   answer or deliverable when feasible. Keep the criteria separate from the
   content-visible verdict.
5. Store or summarize role outputs using `contracts/role-output.schema.json`.
6. Maintain workflow-run state for deep, audit, omics run, translational,
   generated-file, manuscript-support, or long-running work.
7. Maintain the central claim ledger. The final writer may use only
   `allowed_final_wording` from passed or pass-with-caveats claims.
8. For omics run/audit or long-running generated-file workflows, run S1-S5 stage
   evaluation. If S3 Validate does not pass, S4/S5 claims must be blocked,
   downgraded, or labeled exploratory/not assessable.
9. Apply `references/independent-review-policy.md` before using independent
   validation or independent audit wording.
10. Run post-write validation against `contracts/post-write-validation.schema.json`.
11. Downgrade the workflow label when any required gate is skipped or only
   considered informally.

## Checkpoint Types

| checkpoint | required before | block condition |
|---|---|---|
| runtime capability lock | tool-backed or full-depth claims | required runtime capability unavailable |
| context lock | source expansion or analysis | unclear question, unsafe scope, or missing human gate |
| source lock | source-backed claims | missing PMID/DOI/accession/version/retrieval date when needed |
| analysis lock | omics/statistics run | missing sample sheet, biological unit, endpoint, or design formula |
| validation stage lock | omics inference or generated-file reporting | S3 validation failed or was not run when required |
| claim lock | final writing | unchecked central claim ledger |
| integrity gate | high-confidence release | unsupported claim, citation mismatch, provenance gap, unsafe advice |

## Validator-Friendly Output

When returning a formal role output, prefer this compact shape:

```text
role:
task_scope:
inputs_checked:
methods_or_tools_used:
key_findings:
limitations:
handoff:
verdict:
```

If the answer is short and interactive, this can be compressed into prose, but
the final workflow label must say `Compact standard workflow` or
`Partial workflow; formal gates skipped` rather than full protocol compliance.
