# Changelog

All notable BMAT-for-Codex changes are recorded here.

## 1.2.2 - 2026-09-08

- Bind required review checks to actual review scope and current input hashes;
  permit one review to cover multiple requirements without extra model calls.
- Bind post-write review to final/ledger snapshots and complete content-block maps.
- Verify exact quotation offsets and extraction locator maps; preserve distinct
  summary, human-verification, and unverified routes.
- Share order-independent DAG validation; add writer and omics pre-execution gates.
- Recompute tournament means, dispersion, alternate-order stability, and Elo;
  retain a qualitative route and explicit researcher ranking overrides.
- Keep schema 2.0 parsing compatibility while enforcing current release policy.
- Preserve compact defaults, 38 roles, six aliases, and researcher supervision.

## 1.2.1 - 2026-09-05

- Reject missing declared release artifacts and missing/draft hypothesis tournaments.
- Share artifact registration, mode planning, and tournament checks between CLIs.
- Hash ordinary JSON arrays/scalars without imposing artifact-object requirements.
- Generate smaller quick/compact plans and expose stage/file/reviewer counts.
- Preserve full gates for deep, audit, run, and full-tier workflows.
- Create honest empty tournament drafts and distinguish domain-file availability from reading.
- Unify independent-review guidance and keep generic research routing domain-neutral.
- Separate installed-package tests from repository marketplace tests; bundle user documentation.
- Add explicit smoke_passed/release_passed self-test modes and isolated-package CI.

Completed v2 tournament artifacts without a status field remain compatible.
Drafts are editable planning artifacts and never satisfy a release gate.

## 1.2.0 - 2026-07-10

### Added

- Strict v2 source-verification, source-corpus, claim-support, tool-ledger,
  review-runtime-receipt, experiment-design, hypothesis-tournament, and bundle
  manifest surfaces.
- Hash-bound release-bundle integrity and artifact identity checks.
- Conservative v1-to-v2 bundle migration with an explicit re-verification list
  and no in-place overwrite by default.
- Domain-pack routing contracts for generic biomedical, cell-therapy, and
  immuno-oncology workflows.
- Claim-support and tournament checkers plus expanded release regression cases.
- Ubuntu and Windows CI across supported Python versions.

### Changed

- Fixture and sample-mode source rows are explicitly non-release and
  `not-checked`; they can no longer stand in for verified retrieval.
- Claim support is bound to source-owned evidence spans and seven explicit
  scope axes.
- Independent-review eligibility now requires hash-bound input, prompt, output,
  and runtime receipts with author/reviewer identity checks. Same-model review,
  including a separate context, remains supplementary and non-independent.
- Full-protocol release requires an integrity manifest and structured gate
  evidence; prose labels cannot promote a bundle.
- Experiment design and hypothesis tournaments expose quantitative uncertainty,
  confounding, multiplicity, feasibility, safety, order sensitivity, and
  correlated-judgment limitations as structured fields.

### Validation boundary

A passing v1.2.0 validator establishes implemented process invariants. Source
identity, claim entailment, independent review, and scientific truth remain
distinct layers. See `docs/validation-boundaries.md`.

### Migration

Legacy bundles must be converted into a new v2 directory and re-verified before
release. The converter never invents verification, hashes, review identity, or
scientific support. See `docs/migration-v1-to-v2.md`.

## 1.1.1 - 2026-07-09

- Hardened release-artifact DAG/output alignment, runner scaffolds, checker
  version handling, translational post-write routing, and patch-version residue
  guards.

## 1.1.0

- Added lead decisions, omics manifest v2, source/support release gates,
  review-artifact hashes, experiment-design and omics metadata checks, expanded
  golden cases, and the public-omics metadata smoke harness.
