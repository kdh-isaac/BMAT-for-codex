# Biomedical Agent Teams quick start

BMAT v1.2.0 is installed through the Codex plugin browser.

```bash
codex plugin marketplace add kdh-isaac/BMAT-for-codex --ref main
codex
```

Open `/plugins`, choose **Biomedical Agent Teams**, and install it. Then invoke
the `biomedical-agent-teams:biomedical-agent-teams` skill or name one alias:

- `biomedical-research-council`
- `evidence-audit-team`
- `omics-analysis-team`
- `idea-discovery-team`
- `experiment-design-team`
- `translational-scout-team`

For a local scaffold from the repository root:

```bash
python plugins/biomedical-agent-teams/skills/biomedical-agent-teams/scripts/bmat_run.py --alias evidence-audit-team --mode standard --tier compact --question "Audit this bounded biomedical claim" --out outputs/bmat-audit --domain-pack generic-biomedical --dry-run
```

The scaffold is not a verified review. Fixture and sample-mode records exercise
plumbing only, same-model review is not independent, and `Full protocol
followed` requires a complete v2 bundle, eligible hash-bound review receipts,
`bundle_manifest.json`, and a passing release validator.

```bash
python plugins/biomedical-agent-teams/skills/biomedical-agent-teams/scripts/bmat_bundle_manifest.py --bundle path/to/completed-bundle
python plugins/biomedical-agent-teams/skills/biomedical-agent-teams/scripts/bmat_validate.py --bundle path/to/completed-bundle --release
```

See the repository `docs/validation-boundaries.md` before interpreting a pass.
