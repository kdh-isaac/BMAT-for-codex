# Biomedical Agent Teams quick start

BMAT v1.2.2 is installed through the Codex plugin browser.

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

From the installed plugin directory, create a local scaffold:

```bash
python skills/biomedical-agent-teams/scripts/bmat_run.py --alias evidence-audit-team --mode standard --tier compact --question "Audit this bounded biomedical claim" --out outputs/bmat-audit --domain-pack generic-biomedical --dry-run
```

The scaffold is not a verified review. Fixture and sample-mode records exercise
plumbing only, same-model review is not independent, and `Full protocol
followed` requires a complete v2 bundle, eligible hash-bound review receipts,
`bundle_manifest.json`, and a passing release validator.

```bash
python skills/biomedical-agent-teams/scripts/bmat_bundle_manifest.py --bundle path/to/completed-bundle
python skills/biomedical-agent-teams/scripts/bmat_validate.py --bundle path/to/completed-bundle --release
```

See the bundled [validation boundaries](docs/validation-boundaries.md) before interpreting a pass.

For the installed release checks, install `jsonschema>=4.18,<5` and run:

```bash
python skills/biomedical-agent-teams/scripts/bmat_selftest.py --root . --release
```

For required review coverage, final/ledger snapshots, and source locator maps,
see the [1.2.2 integrity contract](docs/release-integrity-1.2.2.md).
Compact work remains inline-first; release validation does not certify scientific truth.
