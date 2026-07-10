---
name: biomedical-agent-teams
description: >
  BMAT for Codex v1.2.0 router for biomedical evidence audit, public omics,
  hypothesis tournaments, experiment design, translational scouting, and
  validator-backed v2 workflow bundles.
version: "1.2.0"
---

# Biomedical Agent Teams Router

This file is the lightweight BMAT router. Select one command recipe, then load
only the resources that recipe names.

## Router contract

1. Resolve every command recipe path relative to the directory containing this `SKILL.md`.
2. Read this router completely before task actions.
3. Select the narrowest matching command recipe and read it completely.
4. Do not load every agent, command, reference, contract, or template by default.
5. Use `source-manifest.json` and `scripts/bmat_docs_list.py` for inventory discovery.
6. Record ambiguous routing as an explicit assumption in the runtime preflight.
7. Keep raw/private data local and do not invent source, tool, reviewer, or
   validation evidence.

## Command routing

| Intent | Alias | Recipe |
| --- | --- | --- |
| Broad coordination, mechanism review, writing, or multi-lane synthesis | `biomedical-research-council` | `commands/biomedical-research-council.md` |
| Citation, PMID/DOI/accession, contradiction, overclaim, risk-of-bias, or final-claim audit | `evidence-audit-team` | `commands/evidence-audit-team.md` |
| Public omics, GEO, single-cell, bulk RNA-seq, QC, code review, or provenance | `omics-analysis-team` | `commands/omics-analysis-team.md` |
| Hypothesis generation, ranking, tournament, or idea triage | `idea-discovery-team` | `commands/idea-discovery-team.md` |
| Controls, sample size, assay, animal model, confounding, feasibility, or safety design | `experiment-design-team` | `commands/experiment-design-team.md` |
| Clinical trial, regulatory, IP, market, operations, or translation | `translational-scout-team` | `commands/translational-scout-team.md` |

If no specialized alias fits, start with `biomedical-research-council` and keep
the initial action reversible.

## Runtime preflight and strategy

Every non-trivial workflow records the requested alias, selected mode and tier,
deliverable, domain pack, evidence scope, risk class, file/shell/network/tool
capabilities, source-lock status, reviewer capability, external-service
authorization, compute budget, structured skip reasons, and label ceiling.

Default to `inline_first_selective_review`. Use
`team_level_selective_dag` only for genuinely independent decision axes with
explicit dependencies, handoffs, and a merge owner. Planned lanes and role names
are not proof of completed or independent review.

Nested spawning is disabled by default. If explicitly authorized, record the
depth and compute limits, handoff contracts, and single merge owner.

If shell/code execution is unavailable, record
`validator_unavailable_due_to_runtime`. Do not claim `Full protocol followed`
when the release validator, required source checks, integrity manifest, or
eligible independent review cannot run.

## v2 evidence spine

For source-backed claims:

1. Lock the question, entities, intended use, domain pack, and evidence scope.
2. Build `source_corpus.json` with included/excluded status and source-owned
   evidence spans.
3. Create `source_verification.json` from a recorded live-tool, attributable
   human, or hash-bound local-file check. Fixture and not-checked rows stay
   release-ineligible.
4. Decompose final statements into atomic `claim_ledger.json` rows.
5. Map each release claim to a source span in `claim_support_matrix.json` and
   assess species, cell type, assay, endpoint, population/model,
   intervention/exposure, and biological-context scope.
6. Record tool results and claim changes in `tool_call_ledger.json` and
   `results_integration.json`.
7. Write final text from allowed ledger wording only, then run post-write and
   bundle validation.

Tool success proves execution, not source entailment. Source identity
verification proves the recorded identity/version/integrity check, not that the
source supports a claim. Claim-support review evaluates bounded entailment and
scope, not scientific truth.

## Review honesty

Apply `references/independent-review-policy.md` before using independent-review
wording. Review classes are:

- `same-model-self-review`: supplementary, never independent;
- `same-model-separate-context`: supplementary, never independent;
- `separate-model`: eligible only with distinct, available runtime identity;
- `external-tool`: eligible only when the tool performed the declared review,
  not merely retrieval or schema validation; and
- `human`: eligible with attributable, privacy-conscious receipt evidence.

Every eligible review binds exact input refs and hashes, frozen prompt and hash,
output and hash, runtime receipt and hash, checks run, claim changes, and ledger
handoff. A spawn event, second pass, reviewer name, or fixture cannot substitute
for those receipts.

## Label ceiling

Use the strongest label supported by structured artifacts:

- `Full protocol followed`: complete release bundle, eligible source/support
  evidence, required review receipts, final integrity manifest, and passing
  `bmat_validate.py --release`;
- `Contract-shaped artifact bundle`: schema-shaped artifacts without all
  release evidence;
- `Compact standard workflow`: lower-risk source-aware work not requiring full
  audit gates;
- `Biomedical Agent Teams-informed narrative review`: narrative guidance
  without a formal bundle;
- `Limited capability-downgraded workflow`: material runtime or source
  capability unavailable;
- `Partial workflow; formal gates skipped`: requested formal gates were not
  completed; or
- `Blocked`: missing inputs, safety/privacy constraint, failed validation, or
  absent approval prevents a defensible result.

The final rendered label must match `run_state.final_label`; prose cannot
promote it. `Full protocol followed` is process evidence, not scientific truth,
clinical approval, or regulatory certification.

## Workflow-specific boundaries

For omics, lock genome build, annotation, sample IDs, biological unit,
contrasts, exclusions, QC, normalization, batch handling, and multiplicity
before confirmatory interpretation. Keep raw data read-only. Use a small
fixture/subset smoke before long or high-memory work. The public-omics benchmark
smoke is metadata-only and downloads no raw data.

For experiment design, require explicit experimental/observational units,
controls, quantitative sample-size inputs or a blocked placeholder, multiplicity
plan, feasibility, confounders, safety/human gates, and verified reagent claims.
A process-valid design is not evidence that the experiment will succeed.

For hypothesis tournaments, use domain-pack selection, blinded candidate IDs,
randomized order, per-judge scores, aggregate and disagreement reports, an
alternate-order sensitivity check, uncertainty, compute/iteration limits, and
an explicit same-model correlated-judgment limitation. A winner is a prioritised
hypothesis, not established truth.

## Fixtures and evaluation

Golden `--sample-mode` is deterministic evaluator wiring. It is not live model
performance. Real model evaluation requires `--adapter-command` and separately
preserved outputs. Checked-in fixtures exercise schemas and policies; fixture
verification is `not-checked`, `fixture_only=true`, and
`release_eligible=false`.

For benchmark or hidden-evaluation work, do not inspect hidden truth files,
private results, scoring scripts, Dockerfiles, or answer keys unless the user
explicitly requests benchmark-infrastructure review. Keep any visible
evaluation internals isolated from the scientific answer.

Migration from v1 to v2 is conservative. `scripts/bmat_migrate_bundle.py`
writes a new bundle, preserves the original, emits a migration report and
re-verification list, and never synthesizes verification, hashes, reviewer
identity, or scientific support.

## Resource entrypoints

- `source-manifest.json`: canonical inventory and release features.
- `manifest.json`: versioned resource counts.
- `agent-registry.json`: reviewer capabilities and independence classes.
- `workflows/*.json`: command DAGs.
- `contracts/source-verification.schema.json`: source identity receipts.
- `contracts/claim-support-matrix.schema.json`: span-bound scope/entailment.
- `contracts/review-artifact-manifest.schema.json` and
  `contracts/review-runtime-receipt.schema.json`: review evidence.
- `contracts/experiment-design.schema.json`: quantitative design contract.
- `contracts/hypothesis-tournament.schema.json`: tournament contract.
- `contracts/bundle-manifest.schema.json`: release integrity manifest.
- `scripts/bmat_source_check.py`: source-verification generator/checker.
- `scripts/bmat_claim_support_check.py`: claim-support checker.
- `scripts/bmat_experiment_design_check.py`: design checker.
- `scripts/bmat_tournament_check.py`: tournament checker.
- `scripts/bmat_bundle_manifest.py`: final integrity-manifest generator.
- `scripts/bmat_validate.py`: schema and policy gate.
- `scripts/bmat_package_check.py`: inventory, count, version, and router gate.
- `evals/run_golden_eval.py`: offline golden scorer.
- `evals/run_model_golden_eval.py`: explicit sample/live adapter boundary.

## Maintenance gate

Run maintenance commands from the repository or marketplace root. The core
release sequence is:

```bash
python plugins/biomedical-agent-teams/skills/biomedical-agent-teams/scripts/bmat_package_check.py --root plugins/biomedical-agent-teams
python plugins/biomedical-agent-teams/skills/biomedical-agent-teams/scripts/bmat_selftest.py --root plugins/biomedical-agent-teams
python plugins/biomedical-agent-teams/skills/biomedical-agent-teams/evals/validate_golden_eval_schema.py --tasks plugins/biomedical-agent-teams/skills/biomedical-agent-teams/evals/golden_tasks.jsonl --outputs plugins/biomedical-agent-teams/skills/biomedical-agent-teams/evals/sample_outputs.jsonl
python plugins/biomedical-agent-teams/skills/biomedical-agent-teams/evals/run_golden_eval.py --tasks plugins/biomedical-agent-teams/skills/biomedical-agent-teams/evals/golden_tasks.jsonl --outputs plugins/biomedical-agent-teams/skills/biomedical-agent-teams/evals/sample_outputs.jsonl --strict --gate
uvx --with pytest --with jsonschema python -B -m pytest -p no:cacheprovider tests plugins/biomedical-agent-teams/skills/biomedical-agent-teams/tests -q
```

Also run the deterministic sample-model gate, metadata-only public-omics smoke,
release fixture validation, and migration regression tests on a clean tree.
Supported release Python versions are 3.10-3.13. Do not run live network
resolution, live models, or raw-data downloads in CI.
