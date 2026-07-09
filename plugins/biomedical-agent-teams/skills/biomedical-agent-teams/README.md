# Biomedical Agent Teams

Current version: `1.1.0`.

Codex biomedical agent-team bundle with a lightweight router, protocol and
runtime lock, source corpus, central claim ledger, results integration,
tool-ledger honesty checks, workflow DAGs, loop-state resources, post-write
validation, and deterministic release gates.

Codex uses `SKILL.md` as the router and treats `agents/*.md` as role prompts.
Long governance instructions live in command recipes, references, templates,
contracts, and scripts that are lazy-loaded only when needed.

## 1.1.0 Resource Surface

| Resource | Count |
| --- | ---: |
| Agent role prompts in `agents/` | 38 |
| Workflow recipes in `commands/` | 6 |
| Contract schemas in `contracts/` | 23 |
| Templates in `templates/` | 21 |
| Markdown references in `references/` | 10 |
| JSON references in `references/` | 1 |
| Loop recipes in `loops/` | 4 |
| Codex reviewer TOML templates in `codex-agents/` | 14 |
| Workflow DAGs in `workflows/` | 6 |
| Domain packs in `domain-packs/` | 3 |
| Package scripts in `scripts/` | 14 |
| Eval scripts in `evals/` | 3 |
| Public omics benchmark cases in `evals/` | 9 |

## 1.1.0 Highlights

- `runtime_capability_preflight.json` is the canonical runtime capability
  preflight artifact.
- `lead_decision.json` is the auditable lead-scientist routing artifact for
  source-backed `standard`, `deep`, `audit`, team-DAG, and full-protocol runs.
- `omics_run_manifest.json` uses the v2 10x/bulk contract for Cell Ranger,
  matrix, doublet/ambient, pseudobulk, bulk reference, design, and DE provenance.
- `results_integration.json` maps sources, tools, reviewer outputs, omics
  outputs, and literature outputs back to claim rows.
- `source_verification.json` records source/source-span checks, while
  `claim_support_matrix.json` records high-confidence, tool-backed,
  analysis-backed, and blocked-claim support decisions.
- `omics_metadata_check.json`, `experiment_design.json`, and
  `review_artifact_manifest.json` provide release-checkable metadata,
  experimental design, and SHA-256-bound review artifact surfaces.
- `tool_call_ledger.json` records successful, skipped, blocked, failed, or
  unavailable tool calls.
- `workflow_dag.json` records alias-specific execution structure; the runner
  normalizes DAG `mode` and `workflow_id` to the requested run mode.
- `bmat_validate.py` enforces bundle shape, source-backed claim references,
  final wording, post-write verdict, independent review evidence, S3/high
  confidence gates, team DAG contracts, tool-ledger policy, workflow DAG
  alias/mode/id consistency, and release-mode source/support/artifact gates.
- `bmat_run.py` creates local dry-run bundles, supports `--tier compact|full`
  and `--track bulk-rnaseq|tenx-*|single-cell-other|survival|multi-omics`,
  writes workflow DAGs, runs validator/tool-ledger checks, and can export a
  Markdown workbench.
- `bmat_codex_adapter.py` scaffolds a local Codex orchestration bundle and
  validates collected artifacts.
- `bmat_public_omics_benchmark_smoke.py` runs metadata-only public benchmark
  smokes for 10x PBMC, GEO single-cell/CellPlex, bulk RNA-seq, CITE-seq,
  V(D)J, and multiome cases without downloading raw data.
- Golden eval gates cover PMID drift, contradiction, overclaim,
  tournament-loop, tournament-ranking, Codex-runtime, semantic-scope, 10x/bulk
  omics provenance, privacy/runtime, and expected-block behavior.
- Runtime documentation keeps only the current release surface; older release
  archaeology belongs in git history.

## Workflow Structure

```mermaid
flowchart TD
    accTitle: BMAT v1.1.0 End-to-End Workflow Structure
    accDescr: Full package workflow from Codex routing through command DAGs, optional team, reviewer, tool, and loop lanes, artifact bundle creation, validation gates, and final label selection.

    request["1. User request<br/>or explicit BMAT alias"]
    router["2. SKILL.md lightweight router<br/>selects one command recipe"]
    recipe["3. Command recipe<br/>loads only required agents,<br/>references, templates, contracts, scripts"]
    preflight["4. Runtime capability preflight<br/>mode, scope, source needs,<br/>tools, file/write, web, spawn support"]
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

    subgraph team_lane["Optional team-level DAG lane"]
        direction TB
        team_plan["team_spawn_plan<br/>dependency-aware lane selection"]
        team_outputs["team_output_artifacts<br/>artifact path, checks, dependencies"]
        team_record["run_state team_spawn_lanes<br/>and stage handoff"]
        team_plan --> team_outputs --> team_record
    end

    subgraph reviewer_lane["Optional spawned reviewer lane"]
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

The main workflow progresses from router selection to a validator-backed label.
The lead owns the router decision, runtime preflight, selected command DAG,
central claim ledger, artifact bundle, and final synthesis. Team, reviewer,
tool/result, and recurring-loop lanes run only when the selected recipe,
execution strategy, risk class, or requested label requires them. Team outputs
are proven by `team_output_artifacts`, reviewer execution is proven by
`spawned_agent_instances`, tool/result claims are reconciled through
`tool_call_ledger.json` and `results_integration.json`, and recurring loops are
checked by `bmat_loop_check.py`.

## Full Protocol Structure

```mermaid
flowchart TD
  A["Declared label: Full protocol followed"] --> B["Required bundle artifacts exist"]
  B --> C["Required stages pass"]
  C --> D["Source-backed claims resolve to included source_corpus rows"]
  D --> E["Results and tool-backed claims are reconciled"]
  E --> F["Independent review surface exists"]
  F --> G["Complete spawned_agent_instances record exists when required"]
  G --> H["post_write_validation verdict passes"]
  H --> I["final.md uses ledger-allowed wording"]
  I --> J["bmat_validate.py passes"]
```

Required full-protocol artifacts:

- `run_state.json`
- `runtime_capability_preflight.json`
- `lead_decision.json`
- `source_corpus.json`
- `claim_ledger.json`
- `stage_evaluation.json`
- `post_write_validation.json`
- `final.md`

Optional but policy-checked artifacts:

- `workflow_dag.json`
- `results_integration.json`
- `tool_call_ledger.json`
- `omics_run_manifest.json`
- `source_verification.json`
- `claim_support_matrix.json`
- `omics_metadata_check.json`
- `experiment_design.json`
- `review_artifact_manifest.json`

Release-bound validation should use `scripts/bmat_validate.py --release`.
Release mode fails if `jsonschema` is unavailable, high-confidence claims lack
support rows, source-backed claims cannot be verified, review artifact hashes
drift, or sample-mode golden eval output is presented as live model evidence.

## Included Commands

- `biomedical-research-council`: broad mechanism, evidence, omics, design, and
  writing coordination.
- `idea-discovery-team`: hypothesis generation, tournament ranking, red-team
  critique, and experimental planning.
- `omics-analysis-team`: public-omics dataset curation, analysis planning or
  execution, review gates, and provenance reporting.
- `evidence-audit-team`: claim-level evidence, citation, provenance,
  statistics, contradiction, and safer wording audit.
- `experiment-design-team`: mechanistic validation, controls, sample-size
  logic, protocol logistics, and decision gates.
- `translational-scout-team`: trial landscape, operational feasibility,
  safety/regulatory flags, IP, and competitive positioning.

## Included Agents

- `life-science-lead-scientist`
- `protocol-context-locker`
- `entity-normalizer`
- `central-claim-ledger-evidence-graph`
- `life-science-literature-curator`
- `scientific-literature-researcher`
- `public-omics-analyst`
- `immunology-mechanism-critic`
- `hypothesis-generator`
- `hypothesis-ranker`
- `meta-review-synthesizer`
- `contradiction-red-team`
- `experimental-design-planner`
- `citation-verifier`
- `scientific-writer-citation-agent`
- `omics-data-curator`
- `omics-code-reviewer`
- `bulk-deg-analyst`
- `scrna-qc-specialist`
- `pathway-interpreter`
- `biostats-repro-auditor`
- `omics-provenance-validator`
- `omics-reporter`
- `scenario-playbook-router`
- `claim-level-evidence-verifier`
- `causal-inference-confounder-analyst`
- `risk-of-bias-study-quality-auditor`
- `safety-ethics-privacy-dual-use-auditor`
- `bayesian-decision-modeler`
- `clinical-trial-operations-scout`
- `grant-ip-landscape-scout`
- `protocol-reagent-logistics-planner`
- `provenance-traceability-architect`
- `figure-schematic-director`
- `model-card-dataset-card-writer`
- `post-write-final-validator`

## Validation

From `skills/biomedical-agent-teams/`:

```bash
python scripts/bmat_package_check.py --root ../..
python scripts/bmat_selftest.py --root ../..
python evals/validate_golden_eval_schema.py --tasks evals/golden_tasks.jsonl --outputs evals/sample_outputs.jsonl
python evals/run_golden_eval.py --tasks evals/golden_tasks.jsonl --outputs evals/sample_outputs.jsonl --strict --gate
python evals/run_model_golden_eval.py --tasks evals/golden_tasks.jsonl --alias evidence-audit-team --runtime codex --model sample-model --out bmat_eval_outputs/model-sample.jsonl --sample-mode --then-score --gate
python scripts/bmat_public_omics_benchmark_smoke.py --out bmat_eval_outputs/public-omics-benchmark --validate --force
uvx --with jsonschema pytest tests -q
```

## Safety Boundaries

- Treat raw data as read-only.
- Do not upload private data, PHI/PII, unpublished project text, or
  patent-sensitive details.
- Do not fabricate PMIDs, DOIs, accessions, reagent details, database records,
  tool use, reviewer use, or validation results.
- Separate evidence, inference, hypothesis, and speculation.
- Keep public-omics proxy evidence separate from CAR-T-intrinsic mechanism
  claims unless the design supports that inference.
