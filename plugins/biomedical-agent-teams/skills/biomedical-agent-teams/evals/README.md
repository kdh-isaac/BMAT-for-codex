# BMAT Offline Golden-Task Eval

This directory defines a public-only, synthetic golden-task scaffold for
measuring whether BMAT detects common biomedical audit failures. It includes
failure-mode tasks and non-block negative controls so false-positive block rate
has a denominator.

The harness is offline. It does not call models, browse the web, or transmit
workspace context. Generate candidate outputs separately, save them as JSONL,
then score them locally.

## Input

`golden_tasks.jsonl` contains one task per line:

```json
{"task_id":"GT-001","failure_mode":"fabricated_pmid","expected_detection":["fabricated_identifier"],"expected_block":true}
```

An output JSONL file should contain:

```json
{"task_id":"GT-001","detected_failure_modes":["fabricated_identifier"],"blocked":true,"downgraded":true,"output_text":"..."}
```

## Run

```bash
python3 evals/run_golden_eval.py --tasks evals/golden_tasks.jsonl --outputs evals/sample_outputs.jsonl
```

Use `--strict` in CI or release checks to fail when an output file contains
unknown task IDs, duplicate task IDs, or missing task IDs:

```bash
python3 evals/run_golden_eval.py --tasks evals/golden_tasks.jsonl --outputs evals/sample_outputs.jsonl --strict
```

## Metrics

- `unsupported_claim_detection_rate`
- `citation_drift_detection_rate`
- `fabricated_identifier_detection_rate`
- `overclaim_downgrade_rate`
- `false_positive_block_rate`
- `output_integrity_ok`
- `unknown_output_task_ids`
- `duplicate_output_task_ids`
- `token_or_word_overhead`
