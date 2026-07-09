# Experiment Design Template

Use `experiment_design.json` for experiment-design release gates.

```json
{
  "design_id": "exp-<workflow_run_id>",
  "workflow_run_id": "<workflow_run_id>",
  "plugin_version": "1.1.0",
  "hypothesis": "State the bounded hypothesis.",
  "experimental_objective": "State the objective and intended decision.",
  "experimental_unit": {
    "unit_type": "donor",
    "justification": "The donor is the biological replicate."
  },
  "primary_endpoint": "Primary endpoint",
  "secondary_endpoints": [],
  "positive_controls": ["Positive control"],
  "negative_controls": ["Negative control"],
  "vehicle_or_mock_controls": ["Vehicle/mock control"],
  "biological_replicates": {
    "planned_n": 3,
    "rationale": "State effect-size or feasibility rationale."
  },
  "technical_replicates": {
    "planned_n": 2,
    "rationale": "State technical precision rationale."
  },
  "randomization": {
    "planned": true,
    "method_or_reason": "Describe randomization."
  },
  "blinding": {
    "planned": false,
    "method_or_reason": "Explain if not feasible."
  },
  "exclusion_criteria": [],
  "confounders": [],
  "causal_kill_tests": [],
  "statistical_plan": {
    "model": "linear mixed model",
    "multiplicity": "BH-FDR",
    "effect_size_or_decision_threshold": "Define threshold."
  },
  "go_no_go_gates": [],
  "safety_ethics_privacy_boundary": "Record public/private, animal/human, IRB/DUA, and disclosure boundaries.",
  "reagent_provenance_policy": "Verify catalog/protocol identifiers or mark unknown.",
  "source_ids": [],
  "claim_ids_supported": []
}
```
