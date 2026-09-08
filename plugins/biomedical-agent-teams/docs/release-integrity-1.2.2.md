# Researcher-supervised release integrity in 1.2.2

BMAT assists a researcher who remains responsible for scientific judgment.
The 38 roles and six aliases are unchanged. Compact work remains inline-first;
logical writer and reviewer stages do not imply additional model calls or new
approval steps. A single real review can cover multiple required checks when
its scope, input snapshots, and independence classification satisfy each check.

## Review coverage

The selected workflow's versioned `required_checks` and `required_input_refs`
define minimum coverage. Release and Full validation also include requirements
recorded in the actual DAG and `required_reviews` in the lead/preflight contract.
An inline run without a DAG still has the selected workflow's minimum checks.
Deleting a reviewer node or changing its independence flag does not remove that
minimum. Record a changed plan and downgrade when required work is skipped.

Each review instance records `covered_node_ids`, `covered_check_ids`, and the
same check IDs in `checks_run`. The input refs and hashes must match the actual
reviewed files. Existing output, prompt, and runtime receipts remain required.
A citation-role name alone cannot establish contradiction or final coverage.
One combined review may cover `citation.identity`, `claims.contradictions`,
`claims.scope`, `final.coverage`, and `final.scope` when it actually performed
those checks on the frozen final candidate and its supporting files.

Same-model review remains useful but does not become independent. Likewise,
deterministic hash/locator checks are process checks, not scientific reviewers.
Fixture receipts are synthetic test inputs, never evidence of live review.

## Final candidate and claim map

Use this order: finish the ledger, write `final.md`, freeze the candidate,
review it, resolve issues and review any revisions, generate the bundle
manifest, then run `bmat_validate.py --bundle PATH --release`. Do not edit the
final document or completion label after the last successful check.

The post-write record contains:

- `reviewed_final_ref: "final.md"` and `reviewed_final_sha256`;
- `reviewed_ledger_ref: "claim_ledger.json"` and `reviewed_ledger_sha256`;
- `coverage_review_instance_id` identifying the actual final reviewer;
- `wording_policy`, either `literal` or `reviewed-paraphrase`;
- ordered `content_coverage` rows with `block_id`, `block_sha256`,
  `classification`, `claim_ids`, and `reason`.

`bmat_release_integrity.final_blocks` normalizes CRLF/CR to LF, splits Markdown
at blank lines, trims outer whitespace, and assigns B0001, B0002, etc. It hashes
each resulting UTF-8 block. Lists, tables, and paragraphs can contain multiple
claims; the reviewer maps every claim in the block. Hypotheses and researcher
interpretations can use the corresponding existing ledger claim types.
`heading`, `formatting`, and `non-claim` rows require a reason and no claim IDs.
The reviewer explicitly checks misclassification and incomplete claim mapping.

File digests bind exact bytes, independently of block normalization. A change
to the final file or ledger invalidates the prior snapshot even if the bundle
manifest is regenerated. `reviewed-paraphrase` allows natural Korean/English
restatement only when a current, complete, reviewer-bound map covers that claim.
The software cannot decide whether the reviewer classified prose correctly or
whether a paraphrase preserves scientific meaning.

## Source quotations, summaries, and scans

For each included evidence span, explicitly set `extraction.kind`:

- `quotation`: exact comparison with preserved text and a locator interval;
- `summary`: interpretation linked to verified spans and a `source.summary`
  review of the current source corpus;
- `human-verified`: attributable human `source.extraction` review binding the
  source snapshot and corpus, with a rationale;
- `not-checked`: incomplete extraction; it cannot qualify for current release.

Quotation extraction records `text_ref`, `text_sha256`,
`original_snapshot_sha256`, `extractor`, `extractor_version`,
`normalization: "NFC-LF"`, `offset_unit: "unicode-codepoint"`, and half-open
`start`/`end` offsets. NFC and LF normalization apply to both text and excerpt;
there is no fuzzy or whitespace-collapsing match. Binary PDF/HTML sources need
a preserved UTF-8 extraction; no automatic OCR or external service is invoked.

`locator_map_ref` and `locator_map_sha256` bind a separate JSON extraction map.
It repeats the text ref/hash, original snapshot hash, normalization, offset
unit, extractor, and version. Its `segments` contain `start`, `end`, `locator`,
`section`, `paragraph_or_table`, and `sentence_or_cell`. A quotation's interval
must fall within a segment whose four locator fields match the span. This
rejects a changed page/paragraph locator even when the same text occurs elsewhere.
Extraction tools or a researcher create this map from the source; a hash does
not independently prove that a PDF extractor mapped the original pages correctly.

Summary `supporting_span_ids` must refer to verified quotation/human spans from
the same source. Do not label a paraphrase as a quotation. For images or scans,
use the explicit human route or retain the unverified state. Do not invent
classification, offsets, locators, or review receipts for migrated evidence.

## Tournament arithmetic

Numeric tournaments preserve the actual judge-by-candidate matrices for primary
and alternate rounds. Judgment IDs are unique within each round. Presentation
positions must equal the recorded candidate order. A different seed alone does
not demonstrate a different order.

`aggregation.method` supports `mean` and `weighted-mean`. Weighted means require
all eight axis weights (nonnegative with a positive total); optional judge
weights cover every judge and are positive. Evidence strength and execution
priority remain separate axes. Disagreement uses unweighted `range` or
`population-sd` across judges, independently of aggregation weights.

The alternate round records its different permutation, actual scores, and
`alternate_ranking`. Numeric stability uses `pairwise-order-agreement`: each
candidate pair receives 1 for matching relations including matching ties, 0.5
when only one round ties, or 0 for a reversal. The reported value is the pair
mean. Ties use tolerance 1e-9; stored score rankings use descending aggregate
and hypothesis ID for exact ties. Arithmetic comparisons use tolerance 1e-9.

`ranking_model: "weighted-score"` uses the aggregate ranking. `elo` additionally
requires `elo_input` with replayable settings and match outcomes. A final
researcher priority that overrides the model ranking needs
`ranking_override_reason`. Other numeric models are not certified by 1.2.2.

For a qualitative comparison, use `aggregation.method: "qualitative"` and
`ranking_model: "qualitative"`, empty numeric arrays/model ranking, and no Elo
input or numeric ratings. Retain candidate dispositions and rationale. An
unperformed sensitivity check has `performed: false`, null alternate seed and
null stability, with limitations. If performed, preserve a different order,
alternate ranking, and hash-bound JSON `review_artifact_ref` containing
`primary_order`, `primary_ranking`, `alternate_order`, `alternate_ranking`, and
`rationale`. Qualitative sensitivity does not claim numeric rank stability.

## Workflow execution and compatibility

All DAGs explicitly separate `W_write` from final review. Validation and
planning use a shared order-independent graph check and deterministic
topological ordering. Self-loops, cycles, unknown roles, missing dependencies,
and mismatched run-state dependencies fail. Completed dependent stages require
completed prerequisites.

Omics run planning includes `S1_setup` and `S1_smoke` before `S2_execute`.
Passed inference requires both gates to be passed upstream. Bulk and 10x work
route to existing track specialists; other single-cell work routes to the QC
specialist with bounded execution scope. The lead owns survival/multi-omics
execution using explicitly selected methods. Plan/audit modes describe analysis
plans or inspect existing results and cannot claim new analysis execution.
These DAGs document the contract; the scaffold CLI is not an execution engine.

Artifact schemas remain 2.0. Added fields are optional for parsing old bundles,
but current `--release` or Full validation requires the new bindings. Legacy
2.0 files are not silently certified; preserve originals, explicitly complete
missing evidence/review records, or retain a lower workflow label. Migration
must not infer missing quotation kinds or create successful review receipts.

The adapter accepts `--release` before `--codex-command`. It performs the final
release check after manifest generation and sends its output to the caller;
`adapter_validator_*` files describe the preliminary check. No bundle writes
follow the final release gate. Dry-run scaffolds remain incomplete.
