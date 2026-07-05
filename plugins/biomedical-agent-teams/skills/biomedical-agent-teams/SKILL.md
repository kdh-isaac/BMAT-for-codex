---
name: biomedical-agent-teams
description: >
  BMAT for Codex v0.8.11 router for biomedical evidence audit, public-omics
  analysis, hypothesis tournaments, experiment design, translational scouting,
  loop workflows, tool-use/result integration, and validator-backed artifacts.
version: "0.8.11"
---

# Biomedical Agent Teams Router

This file is the lightweight router for the Biomedical Agent Teams (BMAT)
plugin. It intentionally stays small so Codex does not load the full governance
manual on every biomedical prompt. Load only the command recipe that matches the
user request, then follow that recipe to its required references, templates, and
contracts.

## Router Contract

1. Resolve every command recipe path relative to the directory containing this `SKILL.md`.
2. Read this router completely before task actions.
3. Select the narrowest command alias below, then read that command recipe
   completely before executing the workflow.
4. Do not load every agent, command, reference, contract, or template by default.
5. Use `source-manifest.json` and `scripts/bmat_docs_list.py` for inventory discovery.
6. Load agents, references, contracts, templates, loops, and scripts only when
   the selected command recipe, package check, validator, or user task requires
   them.
7. If routing is ambiguous, choose the smallest reversible command and state the
   assumption in the runtime capability preflight.

The current version adds stricter spawned-instance evidence checks, tool-use
honesty, results integration, one-page research overview, compute-budget,
team-DAG, loop-policy, and release-surface checks on top of the golden eval and
lightweight-router gates.

## Command Aliases

| User intent | Alias | Load this command recipe |
| --- | --- | --- |
| Broad biomedical research coordination, mechanism review, writing support, or multi-lane audit | `biomedical-research-council` | `commands/biomedical-research-council.md` |
| Hypothesis generation, ranking, tournament design, or idea triage | `idea-discovery-team` | `commands/idea-discovery-team.md` |
| Public omics discovery, QC, reproducible code review, dataset provenance, or analysis planning | `omics-analysis-team` | `commands/omics-analysis-team.md` |
| Citation, PMID, source-corpus, contradiction, overclaim, risk-of-bias, or final-claim audit | `evidence-audit-team` | `commands/evidence-audit-team.md` |
| Wet-lab or in vivo experiment design, controls, confounders, reagent/logistics planning, or statistical design | `experiment-design-team` | `commands/experiment-design-team.md` |
| Translational, clinical-trial, regulatory, IP, commercial, or scouting review | `translational-scout-team` | `commands/translational-scout-team.md` |

Common plain-language triggers map as follows:

- "verify", "audit", "PMID drift", "contradiction", "overclaim", or
  "citation check" -> `evidence-audit-team`.
- "GEO", "single-cell", "bulk RNA-seq", "public omics", "analysis code",
  or "reproducibility" -> `omics-analysis-team`.
- "experiment", "controls", "sample size", "mouse model", or "assay plan"
  -> `experiment-design-team`.
- "hypothesis", "mechanism ideas", "rank candidates", or "tournament"
  -> `idea-discovery-team`.
- "clinical trial", "regulatory", "IP", "market", or "translation"
  -> `translational-scout-team`.
- Otherwise start with `biomedical-research-council`.

## Runtime Capability Preflight

Every non-trivial BMAT workflow starts with a runtime capability preflight. The
selected command recipe may add fields, but the preflight must at least record:

- requested alias, selected mode, deliverable type, evidence scope, and risk
  class;
- available file read/write, shell/code execution, network, web/database lookup,
  and spawned-reviewer capability;
- whether external services or connectors are allowed for this task;
- source corpus needs, source lock status, and evidence freshness needs;
- execution strategy: `inline_first_selective_review` or
  `team_level_selective_dag`;
- skipped gates and downgrade reasons;
- final workflow label ceiling.

Capability checks are governance inputs, not decorative text. If shell/code
execution is unavailable, or if `scripts/bmat_validate.py` cannot be run because
shell/code execution is unavailable, record
`validator_unavailable_due_to_runtime` in the preflight and in the final skipped
gates or downgrade reasons. Do not claim `Full protocol followed` in that state.

When a complete artifact bundle exists and shell/code execution is available,
`scripts/bmat_validate.py` is a mandatory release gate for audit-bundle or full
protocol labels. If the validator fails, the workflow may still report findings,
but the final label must be downgraded and the blocking validator findings must
be summarized.

## Label Honesty Ceiling

Use the strongest label that is actually supported by runtime, source access,
artifact completeness, validation, and independent review:

- `Full protocol followed`: allowed only when required sources are locked,
  required artifacts exist, `scripts/bmat_validate.py` passes for the complete
  bundle, and an independent or tool-backed review surface was used where the
  selected recipe requires it.
- `Contract-shaped artifact bundle`: allowed when artifacts follow the schemas
  but validator execution or independent review is incomplete.
- `Compact standard workflow`: allowed for lower-risk, source-aware work where
  not all audit-bundle gates are required.
- `Biomedical Agent Teams-informed narrative review`: allowed when BMAT routing,
  source-aware reasoning, or claim-audit guidance informed a narrative answer but
  a complete formal artifact bundle was not requested or produced.
- `Limited capability-downgraded workflow`: required when source lock,
  validator execution, file access, shell/code execution, web/database lookup,
  reviewer spawning, or external corroboration is unavailable but material to
  the requested task.
- `Partial workflow; formal gates skipped`: required when material formal gates,
  artifacts, or validation steps were requested but skipped or could not be
  completed.
- `Blocked`: required when missing inputs, runtime capability, source access,
  privacy/safety constraints, failed validation, or user approval prevent a
  defensible BMAT result.

If the user asks for a final answer only, still report material skipped gates.
Do not hide unavailable validation behind a passing narrative summary.

## Evidence Audit Spine

For citation-sensitive or biomedical-claim-sensitive work, route claims through
this minimum spine:

1. Lock the question, entities, intended use, and evidence scope.
2. Build or update a source corpus with identifiers, retrieval date, inclusion
   status, claim use, and limitations.
3. Track claims in the central claim ledger before final writing.
4. Run targeted checks for PMID drift, DOI/accession drift, contradiction,
   overclaim, causal overstatement, missing uncertainty, study-quality limits,
   and safety/privacy/dual-use issues.
5. Use excluded-claim tracking for claims that are plausible but unsupported,
   out of scope, stale, contradictory, or not independently verified.
6. Write final biomedical text from the ledger only.
7. Apply the post-write final validator or explicitly downgrade when it cannot
   run.

Golden evals under `evals/` exercise this spine with public synthetic cases,
including negative controls, and should block releases that miss PMID drift,
contradiction, or overclaim cases.

## Omics and Benchmark Hygiene

For omics work, lock genome build, annotation release, sample IDs, biological
unit, contrasts, QC thresholds, normalization, batch handling, exclusions, and
multiple-testing strategy before confirmatory interpretation. Keep raw data
read-only and write derived outputs only to approved project locations.

For benchmark, challenge, or hidden-evaluation work, do not inspect hidden
truth files, private results, scoring scripts, Dockerfiles, or equivalent answer keys
unless the user explicitly asks for benchmark infrastructure review. If such
files are visible, state the boundary and keep analysis isolated from them.

## Execution Strategy

Default to `inline_first_selective_review`: the main Codex agent executes the
core workflow and selectively uses specialized reviewer lanes only when risk,
task complexity, or the selected command requires them.

Use `team_level_selective_dag` only for tasks that genuinely need dependency
aware parallel lanes. Nested spawning is disabled by default. If nested spawning
is requested or unavoidable, record explicit authorization, limits, handoff
contracts, and a merge plan.

Required reviewer lanes are command-specific. For substantive omics runs, the
omics command has a stricter reviewer floor and normally requires provenance and
code-review coverage for code-bearing analyses. For evidence audit runs, the
claim-level evidence verifier, citation verifier, contradiction red team, and
risk-of-bias auditor are the usual first candidates.

## Resource Discovery

Use these inventory surfaces instead of expanding this router:

- `source-manifest.json`: canonical resource lists and versioned package counts.
- `manifest.json`: marketplace/runtime metadata counts.
- `agent-registry.json`: spawnable role metadata and TOML template bindings.
- `references/tool-registry.md`: honest tool-use and downgrade registry.
- `contracts/results-integration.schema.json`: source/result/claim mapping
  contract for tool, reviewer, omics, and literature outputs.
- `templates/research-overview-template.md`: ledger-bound one-page synthesis
  template for final overview outputs.
- `scripts/bmat_docs_list.py`: dependency-free docs inventory helper.
- `scripts/bmat_package_check.py`: package structure, version, count, router,
  and lazy-load guard checks.
- `scripts/bmat_selftest.py`: dependency-free local package smoke check.
- `scripts/bmat_validate.py`: complete artifact bundle schema and policy gate.
- `evals/run_golden_eval.py`: golden-case eval gate.
- `evals/validate_golden_eval_schema.py`: thin schema-validation wrapper.

Use `scripts/bmat_init_bundle.py` when a task needs a new artifact bundle with
validator-named files.

## Package Maintenance Gates

Before releasing or copying this plugin into a cache directory, run the narrowest
available checks from the repository or marketplace root:

```bash
python plugins/biomedical-agent-teams/skills/biomedical-agent-teams/scripts/bmat_package_check.py --root plugins/biomedical-agent-teams
python plugins/biomedical-agent-teams/skills/biomedical-agent-teams/scripts/bmat_selftest.py --root plugins/biomedical-agent-teams
python plugins/biomedical-agent-teams/skills/biomedical-agent-teams/evals/validate_golden_eval_schema.py --tasks plugins/biomedical-agent-teams/skills/biomedical-agent-teams/evals/golden_tasks.jsonl --outputs plugins/biomedical-agent-teams/skills/biomedical-agent-teams/evals/sample_outputs.jsonl
python plugins/biomedical-agent-teams/skills/biomedical-agent-teams/evals/run_golden_eval.py --tasks plugins/biomedical-agent-teams/skills/biomedical-agent-teams/evals/golden_tasks.jsonl --outputs plugins/biomedical-agent-teams/skills/biomedical-agent-teams/evals/sample_outputs.jsonl --strict --gate
```

When test tooling is available, also run the package tests:

```bash
uvx --with jsonschema pytest tests plugins/biomedical-agent-teams/skills/biomedical-agent-teams/tests -q
```

The package check enforces that this router remains lightweight and that command
recipes, not the root router, carry the longer governance manuals. If a future
change pushes this file over the configured router size ceiling, move detailed
instructions into command recipes, references, templates, contracts, or scripts.
