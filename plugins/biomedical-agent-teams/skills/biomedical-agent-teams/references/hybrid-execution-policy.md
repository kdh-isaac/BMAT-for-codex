# Hybrid Execution Policy

BMAT is lead-controlled and inline-first. The main assistant owns the protocol
lock, source scope, central claim ledger, workflow-run state, and final
synthesis. Spawned subagents are a review and parallelization tool, not the
default way to execute every role.

## Execution Strategies

| strategy | use when | avoid when |
|---|---|---|
| `inline_only` | The request is quick, narrow, conceptual, or low risk. | The user asked for independent review or the answer depends on high-confidence source-backed claims. |
| `inline_first_selective_review` | The main workflow is best kept coherent, but selected reviewer independence improves audit quality. | The task needs several independent domain teams to work in parallel. |
| `team_level_selective_dag` | The question has separable decision axes such as idea generation, omics feasibility, translational scouting, experiment design, and evidence audit. | The task has a single claim or one obvious workflow recipe. |
| `user_requested_full_spawn` | The user explicitly requests broad spawning after being told it is usually inefficient. | The user did not authorize broad spawning or the budget/privacy boundary is unclear. |
| `blocked` | Required runtime capability, safety, privacy, or scope constraints prevent the requested execution pattern. | A narrower inline or selective-review workflow can answer safely. |

## Selective Spawn Review

Use this pattern when the most efficient workflow is inline, but the final
answer should look and behave like an audited output.

1. Main lead runs the command recipe inline.
2. Main lead builds or updates the central claim ledger.
3. Spawn only reviewer roles that materially improve the output:
   - `claim-level-evidence-verifier`
   - `citation-verifier`
   - `contradiction-red-team`
   - `causal-inference-confounder-analyst`
   - `biostats-repro-auditor`
   - `provenance-traceability-architect`
   - `omics-provenance-validator`
   - `omics-code-reviewer` for omics `run` or code-bearing outputs
   - `risk-of-bias-study-quality-auditor`
   - `post-write-final-validator` for high-confidence final prose
   - `safety-ethics-privacy-dual-use-auditor` when triggered
4. Reviewer outputs must map to claim IDs or clearly state that no ledger was
   available.
5. Main lead accepts, rejects, or downgrades reviewer findings in the ledger
   before final writing.

Use `agent-registry.json` before spawning. A reviewer must be marked
`spawnable: true`, its `codex-agents/*.toml` template must point to an existing
role prompt and `contracts/spawned-agent-output.schema.json`, and the workflow
run must record the concrete execution in `spawned_agent_instances`. A planned
or completed `spawned_review_lanes` row without a matching instance is only a
planning record and must not be used as proof of independent execution.

Do not call same-model separate-pass review independent unless a spawned
subagent, separate model, tool-backed validator, external verifier, or human
reviewer actually performed the review.

## Team-Level Selective DAG

Use this pattern when several command-level teams can answer independent parts
of a broad research decision.

Phase 0, inline lead lock:

- protocol/context lock
- entity normalization
- evidence scope and source-corpus plan
- execution strategy and spawn budget
- team dependency graph
- central claim-ledger skeleton

Phase 1, independent spawned team bundles when useful:

- `idea-discovery-team`: candidate hypotheses, mechanism/ranking frame, and
  useful excluded ideas.
- `omics-analysis-team`: public-data feasibility, S1-S3 plan, or locked audit.
  Full `run` requires S1-S3 validation before S4/S5 claims.
- `translational-scout-team`: trial, regulatory, IP, operational, and safety
  boundary scan.

Phase 2, dependency-bound spawned team bundles when useful:

- `experiment-design-team`: run after the lead narrows one or more candidate
  hypotheses or designs.
- `evidence-audit-team`: run after final candidate claims, draft text, or result
  claims are available.

Phase 3, inline synthesis:

- merge accepted spawned-team outputs into the central claim ledger
- keep rejected or not-verified material out of final wording
- run claim/citation/post-write validation
- report execution strategy, spawned outputs, skipped gates, and downgrade
  reasons

The deterministic verification point for this DAG is the `team_spawn_outputs`
stage in workflow-run state. A completed `team_spawn_lanes` row is only a plan
record until there is a matching complete `team_output_artifacts` entry with
the same `team` and `phase`, a non-empty artifact path, `checks_run`,
`ledger_handoff`, and dependency links. For Phase 2+ lanes, `depends_on` must
resolve to a complete prior-phase team lane or prior team output artifact, and
`depends_on_outputs` must resolve to complete prior team artifact IDs.
`scripts/bmat_validate.py` enforces these checks before a bundle can honestly
claim full-protocol release. If a team output uses nested child agents while
`nested_spawn_allowed` is false, the validator blocks the run.

## Anti-Patterns

- Spawning every role by default.
- Spawning every team by default.
- Letting spawned teams spawn nested child agents without explicit approval.
- Running `experiment-design-team` before a hypothesis is narrowed.
- Running `omics-analysis-team --mode run` before accession/cohort, assay,
  biological unit, contrast/endpoint, and S1-S3 validation are locked.
- Treating team output as final truth without central claim-ledger mapping.
- Hiding reviewer objections or contradiction findings in the synthesis.

## Mode Defaults

| mode | default strategy | typical spawn budget |
|---|---|---|
| quick | `inline_only` | 0 |
| standard | `inline_only` or `inline_first_selective_review` | 0-1 |
| deep | `inline_first_selective_review` or `team_level_selective_dag` | 1-3 |
| audit | `inline_first_selective_review` with optional team DAG for multi-axis audits | 1-4 |
| omics plan | `inline_only` unless feasibility axes are independent | 0-1 |
| omics run | `inline_first_selective_review` after S1-S3 locks; minimum one core spawned reviewer when supported | 1-3, with at least one of `omics-code-reviewer`, `omics-provenance-validator`, or `biostats-repro-auditor` unless explicitly blocked or downgraded |

## Omics Run Reviewer Floor

For omics `run`, reviewer spawning is opt-out rather than opt-in after S1-S3
locks. When the runtime supports spawned subagents or tool-backed reviewer
instances, select at least one core reviewer:

- `omics-code-reviewer` for code, raw-data safety, reproducibility, leakage, and
  parameter provenance.
- `omics-provenance-validator` for metadata locks, design, biological unit,
  statistical provenance, and claim proportionality.
- `biostats-repro-auditor` for model validity, donor/unit handling,
  multiplicity, ranking stability, survival/event handling, and sensitivity
  analysis.

Use two or more core reviewers for donor-aware single-cell contrasts,
multi-omics integration, survival modeling, large generated scripts, or
manuscript-grade interpretation. A zero reviewer budget is acceptable only when
the preflight records an explicit runtime-unavailable, privacy-blocked,
user-requested compact, or budget-blocked rationale and the workflow label is
downgraded. Role prompts read inline do not satisfy this reviewer floor.

## Required Spawned Output Contract

Every spawned reviewer or spawned team must return:

- objective and assigned scope
- inputs, files, metadata, and sources checked
- tools, skills, commands, or databases used
- key findings, contradictions, risks, and confidence level
- files changed, if any, or `none`
- checks run, skipped checks, and reasons
- recommended handoff
- claim IDs or ledger rows affected when available

A bare "done" is not sufficient for BMAT review or team output.

For reviewer subagents, the output must also satisfy
`contracts/spawned-agent-output.schema.json` plus any role-specific TOML fields.
Record the output artifact path in `workflow-run.spawned_agent_instances` so a
validator can connect the actual subagent execution to the final claim ledger.

For spawned command-level teams, record the formal team report in
`workflow-run.team_output_artifacts`. Reviewer instances and team bundle
outputs are deliberately separate: `spawned_agent_instances` proves a reviewer
or tool-backed validator ran, while `team_output_artifacts` proves a selected
team DAG node produced a dependency-resolved handoff artifact.
