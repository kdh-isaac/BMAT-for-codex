# BMAT v1.2 validation boundaries

BMAT validates an auditable biomedical workflow bundle. It does not certify
that a scientific statement is true. Release reports must keep the following
five questions separate.

| Layer | Question answered | Principal v2 evidence | What it does not prove |
| --- | --- | --- | --- |
| Process and contract validation | Are required artifacts present, schema-valid, internally consistent, run-bound, and hash-bound? | `bundle_manifest.json`, artifact identity fields, `bmat_validate.py --release` | Source existence, claim support, or scientific truth |
| Source identity verification | Does the cited identifier or preserved local snapshot resolve to the recorded source/version, with current integrity metadata? | `source_verification.json`, tool or human receipt, local snapshot hash | That the source entails a particular claim |
| Claim entailment and scope review | Does an owned evidence span support the bounded claim at the recorded strength and scope? | `source_corpus.json` evidence spans and `claim_support_matrix.json` | Independence of the reviewer or external truth |
| Independent review | Did an eligible separate model, review tool, or human review a frozen input snapshot under a verifiable runtime identity? | `review_artifact_manifest.json`, runtime receipt, input/prompt/output hashes | Replication, causal validity, consensus, or scientific truth |
| Scientific truth | Is the conclusion correct in the world and robust to bias, alternative explanations, and replication? | External evidence, domain expertise, suitable experiments, statistics, replication, and applicable oversight | BMAT cannot certify this layer |

## Release interpretation

`Full protocol followed` is a process label. It means that the current bundle
passed the release validator with the required source, claim-support, review,
and integrity receipts. It is not a truth label, regulatory approval, clinical
recommendation, or replacement for expert review.

A successful tool call proves only that the recorded operation completed. A
successful source lookup can establish source identity. Neither automatically
establishes claim entailment. A claim-support row must point to an evidence span
owned by the cited source and record all seven scope axes: species, cell type,
assay, endpoint, population or model, intervention or exposure, and biological
context.

Independent review is also a process property. `separate-model`,
`external-tool`, and `human` are eligible only when runtime identity, bounded
inputs, hashes, output, and handoff records validate. `same-model-self-review`
and `same-model-separate-context` can be useful supplementary checks, but they
are never independent-review evidence for the full-protocol gate.

## Fixture and sample-mode boundaries

- A `fixture` source-verification row is always `not-checked`,
  `fixture_only=true`, and `release_eligible=false`. Fixture content exercises
  schema and policy wiring; it is not retrieved evidence.
- Migration never upgrades fixture or missing verification to verified status.
- Golden-eval `--sample-mode` is deterministic evaluator plumbing. It does not
  execute or measure a live model. Live model evaluation requires an explicit
  `--adapter-command` and separately preserved results.
- The public-omics smoke harness uses metadata-only synthetic/proxy bundles. It
  downloads no raw omics data and does not validate biological conclusions.
- A checked-in release fixture demonstrates that the validator can accept a
  self-contained, hash-consistent example. It does not make that example a
  real literature review or scientific result.
- A schema pass checks shape. A policy pass checks implemented invariants.
  Neither substitutes for statistical diagnostics, risk-of-bias assessment,
  experimental controls, or subject-matter judgment.

## Reporting minimum

Every release-facing result should state, separately:

1. process/contract gate status;
2. source-identity verification status;
3. claim-entailment and scope status;
4. independent-review class and receipt status; and
5. the remaining scientific uncertainty and required external validation.

If a layer was not run, use the structured skip or downgrade fields and lower
the final label. Free-text confidence language cannot repair a missing receipt.
