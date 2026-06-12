# Claim Audit Inbox Loop

Use for recurring triage of draft claims, manuscript snippets, report bullets,
agent outputs, or review comments that need BMAT evidence auditing.

| field | value |
|---|---|
| loop_type | claim_audit_inbox |
| default_trigger | new claim item added to the inbox or user-requested audit sweep |
| input_scope | claim text, source IDs, draft path, intended audience, claim strength requested |
| state_file | loop_state.json using `contracts/loop-state.schema.json` |
| source_delta | newly attached citations, changed local artifacts, or reviewer objections |
| allowed_connectors | PubMed/NCBI Entrez, DOI/Crossref, ClinicalTrials.gov, repository APIs only when allowed by the claim scope |
| reviewer_lane | `claim-level-evidence-verifier`, `citation-verifier`, `contradiction-red-team` |
| output_artifacts | audit queue report, corrected wording, excluded-claim list, ledger delta |
| stop_condition | all high-priority claims triaged, source gaps blocked, reviewer objections resolved, or cycle budget reached |

## Loop Steps

1. Load the existing claim ledger and source corpus before auditing new claims.
2. Split claim items into atomic claims and assign claim IDs.
3. Verify each source-backed claim against included source IDs and retrieval dates.
4. Preserve unsupported but useful material as excluded or not-ledger-verified.
5. Add reviewer objections for citation drift, overclaim, scope mixing, missing
   uncertainty, or clinical/IP overreach.
6. Generate corrected wording only from passed or pass-with-caveats ledger rows.
7. Run `scripts/bmat_loop_check.py` before marking the inbox sweep complete.

## Release Rule

Do not release corrected wording when source deltas are pending or reviewer
objections remain open. The loop may stop with a blocked status and a minimum
evidence-needed list.
