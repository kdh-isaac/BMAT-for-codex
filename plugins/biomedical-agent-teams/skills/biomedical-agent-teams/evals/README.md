# BMAT Offline Golden-Task Eval

This directory defines a public-only, synthetic golden-task gate for measuring
whether BMAT detects common biomedical audit failures. It includes 24 tasks:
22 positive failure-mode cases and 2 non-block negative controls so
false-positive block rate has a denominator.

The harness is offline. It does not call models, browse the web, or transmit
workspace context. Generate candidate outputs separately, save them as JSONL,
then score them locally.

## Input

`golden_tasks.jsonl` contains one task per line:

```json
{"task_id":"GT-001","failure_mode":"fabricated_pmid_identifier","expected_detection":["fabricated_identifier","pmid_drift"],"expected_block":true,"tags":["pmid_drift","citation","fabricated_identifier"]}
```

An output JSONL file should contain:

```json
{"task_id":"GT-001","detected_failure_modes":["fabricated_identifier"],"blocked":true,"downgraded":true,"output_text":"..."}
```

Required output fields are `task_id`, `detected_failure_modes`, and `blocked`.
`downgraded`, `output_text`, and `word_count` are optional but recommended.

## Run

```bash
python evals/run_golden_eval.py --tasks evals/golden_tasks.jsonl --outputs evals/sample_outputs.jsonl
```

Validate only the JSONL task/output shape with the dependency-free wrapper:

```bash
python evals/validate_golden_eval_schema.py --tasks evals/golden_tasks.jsonl --outputs evals/sample_outputs.jsonl
```

Use `--strict` in CI to fail when schema validation fails or an output file
contains unknown task IDs, duplicate task IDs, or missing task IDs:

```bash
python evals/run_golden_eval.py --tasks evals/golden_tasks.jsonl --outputs evals/sample_outputs.jsonl --strict
```

Use `--gate` for release checks. The default gate requires 10-30 tasks,
complete output integrity, schema-valid rows, perfect detection for PMID drift,
contradiction, overclaim, tournament-loop, tournament-ranking, Codex-runtime,
semantic-scope, and expected-block action categories, and zero false-positive
blocks in negative controls:

```bash
python evals/run_golden_eval.py --tasks evals/golden_tasks.jsonl --outputs evals/sample_outputs.jsonl --strict --gate
```

## Model-In-Loop Harness

`run_model_golden_eval.py` generates scorer-compatible model-style outputs.
CI should use deterministic sample mode:

```bash
python evals/run_model_golden_eval.py --tasks evals/golden_tasks.jsonl --out evals/outputs/model-sample.jsonl --sample-mode --then-score --gate
```

Real Codex/model execution is intentionally explicit. Provide an adapter command
that receives one task JSON object on stdin and writes one output JSON object on
stdout:

```bash
python evals/run_model_golden_eval.py --tasks evals/golden_tasks.jsonl --alias evidence-audit-team --runtime codex --model "<model-id>" --out evals/outputs/<model-id>.jsonl --adapter-command "python path/to/adapter.py" --then-score --gate
```

The adapter output row must include `task_id`, `detected_failure_modes`, and
`blocked`; `downgraded` and `output_text` are recommended. The harness adds
runtime metadata such as `plugin_version`, host OS, Python invocation, model
name, and prompt hash before scoring.

## Metrics

- `unsupported_claim_detection_rate`
- `citation_drift_detection_rate`
- `fabricated_identifier_detection_rate`
- `overclaim_downgrade_rate`
- `pmid_drift_detection_rate`
- `contradiction_detection_rate`
- `tournament_loop_detection_rate`
- `tournament_ranking_detection_rate`
- `codex_runtime_detection_rate`
- `semantic_scope_detection_rate`
- `expected_block_action_rate`
- `tag_detection_rates`
- `false_positive_block_rate`
- `output_integrity_ok`
- `schema_valid`
- `gate`
- `unknown_output_task_ids`
- `duplicate_output_task_ids`
- `token_or_word_overhead`
