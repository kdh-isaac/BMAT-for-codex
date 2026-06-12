# Weekly Literature Watch Loop

Use for recurring public literature surveillance. This loop is public-only by
default and must not include unpublished project text, private hypotheses,
patent-sensitive detail, PHI/PII, or controlled-access data in external search
queries unless a human gate explicitly approves that scope.

| field | value |
|---|---|
| loop_type | weekly_literature_watch |
| default_trigger | weekly scheduled run or user-requested refresh |
| input_scope | public search terms, normalized entities, date window, inclusion/exclusion rules |
| state_file | loop_state.json using `contracts/loop-state.schema.json` |
| source_delta | new or changed PMID/DOI/preprint records since the prior source corpus lock |
| allowed_connectors | PubMed/NCBI Entrez, bioRxiv/medRxiv, Crossref/DOI, Europe PMC when available |
| reviewer_lane | `citation-verifier`, `claim-level-evidence-verifier`, optional `contradiction-red-team` |
| output_artifacts | source delta, source corpus delta, claim ledger delta, human review packet |
| stop_condition | no qualifying new sources, cycle budget reached, source delta processed, or human gate blocks release |

## Loop Steps

1. Load prior loop state, source corpus, and claim ledger before searching.
2. Re-lock normalized entities, date window, and privacy boundary.
3. Query only approved public connectors and record retrieval date.
4. Classify source deltas as included, excluded, duplicate, not-checked, or blocked.
5. Update the source corpus and claim ledger only for included sources.
6. Run citation and claim-level checks for any source-backed wording.
7. If a contradiction or scope drift appears, add a reviewer objection rather
   than silently weakening the final report.
8. Run `scripts/bmat_loop_check.py` before marking the loop stopped or complete.

## Release Rule

Release only a reviewed source-delta summary and ledger delta. Do not publish
new mechanistic, clinical, IP, or experimental conclusions until the affected
claim rows pass the normal BMAT evidence gates.
