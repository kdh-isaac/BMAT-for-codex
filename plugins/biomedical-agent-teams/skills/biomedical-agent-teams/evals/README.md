# BMAT offline golden evaluation

This directory contains public synthetic regression tasks for BMAT policy and
evaluator wiring. The harness is offline: it does not browse, call a model, or
transmit workspace context.

`golden_tasks.jsonl` defines one task per line. `sample_outputs.jsonl` contains
the deterministic expected scorer surface, including positive failure cases and
non-block controls. Release counts are checked from the files themselves and
the package manifests; this README does not hardcode them.

## Validate and score

```bash
python evals/validate_golden_eval_schema.py --tasks evals/golden_tasks.jsonl --outputs evals/sample_outputs.jsonl

python evals/run_golden_eval.py --tasks evals/golden_tasks.jsonl --outputs evals/sample_outputs.jsonl --strict --gate
```

`--strict` rejects missing, duplicate, and unknown task IDs and malformed rows.
`--gate` enforces category-specific detection/action thresholds and the
false-positive block ceiling.

The v1.2 adversarial layer explicitly covers DOI wrong-paper resolution,
accession/version drift, identity-versus-entailment confusion, abstract-only and
preprint-only overclaim, four-axis scope mismatch, prognostic-to-predictive and
association-to-causality promotion, retracted sources, fixture/live confusion,
sample-mode/live confusion, same-model independence claims, stale artifacts,
unrelated tool receipts, review hash drift, experiment placeholders, omics
pseudoreplication, and tournament ranking/domain-pack failures.

Seven v1.2 tag rates are independently gated: `source_identity`,
`claim_entailment`, `artifact_integrity`, `review_independence`,
`experiment_design`, `omics_statistics`, and `domain_pack`. Their default
minimum is `1.0`; use `--min-adversarial-tag-rate` only for diagnostic runs, not
to weaken a release gate.

## Sample-mode boundary

CI uses deterministic sample mode:

```bash
python evals/run_model_golden_eval.py --tasks evals/golden_tasks.jsonl --alias evidence-audit-team --runtime codex --model sample-model --out outputs/bmat-model-sample.jsonl --sample-mode --then-score --gate
```

This tests task loading, output normalization, metadata capture, and scorer
integration. It does not invoke or evaluate a live model and must never be
reported as model performance, source verification, independent review, or
scientific validation.

Generated rows make this boundary machine-readable with
`evaluation_mode=sample-mode`, `sample_mode=true`,
`adapter_command_executed=false`, and
`live_model_evidence_eligible=false`.

## Live adapter boundary

Real model-in-loop evaluation is explicit:

```bash
python evals/run_model_golden_eval.py --tasks evals/golden_tasks.jsonl --alias evidence-audit-team --runtime codex --model "<model-id>" --out outputs/<model-id>.jsonl --adapter-command "python path/to/adapter.py" --then-score --gate
```

The adapter receives one task JSON object on stdin and must write one
scorer-compatible JSON object to stdout. Preserve the adapter command, model
identity, runtime metadata, prompt hash, output file, and retrieval time with
the report. Live adapter results remain an evaluation result, not a
full-protocol review receipt unless they independently satisfy the review
contracts and policies.

Adapter rows use `evaluation_mode=adapter-command` and
`adapter_command_executed=true`, while
`live_model_evidence_eligible=false` remains fixed: executing an adapter alone
does not prove which upstream model ran or establish independent-review
eligibility.

## Public omics smoke

`public_omics_benchmark_cases.jsonl` locks public identifiers and metadata-only
case shapes. `bmat_public_omics_benchmark_smoke.py` creates synthetic/proxy
bundles without downloading raw omics data. Its pass confirms metadata and
workflow wiring, not biological correctness or reproducibility of a raw-data
analysis.
