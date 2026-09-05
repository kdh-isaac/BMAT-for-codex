# Installed package release checks

Run from the plugin directory using Python 3.10-3.13. Install jsonschema and
pytest as described in [workflow planning](workflow-planning.md).

```bash
python -B skills/biomedical-agent-teams/scripts/bmat_package_check.py --root .
python -B skills/biomedical-agent-teams/scripts/bmat_selftest.py --root . --release
python -B -m pytest -p no:cacheprovider skills/biomedical-agent-teams/tests -q
```

These checks exercise package mechanics and synthetic fixtures only. Run
bmat_validate.py --release against each completed research bundle as well.
Source checkout CI additionally runs marketplace integration tests and the
Python 3.10-3.13 Ubuntu/Windows matrix.
