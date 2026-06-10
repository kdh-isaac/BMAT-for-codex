# Independent Review Policy

Use this reference whenever a BMAT workflow claims validation, audit, review,
red-team, or independent verification.

## Terminology

- `independent_validation`: validation performed by a separate spawned subagent,
  separate model, tool-backed validator, external verifier, or explicitly
  independent human review.
- `same_model_separate_pass`: the current assistant performs a later validation
  pass using predeclared criteria. This is useful but is not fully independent.
- `self_ratification`: the same pass writes and validates claims without
  predeclared criteria, dissent preservation, or ledger comparison.

## Independence In Tool-Only Runtimes

Most Codex/agent runtimes cannot spawn a separate subagent, so role-to-role
"independence" collapses to a same-model second pass. In that case the practical
source of independence is **tool-backed external corroboration**: an external
tool call (PubMed, ClinicalTrials.gov, bioRxiv, ChEMBL, Open Targets, or another
database/API) that returns evidence matching the claim scope.

- A claim is `tool_corroborated` when a real external tool returned data
  supporting it at the stated scope (species, assay, cohort, endpoint).
- A claim checked only by a same-model second pass with no external tool is
  `same_model_separate_pass`, not independent.
- Prefer adding one decisive external tool check over adding another inline
  reviewer role when subagents are unavailable.

## Required Controls

1. Declare validator criteria before reviewing final prose whenever feasible.
2. Compare final prose directly against claim ledger row IDs or
   `allowed_final_wording`.
3. Do not introduce new evidence during validation unless the source corpus and
   claim ledger are updated first.
4. Preserve contradiction, negative evidence, and skipped-gate findings through
   final synthesis.
5. If validation was only a same-model separate pass, state that limitation and
   downgrade the workflow label when the output would otherwise claim full
   protocol compliance.

## Labeling Rules

| validation surface | allowed wording | workflow label effect |
|---|---|---|
| spawned subagent, separate model, tool-backed validator, or human reviewer | independent validation | may support `Full protocol followed` if all other required gates pass |
| external database/API tool call returning matching evidence (tool-backed corroboration) | tool-corroborated, externally checked | may support `Full protocol followed` for that claim if scope matches |
| same model separate pass with declared criteria and ledger comparison | same-model separate-pass validation | usually `pass-with-caveats` or non-full label unless user requested compact output |
| same pass without criteria or ledger comparison | self-ratification risk | downgrade or block high-confidence release |

## FM10 Handling

If FM10 is suspected in a high-confidence source-backed deliverable, correct the
workflow by adding an independent audit section, running a separate validator
surface if available, or downgrading the workflow label and claim strength.
