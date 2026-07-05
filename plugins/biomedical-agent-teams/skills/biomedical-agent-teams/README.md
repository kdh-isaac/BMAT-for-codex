# Biomedical Agent Teams

Current version: `1.0.0`.

Codex biomedical agent-team bundle with a lightweight router, protocol and
runtime lock, source corpus, central claim ledger, results integration,
tool-ledger honesty checks, workflow DAGs, loop-state resources, post-write
validation, and deterministic release gates.

Codex uses `SKILL.md` as the router and treats `agents/*.md` as role prompts.
Long governance instructions live in command recipes, references, templates,
contracts, and scripts that are lazy-loaded only when needed.

## 1.0.0 Resource Surface

| Resource | Count |
| --- | ---: |
| Agent role prompts in `agents/` | 36 |
| Workflow recipes in `commands/` | 6 |
| Contract schemas in `contracts/` | 17 |
| Templates in `templates/` | 15 |
| Markdown references in `references/` | 10 |
| JSON references in `references/` | 1 |
| Loop recipes in `loops/` | 4 |
| Codex reviewer TOML templates in `codex-agents/` | 12 |
| Workflow DAGs in `workflows/` | 6 |
| Domain packs in `domain-packs/` | 2 |
| Package scripts in `scripts/` | 9 |
| Eval scripts in `evals/` | 3 |

## 1.0.0 Highlights

- `runtime_capability_preflight.json` is the canonical runtime capability
  preflight artifact.
- `results_integration.json` maps sources, tools, reviewer outputs, omics
  outputs, and literature outputs back to claim rows.
- `tool_call_ledger.json` records successful, skipped, blocked, failed, or
  unavailable tool calls.
- `workflow_dag.json` records alias-specific execution structure; the runner
  normalizes DAG `mode` and `workflow_id` to the requested run mode.
- `bmat_validate.py` enforces bundle shape, source-backed claim references,
  final wording, post-write verdict, independent review evidence, S3/high
  confidence gates, team DAG contracts, tool-ledger policy, and workflow DAG
  alias/mode/id consistency.
- `bmat_run.py` creates local dry-run bundles, writes workflow DAGs, runs
  validator/tool-ledger checks, and can export a Markdown workbench.
- Golden eval gates cover PMID drift, contradiction, overclaim,
  tournament-loop, tournament-ranking, Codex-runtime, semantic-scope, and
  expected-block behavior.
- Runtime documentation keeps only the current release surface; older release
  archaeology belongs in git history.

## Workflow Structure

```mermaid
flowchart TD
    accTitle: BMAT v1.0.0 Workflow Structure
    accDescr: Vertical BMAT workflow spine with optional loop, team DAG, and reviewer lanes feeding back into the central ledger.

    request["User request or BMAT alias"]
    lock["1. Runtime, scope, source, and strategy lock"]
    route{"2. Execution strategy"}
    spine["3. Selected inline specialist work"]
    ledger["4. Central claim ledger<br/>source corpus<br/>workflow-run state"]
    synth["5. Ledger-only synthesis"]
    release{"6. Release gates<br/>post-write + bmat_validate.py"}
    label["7. Final workflow label<br/>Full / Contract / Compact / Limited / Partial / Blocked"]

    request --> lock --> route --> spine --> ledger --> synth --> release --> label

    subgraph team_dag["Optional lane: team_level_selective_dag"]
        direction TB
        t1["Phase 1 teams<br/>idea / omics / translational"]
        t2["Phase 2 teams<br/>experiment design / evidence audit"]
        tout["team_output_artifacts<br/>artifact path + checks + dependencies"]
        tgate{"team_spawn_outputs<br/>stage pass?"}
        t1 --> t2 --> tout --> tgate
    end

    subgraph review_lane["Optional lane: selective spawned review"]
        direction TB
        registry["agent-registry.json<br/>codex-agents/*.toml"]
        instances["spawned_agent_instances"]
        rcontract["spawned-agent-output contract"]
        rhandoff["accepted findings<br/>ledger handoff"]
        registry --> instances --> rcontract --> rhandoff
    end

    subgraph loop_layer["Optional lane: recurring loop layer"]
        direction TB
        loop_recipe["loops/*.md recipe"]
        loop_state["loop_state.json"]
        loop_check["bmat_loop_check.py"]
        loop_recipe --> loop_state --> loop_check
    end

    route -. "broad independent axes" .-> t1
    tgate --> ledger
    ledger -. "independent audit needed" .-> registry
    rhandoff --> ledger
    route -. "watch / inbox / triage" .-> loop_recipe
    loop_check --> ledger
    loop_check --> release
```

The main workflow progresses vertically from request lock to final label. The
lead owns the lock, selected inline work, claim ledger, workflow-run state, and
final synthesis. Optional lanes run only when the strategy calls for them, then
feed evidence back into the ledger: team DAG outputs are proven by
`team_output_artifacts`, reviewer execution is proven by
`spawned_agent_instances`, and recurring loops are checked by
`bmat_loop_check.py`.

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
- `source_corpus.json`
- `claim_ledger.json`
- `stage_evaluation.json`
- `post_write_validation.json`
- `final.md`

Optional but policy-checked artifacts:

- `workflow_dag.json`
- `results_integration.json`
- `tool_call_ledger.json`

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
