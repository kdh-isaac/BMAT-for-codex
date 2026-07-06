# Results Integration Template

Use after literature lookup, omics analysis, clinical or translational scouting,
local validator output, spawned reviewer output, or human review changes a
claim, result interpretation, ranking, or release label.

Do not report a tool as used unless it has a matching tool-use row. Do not write
final biomedical claims from tool output until the accepted result is mapped to
the source corpus and central claim ledger.

## Header

| field | value |
|---|---|
| integration_id | RI-YYYYMMDD-001 |
| schema_version | 1.0 |
| plugin_version | 1.1.0 |
| workflow_run_id |  |
| source_corpus_lock | locked / partial / missing |
| input_artifacts |  |
| final_claim_policy | ledger-only / downgrade-unmapped-results / blocked |
| human_review_status | not-needed / pending / completed / blocked |

## Tool Use Log

| tool_id | invocation_surface | status | used | retrieval_date | source_corpus_rows | result_rows | downgrade_reason |
|---|---|---|---|---|---|---|---|
| pubmed-ncbi-entrez | web / MCP / API / unavailable | used / unavailable / skipped / blocked / failed | true / false |  | SC-001 | RI-ROW-001 |  |
| local-bmat-validators | local script | used / unavailable / skipped / blocked / failed | true / false | not-applicable |  | RI-ROW-002 |  |

## Result Rows

| result_id | result_type | source_ref | claim_ids | status | evidence_direction | confidence | effect_or_observation | sample_or_model_scope | statistical_support | interpretation | limitations | ledger_action | reviewer_or_human_gate |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| RI-ROW-001 | literature / omics / clinical / experiment-design / translational / tool-output / reviewer-output / statistic / figure / other | SC-001 | CL-001 | support / contradiction / null / ambiguous / qc-failed / excluded / not-reviewed | supports / weakens / mixed / neutral / not-applicable | high / moderate / low / insufficient / not-assessed |  |  |  |  |  | add / update / downgrade / exclude / no-change / block |  |

## Integration Rules

1. `support` can strengthen a claim only when source corpus, limitations, and
   review status are sufficient for the intended label.
2. `contradiction`, `qc-failed`, or `ambiguous` must downgrade, exclude, or block
   the affected claim unless a reviewer or human gate resolves the issue.
3. `null` is an interpretable result, not missing data. State whether it is
   underpowered, design-limited, or genuinely informative.
4. `not-reviewed` rows cannot support high-confidence final wording.
5. If source corpus or claim ledger mapping is incomplete, set
   `final_claim_policy` to `downgrade-unmapped-results` or `blocked`.

## Release Notes

- Tool/source limitations:
- Result rows excluded from final wording:
- Claims downgraded or blocked:
- Human review or reviewer gates still pending:
