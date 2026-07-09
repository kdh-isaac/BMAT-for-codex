# Biomedical Agent Teams for Codex

BMAT for Codex v1.1.1 is a skill-routed biomedical workflow plugin. The live
router is `skills/biomedical-agent-teams/SKILL.md`; this file keeps the hidden
plugin metadata surface aligned with the user-facing workflow contract.

## v1.1.1 Runtime Contract

- Use `--tier compact|full` to make the expected bundle depth explicit.
- Use `--track bulk-rnaseq|tenx-gex|tenx-cellplex|tenx-citeseq|tenx-vdj|tenx-multiome|single-cell-other|survival|multi-omics|other` for omics runs.
- Persist `lead_decision.json` for source-backed `standard`, `deep`, `audit`,
  `team_level_selective_dag`, and `Full protocol followed` workflows.
- Persist `omics_run_manifest.json` v2 for omics workflows and explicit omics
  tracks.
- Treat validator JSON `fix_hint` as the next-action repair surface when a
  bundle fails validation.
- Route tool, connector, reviewer, and omics outputs through
  `results_integration.json`, `tool_call_ledger.json`, and `claim_ledger.json`
  before final writing.

## Local Smoke Commands

```bash
python skills/biomedical-agent-teams/scripts/bmat_run.py --alias omics-analysis-team --mode run --tier full --track tenx-gex --question "10x provenance smoke" --out /tmp/bmat-tenx-smoke --dry-run --validate --force
python skills/biomedical-agent-teams/scripts/bmat_codex_adapter.py --alias omics-analysis-team --mode run --tier compact --track bulk-rnaseq --question "bulk RNA-seq adapter smoke" --out /tmp/bmat-bulk-adapter-smoke --dry-run --force
```
