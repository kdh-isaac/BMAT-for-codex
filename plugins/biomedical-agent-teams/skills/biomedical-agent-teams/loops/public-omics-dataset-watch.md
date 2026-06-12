# Public Omics Dataset Watch Loop

Use for recurring surveillance of public omics repositories for datasets that
may support a BMAT question. This is a feasibility and provenance loop, not a
full analysis run.

| field | value |
|---|---|
| loop_type | public_omics_dataset_watch |
| default_trigger | scheduled repository refresh or user-requested dataset search |
| input_scope | organism, assay, disease/model, biological unit, contrast or endpoint, public repository scope |
| state_file | loop_state.json using `contracts/loop-state.schema.json` |
| source_delta | new or changed GEO/SRA/ArrayExpress/CELLxGENE/TCGA/HPA records |
| allowed_connectors | GEO/SRA/NCBI Datasets, ArrayExpress/BioStudies, CELLxGENE, TCGA/GDC, HPA when available |
| reviewer_lane | `omics-provenance-validator`, optional `biostats-repro-auditor` |
| output_artifacts | dataset delta, feasibility table, S1-S3 risk note, claim ledger handoff candidates |
| stop_condition | no eligible public dataset, metadata insufficient, S1-S3 feasibility classified, or human gate blocks next step |

## Loop Steps

1. Load previous loop state and dataset/source corpus locks.
2. Normalize accessions, organisms, assay platforms, genome build or annotation
   needs, biological units, and endpoint terminology.
3. Search only approved public repositories and record retrieval dates.
4. Classify each dataset by access, sample metadata completeness, biological
   unit clarity, contrast/endpoint feasibility, and privacy/controlled-access risk.
5. Do not run full analysis inside this loop. Escalate to `omics-analysis-team
   --mode plan` or `--mode run` only after S1 Plan and S2/S3 feasibility are
   explicit.
6. Add unresolved metadata or design problems as open loop items.
7. Run `scripts/bmat_loop_check.py` before marking the loop stopped or complete.

## Release Rule

Release a feasibility delta only. Any expression, survival, pathway, or causal
claim requires the normal omics S1-S5 workflow and claim-ledger validation.
