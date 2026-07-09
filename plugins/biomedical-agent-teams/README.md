# Biomedical Agent Teams Codex Plugin

Codex Desktop compatible plugin wrapper for the `biomedical-agent-teams` skill.

Current plugin version: `1.1.1`.

## Purpose

BMAT is a lead-controlled biomedical research workflow router for evidence
audit, public-omics analysis, hypothesis tournaments, experiment design,
translational scouting, loop checks, and validator-backed artifact bundles.

Codex loads `skills/biomedical-agent-teams/SKILL.md` as the router. The router
then points to one command recipe at a time, keeping the root prompt small and
making the selected workflow auditable.

## Package Contents

| Resource | Count |
| --- | ---: |
| Agent role prompts | 38 |
| Command recipes | 6 |
| Contract schemas | 23 |
| Templates | 21 |
| Markdown references | 10 |
| JSON references | 1 |
| Loop recipes | 4 |
| Codex reviewer TOML templates | 14 |
| Workflow DAGs | 6 |
| Domain packs | 3 |
| Package scripts | 14 |
| Eval scripts | 3 |
| Public omics benchmark cases | 9 |

Important files:

- `.codex-plugin/plugin.json`: marketplace metadata and Codex UI description.
- `skills/biomedical-agent-teams/SKILL.md`: lightweight router.
- `skills/biomedical-agent-teams/source-manifest.json`: canonical resource list.
- `skills/biomedical-agent-teams/agent-registry.json`: role metadata and
  spawnable reviewer bindings.
- `skills/biomedical-agent-teams/workflows/*.json`: alias-specific workflow DAGs.
- `skills/biomedical-agent-teams/scripts/bmat_validate.py`: artifact bundle
  schema and policy gate.
- `skills/biomedical-agent-teams/scripts/bmat_run.py`: local runner, DAG
  normalizer, validator wrapper, and Markdown workbench exporter.
- `skills/biomedical-agent-teams/scripts/bmat_codex_adapter.py`: local adapter
  scaffold for preflight -> optional Codex command -> artifact validation.
- `skills/biomedical-agent-teams/scripts/bmat_public_omics_benchmark_smoke.py`:
  metadata-only public benchmark smoke harness for 10x/GEO/bulk/CITE-seq/VDJ/multiome cases.

## Current Capabilities

- Lazy-loads only the selected workflow recipe and its required resources.
- Records runtime capability, source lock, external-tool authorization,
  reviewer strategy, validator availability, and label ceiling before strong
  workflow claims are made.
- Records `lead_decision.json` for source-backed `standard`, `deep`, `audit`,
  team-DAG, and full-protocol runs.
- Supports `--tier compact|full` and omics subtracks such as `bulk-rnaseq`,
  `tenx-gex`, `tenx-cellplex`, `tenx-citeseq`, `tenx-vdj`, and `tenx-multiome`.
- Uses `omics_run_manifest.json` v2 to contract 10x Cell Ranger artifacts,
  doublet/ambient/pseudobulk policy, and bulk RNA-seq design/provenance.
- Supports `inline_first_selective_review` and `team_level_selective_dag`.
- Routes substantive public-omics work through `omics-analysis-team` with code,
  provenance, and statistics reviewer floors when runtime support exists.
- Tracks source/result/claim relationships through `results_integration.json`.
- Tracks source/source-span verification through `source_verification.json` and
  high-confidence/tool/analysis/blocked claim support through
  `claim_support_matrix.json`.
- Tracks honest tool use through `tool_call_ledger.json` and
  `bmat_tool_ledger_check.py`.
- Validates artifact labels, source-backed claims, lead-decision hard gates,
  omics manifest v2 requirements, final wording, PMID drift, contradiction,
  overclaim, runtime mismatch, loop state, ranking semantics, workflow DAG
  alias/mode/id/track consistency, privacy-aware tool-ledger policy, and
  independent-review evidence. In `--release` mode it also hard-fails missing
  `jsonschema`, unverifiable source-backed claims, unsupported `claim_profile`
  rows, missing high-confidence support matrix rows, sample-mode model evidence
  overclaims, and review artifact hash drift.

## Workflow Structure

```mermaid
flowchart TD
    accTitle: BMAT v1.1.1 Workflow Structure
    accDescr: Full package workflow from Codex routing through command DAGs, optional team, reviewer, tool, and loop lanes, artifact bundle creation, validation gates, and final label selection.

    request["1. User request<br/>or explicit BMAT alias"]
    router["2. SKILL.md lightweight router<br/>selects one command recipe"]
    recipe["3. Command recipe<br/>loads only required agents,<br/>references, templates, contracts, scripts"]
    preflight["4. Runtime, scope, source, and strategy lock<br/>mode, scope, source needs,<br/>tools, file/write, web, spawn support"]
    strategy{"5. Execution strategy"}

    request --> router --> recipe --> preflight --> strategy

    strategy --> inline["inline_first_selective_review<br/>default lead-controlled workflow"]
    strategy -. "only for broad independent axes" .-> team_lane
    strategy -. "only for watch / inbox / recurrence" .-> loop_lane

    inline --> dag_select{"6. Alias-specific workflow DAG"}

    subgraph dag_catalog["Canonical command DAGs in workflows/*.json"]
        direction TB
        brc["biomedical-research-council<br/>S0 context lock<br/>S1 source lock<br/>S2 claim graph<br/>S3 evidence review<br/>S4 write + validate"]
        idea["idea-discovery-team<br/>S0 context lock<br/>S1 generate hypotheses<br/>S2 rank hypotheses<br/>S3 confounder critique<br/>S4 post-write validate"]
        omics["omics-analysis-team<br/>S0 context lock<br/>S1 plan / curate data<br/>S2 execute analysis<br/>S3 stats validation<br/>S4 code review<br/>S5 post-write validate"]
        audit["evidence-audit-team<br/>S0 context lock<br/>S1 source corpus<br/>S2 claim ledger<br/>S3 citation check<br/>S4 contradiction check<br/>S5 post-write validate"]
        design["experiment-design-team<br/>S0 context lock<br/>S1 design plan<br/>S2 statistics plan<br/>S3 claim lock<br/>S4 post-write validate"]
        scout["translational-scout-team<br/>S0 context lock<br/>S1 clinical / trial sources<br/>S2 IP + regulatory<br/>S3 safety review<br/>S4 post-write validate"]
    end

    dag_select --> brc
    dag_select --> idea
    dag_select --> omics
    dag_select --> audit
    dag_select --> design
    dag_select --> scout

    subgraph team_lane["Optional team_level_selective_dag lane"]
        direction TB
        team_plan["team_spawn_plan<br/>dependency-aware lane selection"]
        team_outputs["team_output_artifacts<br/>artifact path, checks, dependencies"]
        team_record["run_state team_spawn_lanes<br/>and stage handoff"]
        team_plan --> team_outputs --> team_record
    end

    subgraph reviewer_lane["Optional selective spawned review lane"]
        direction TB
        registry["agent-registry.json<br/>codex-agents/*.toml"]
        spawned["spawned_agent_instances<br/>role, task, status, output_artifact"]
        review_contract["spawned-agent-output contract<br/>findings, confidence, checks"]
        review_handoff["accepted findings<br/>merged back into claim ledger"]
        registry --> spawned --> review_contract --> review_handoff
    end

    subgraph tool_lane["Tool and result honesty lane"]
        direction TB
        tool_calls["tool_call_ledger.json<br/>success / skipped / unavailable / blocked / failed"]
        result_map["results_integration.json<br/>source -> result -> claim mapping"]
        tool_check["bmat_tool_ledger_check.py<br/>registered tools and downgrade reasons"]
        tool_calls --> result_map --> tool_check
    end

    subgraph loop_lane["Optional recurring loop lane"]
        direction TB
        loop_recipe["loops/*.md recipe"]
        loop_state["loop_state.json"]
        loop_check["bmat_loop_check.py<br/>freshness, connector, objection,<br/>release-artifact policy"]
        loop_recipe --> loop_state --> loop_check
    end

    brc --> bundle
    idea --> bundle
    omics --> bundle
    audit --> bundle
    design --> bundle
    scout --> bundle
    team_record --> bundle
    review_handoff --> bundle
    tool_check --> bundle
    loop_check --> bundle
    bundle -. "independent review required by recipe or label" .-> registry

    bundle["7. Canonical artifact bundle<br/>run_state.json<br/>runtime_capability_preflight.json<br/>source_corpus.json<br/>claim_ledger.json<br/>stage_evaluation.json<br/>post_write_validation.json<br/>final.md"]
    extras["Policy-checked extras<br/>lead_decision / workflow_dag<br/>results_integration / tool_call_ledger<br/>source_verification / claim_support_matrix<br/>omics_run_manifest / omics_metadata_check<br/>experiment_design / review_artifact_manifest"]
    gates{"8. Release gates"}
    postwrite["post-write-final-validator<br/>final wording and limitation check"]
    validate["bmat_validate.py<br/>bundle schema + policy gate<br/>source-backed claims, DAG consistency,<br/>independent review, final wording"]
    label{"9. Strongest allowed final label"}

    bundle --> extras --> gates
    gates --> postwrite --> validate --> label

    label --> full["Full protocol followed"]
    label --> contract["Contract-shaped artifact bundle"]
    label --> compact["Compact standard workflow"]
    label --> narrative["BMAT-informed narrative review"]
    label --> limited["Limited capability-downgraded workflow"]
    label --> partial["Partial workflow; formal gates skipped"]
    label --> blocked["Blocked"]
```

The lead owns the router decision, runtime preflight, selected command DAG,
central claim ledger, artifact bundle, and final synthesis. Team, reviewer,
tool/result, and recurring-loop lanes run only when the selected recipe,
execution strategy, risk class, or requested label requires them. Full-protocol
release is allowed only after the complete bundle and policy-checked optional
artifacts satisfy the post-write and validator gates.

## Full Protocol Bundle

The strongest final label, `Full protocol followed`, requires validator-visible
artifacts:

- `run_state.json`
- `runtime_capability_preflight.json`
- `lead_decision.json`
- `source_corpus.json`
- `claim_ledger.json`
- `stage_evaluation.json`
- `post_write_validation.json`
- `final.md`

Optional but policy-checked artifacts include:

- `workflow_dag.json`
- `results_integration.json`
- `tool_call_ledger.json`
- `omics_run_manifest.json`
- `source_verification.json`
- `claim_support_matrix.json`
- `omics_metadata_check.json`
- `experiment_design.json`
- `review_artifact_manifest.json`

The validator fails full-protocol claims when required artifacts are missing,
required stages are blocked, post-write validation does not pass, independent
review is not represented by a complete execution record, source-backed claims
do not resolve to included sources, high-confidence final wording drifts from
the ledger, lead routing is missing where required, 10x/bulk omics provenance is
under-specified, privacy-sensitive tool calls cross an unauthorized boundary, or
workflow DAG alias/mode/id/track fields disagree with the run state.

Release-bound validation should use `skills/biomedical-agent-teams/scripts/bmat_validate.py --release`.
`--sample-mode` golden eval output remains a CI harness and is not live
model-in-the-loop validation evidence.

## Latest Local Verification

Verified locally on 2026-07-09 KST:

| Check | Result |
| --- | --- |
| Source vs installed cache `diff -qr` | clean |
| Installed plugin | `biomedical-agent-teams` `1.1.1`, enabled |
| Prompt surface | `biomedical-agent-teams/1.1.1/.../SKILL.md` visible |
| Targeted tests | `133 passed` |
| Full tests | `243 passed, 162 subtests passed` |
| Package check / self-test / release fixture / strict golden gate | passed |
| Public omics benchmark smoke | 9/9 metadata-only bundles passed |
| Adapter dry-run smoke | validator exit 0 |

## Install

Recommended: register the GitHub-hosted marketplace, then install from the
Codex plugin browser:

```bash
codex plugin marketplace add kdh-isaac/BMAT-for-codex --ref main
codex
```

In Codex, open the plugin browser:

```text
/plugins
```

Find **Biomedical Agent Teams** under the
`biomedical-agent-teams-marketplace` marketplace and choose **Install plugin**.

Developer fallback: clone the repository and register the local marketplace
path when testing unpublished changes:

```bash
git clone https://github.com/kdh-isaac/BMAT-for-codex.git
cd BMAT-for-codex
codex plugin marketplace add .
codex
```

Then open `/plugins` and install **Biomedical Agent Teams** from the local
marketplace entry. Restart Codex Desktop if the plugin list does not refresh
immediately.

## Primary Aliases

- `biomedical-research-council`
- `idea-discovery-team`
- `omics-analysis-team`
- `evidence-audit-team`
- `experiment-design-team`
- `translational-scout-team`

Some clients reserve slash-prefixed commands. Use the plain alias form when
that happens.

## Validation

From this plugin root:

```bash
python skills/biomedical-agent-teams/scripts/bmat_package_check.py --root .
python skills/biomedical-agent-teams/scripts/bmat_selftest.py --root .
python skills/biomedical-agent-teams/evals/validate_golden_eval_schema.py --tasks skills/biomedical-agent-teams/evals/golden_tasks.jsonl --outputs skills/biomedical-agent-teams/evals/sample_outputs.jsonl
python skills/biomedical-agent-teams/evals/run_golden_eval.py --tasks skills/biomedical-agent-teams/evals/golden_tasks.jsonl --outputs skills/biomedical-agent-teams/evals/sample_outputs.jsonl --strict --gate
python skills/biomedical-agent-teams/evals/run_model_golden_eval.py --tasks skills/biomedical-agent-teams/evals/golden_tasks.jsonl --alias evidence-audit-team --runtime codex --model sample-model --out bmat_eval_outputs/model-sample.jsonl --sample-mode --then-score --gate
python skills/biomedical-agent-teams/scripts/bmat_public_omics_benchmark_smoke.py --out bmat_eval_outputs/public-omics-benchmark --validate --force
```

When test tooling is available, also run from the marketplace root:

```bash
uvx --with pytest --with jsonschema python -B -m pytest -p no:cacheprovider tests plugins/biomedical-agent-teams/skills/biomedical-agent-teams/tests -q
```
