# Biomedical Agent Teams Quickstart

Use this page when you need the smallest working BMAT workflow shape. The full
router remains in `skills/biomedical-agent-teams/SKILL.md`.

## Pick A Workflow

- `biomedical-research-council`: broad research synthesis or multi-axis routing.
- `idea-discovery-team`: hypothesis generation, ranking, and kill-test planning.
- `omics-analysis-team`: public omics feasibility, run, or audit.
- `evidence-audit-team`: claim, citation, provenance, or report defensibility.
- `experiment-design-team`: wet-lab or computational validation design.
- `translational-scout-team`: clinical, regulatory, IP, or competitive scouting.

## Pick A Mode

- `quick`: compact answer with explicit assumptions and claim boundary.
- `standard`: preflight, source/claim boundary, and selected specialist lanes.
- `deep`: full audit gates, workflow state, and post-write validation.
- `audit`: pass / pass-with-revisions / block verdict for existing material.
- `plan`: omics planning without full execution.
- `run`: omics execution with S1-S5 gates and reviewer-floor policy.

## Examples

```text
biomedical-research-council TET2 KO plus IL-21 armored CAR-T persistence --mode standard
```

```text
omics-analysis-team public datasets for IL-21-STAT3-FOXO1 stem-like CAR-T signatures --mode plan
```

```text
evidence-audit-team "IL-21 armored TET2 KO CAR-T suppresses exhaustion through FOXO1" --mode audit
```

```text
experiment-design-team FOXO1 dependency of TET2 KO plus IL-21 armored CAR-T persistence --mode deep
```

## Scaffold A Bundle

```bash
python skills/biomedical-agent-teams/scripts/bmat_init_bundle.py --workflow evidence-audit-team --mode audit --topic "audit FOXO1 dependency claim" --out ./bmat_runs/foxo1_audit
```

Then fill the generated `runtime_capability_preflight.json`, `source_corpus.json`,
`claim_ledger.json`, `stage_evaluation.json`, and `post_write_validation.json`
before claiming `Compact standard workflow` or `Full protocol followed`.

## Run A Local Scaffold With Validators

```bash
python skills/biomedical-agent-teams/scripts/bmat_run.py --alias evidence-audit-team --mode audit --tier compact --question "audit FOXO1 dependency claim" --out ./bmat_runs/foxo1_audit --force --validate --export markdown
```

`bmat_run.py` writes `lead_decision.json`, `workflow_dag.json`,
`results_integration.json`, and `tool_call_ledger.json` alongside the core
bundle. For omics runs, add `--track bulk-rnaseq`, `--track tenx-gex`,
`--track tenx-cellplex`, or another supported subtrack to generate
`omics_run_manifest.json`. In 1.1.0 the generated
workflow DAG is normalized to the requested alias and mode before validation.

## Smoke Test

```bash
python skills/biomedical-agent-teams/scripts/bmat_selftest.py --root .
```

The self-test runs package layout checks, loop policy validation, a valid bundle
validation, and the offline golden-eval sample without requiring `pytest`.
