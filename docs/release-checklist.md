# BMAT v1.2.0 clean-checkout release checklist

The release gate is designed to run offline after Python test dependencies are
installed. It does not call a live model, browse biomedical databases, or
download raw omics data. Run it from the repository root with Python 3.10,
3.11, 3.12, or 3.13.

The examples use `uv` so dependencies remain outside the source tree. An
equivalent virtual environment with `pytest`, `pytest-xdist`, and `jsonschema`
is acceptable.

```bash
git status --short

uv run --with pytest --with pytest-xdist --with jsonschema python -B plugins/biomedical-agent-teams/skills/biomedical-agent-teams/scripts/bmat_package_check.py --root plugins/biomedical-agent-teams
uv run --with pytest --with pytest-xdist --with jsonschema python -B plugins/biomedical-agent-teams/skills/biomedical-agent-teams/scripts/bmat_selftest.py --root plugins/biomedical-agent-teams

uv run --with pytest --with pytest-xdist --with jsonschema python -B plugins/biomedical-agent-teams/skills/biomedical-agent-teams/evals/validate_golden_eval_schema.py --tasks plugins/biomedical-agent-teams/skills/biomedical-agent-teams/evals/golden_tasks.jsonl --outputs plugins/biomedical-agent-teams/skills/biomedical-agent-teams/evals/sample_outputs.jsonl
uv run --with pytest --with pytest-xdist --with jsonschema python -B plugins/biomedical-agent-teams/skills/biomedical-agent-teams/evals/run_golden_eval.py --tasks plugins/biomedical-agent-teams/skills/biomedical-agent-teams/evals/golden_tasks.jsonl --outputs plugins/biomedical-agent-teams/skills/biomedical-agent-teams/evals/sample_outputs.jsonl --strict --gate

uv run --with pytest --with pytest-xdist --with jsonschema python -B plugins/biomedical-agent-teams/skills/biomedical-agent-teams/evals/run_model_golden_eval.py --tasks plugins/biomedical-agent-teams/skills/biomedical-agent-teams/evals/golden_tasks.jsonl --alias evidence-audit-team --runtime codex --model sample-model --out .release-tmp/model-sample.jsonl --sample-mode --then-score --gate
uv run --with pytest --with pytest-xdist --with jsonschema python -B plugins/biomedical-agent-teams/skills/biomedical-agent-teams/scripts/bmat_public_omics_benchmark_smoke.py --out .release-tmp/public-omics --validate --force

uv run --with pytest --with pytest-xdist --with jsonschema python -B plugins/biomedical-agent-teams/skills/biomedical-agent-teams/scripts/bmat_validate.py --bundle plugins/biomedical-agent-teams/skills/biomedical-agent-teams/tests/fixtures/valid_full_protocol_bundle --release

uv run --with pytest --with pytest-xdist --with jsonschema python -B -m pytest -p no:cacheprovider -n auto tests plugins/biomedical-agent-teams/skills/biomedical-agent-teams/tests -q

git status --short
```

Use a temporary directory outside the checkout in automation. If `.release-tmp`
is used locally, remove it after inspecting outputs and confirm that the final
`git status --short` matches the initial clean state.

## Gate coverage

- BOM-free release text and Python syntax compilation;
- package layout, source-manifest set equality, metadata versions, and resource
  counts;
- dependency-free self-test and schema validation;
- strict offline golden scoring and deterministic sample-model plumbing;
- metadata-only public-omics smoke cases;
- release validation of the self-contained full-protocol fixture;
- conservative v1-to-v2 migration and round-trip/non-overwrite tests;
- full pytest on Ubuntu and Windows-focused path/CLI tests;
- current-version residue checks; and
- a clean working tree after the suite.

GitHub Actions defines the executable matrix in `.github/workflows/ci.yml`.
Sample mode and fixtures validate mechanics only; see
[`validation-boundaries.md`](validation-boundaries.md) before interpreting a
passing release.
