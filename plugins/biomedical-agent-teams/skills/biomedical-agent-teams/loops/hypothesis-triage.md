# Hypothesis Triage Loop

Use for recurring triage of candidate biomedical hypotheses before promoting
them to a full `idea-discovery-team` or `experiment-design-team` workflow.

| field | value |
|---|---|
| loop_type | hypothesis_triage |
| default_trigger | new hypothesis added, new source delta affects ranking, or user-requested triage refresh |
| input_scope | hypothesis text, target/model/cell type, proposed mechanism, assayability constraints, public evidence scope |
| state_file | loop_state.json using `contracts/loop-state.schema.json` |
| source_delta | new literature, dataset feasibility changes, contradiction findings, or experiment feasibility notes |
| allowed_connectors | PubMed/NCBI Entrez, public omics repositories, pathway databases when allowed by scope |
| reviewer_lane | `contradiction-red-team`, `risk-of-bias-study-quality-auditor`, optional `omics-provenance-validator` |
| output_artifacts | triage matrix, EIG ranking delta, kill-test list, ledger handoff |
| stop_condition | top candidates ranked, low-quality duplicates collapsed, kill-tests assigned, or unresolved evidence blocks promotion |

## Loop Steps

1. Load previous hypothesis tournament state and claim ledger before adding new candidates.
2. Normalize entities and collapse duplicate or near-duplicate hypotheses.
3. Score novelty only after plausibility, assayability, safety, confounder
   resistance, and expected information gain are recorded.
4. Preserve contradictions and negative evidence as first-class reviewer objections.
5. Promote only candidates with explicit kill-tests and claim-ledger handoff.
6. Run `scripts/bmat_loop_check.py` before marking the triage loop stopped or complete.

## Release Rule

Release a ranking delta and next-experiment recommendation only when source
deltas are processed and reviewer objections are resolved or explicitly rejected
with rationale.
