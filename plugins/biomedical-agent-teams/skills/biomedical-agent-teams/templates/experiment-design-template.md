# Experiment Design v2 Template

Use this domain-neutral shape for `experiment_design.json`. The numerical values
below are illustrative only; replace them with design-specific assumptions and
do not treat the example as scientific support. Release validation rejects v1,
placeholders, unsafe operational detail, and stale or mismatched artifact hashes.

```json
{
  "schema_version": "2.0",
  "design_id": "exp-run-example-001",
  "plugin_version": "1.2.0",
  "workflow_run_id": "run-example-001",
  "created_at": "2026-07-10T00:00:00Z",
  "design_stage": "exploratory",
  "recommendation_confidence": "moderate",
  "decision_authority": "research-assistance-only",
  "hypothesis": "A bounded, testable hypothesis stated without a specialty assumption.",
  "experimental_objective": "Estimate the prespecified effect and decide whether confirmatory work is justified.",
  "primary_estimand": {
    "population_or_model": "The prespecified study population or model",
    "treatment_or_exposure": "The prespecified intervention or exposure",
    "comparator": "The prespecified control condition",
    "outcome": "Primary endpoint at the prespecified time",
    "summary_measure": "Difference in group means"
  },
  "primary_endpoint": {
    "endpoint_id": "EP-PRIMARY",
    "name": "Primary quantitative endpoint",
    "measurement_scale": "continuous",
    "measurement_unit": "prespecified assay unit",
    "assessment_timepoint": "prespecified endpoint time",
    "direction_of_benefit": "higher"
  },
  "secondary_endpoints": [],
  "expected_effect_size": {
    "measure": "standardized mean difference",
    "value": 0.5,
    "unit": "standard-deviation units",
    "direction": "increase",
    "assumption_basis": "domain-conservative",
    "rationale": "Illustrative conservative assumption; replace with source- or pilot-grounded rationale.",
    "source_ids": []
  },
  "variance_or_event_rate_assumption": {
    "assumption_type": "standard-deviation",
    "value": 1.0,
    "unit": "standard-deviation units",
    "assumption_basis": "domain-conservative",
    "rationale": "Standardized illustrative scale; replace before release if the endpoint is not standardized.",
    "source_ids": []
  },
  "alpha": 0.05,
  "power": 0.8,
  "sidedness": "two-sided",
  "planned_n": 40,
  "dropout_or_failure_allowance": 0.1,
  "positive_controls": ["Prespecified positive control"],
  "negative_controls": ["Prespecified negative control"],
  "vehicle_or_mock_controls": ["Prespecified vehicle, mock, or sham control"],
  "biological_replicates": {
    "planned_n": 40,
    "allocation": "20 intervention and 20 comparator biological units",
    "rationale": "Must match the top-level total planned_n and sample-size calculation."
  },
  "technical_replicates": {
    "planned_n": 0,
    "rationale": "No technical replication in this illustrative conceptual design."
  },
  "randomization_unit": "independent biological unit",
  "analysis_unit": "independent biological unit",
  "biological_unit": "independent biological unit",
  "unit_mismatch_handling": null,
  "randomization_plan": {
    "planned": true,
    "method_or_reason": "Computer-generated allocation with a retained seed and allocation receipt.",
    "allocation_concealment_or_reason": "Allocation remains concealed until assignment."
  },
  "blocking_factors": [],
  "blinding_plan": {
    "planned": true,
    "masked_roles": ["outcome assessor", "analyst"],
    "method_or_reason": "Use coded groups until the primary analysis is locked."
  },
  "exclusion_criteria": ["Prespecified technical failure criterion applied without group-label access"],
  "confounders": ["Batch or site effects if more than one batch or site is used"],
  "causal_kill_tests": ["A prespecified result that would falsify the proposed mechanism"],
  "statistical_plan": {
    "model": "Prespecified model appropriate to the endpoint distribution",
    "covariates": [],
    "clustering_or_repeated_measures": "Not applicable when one independent endpoint is analyzed per biological unit.",
    "effect_size_reporting": "Estimate with a two-sided 95% confidence interval."
  },
  "multiplicity_plan": {
    "method": "none-prespecified",
    "family_definition": "One primary endpoint; secondary endpoints are explicitly exploratory.",
    "alpha_allocation": "All two-sided alpha 0.05 is assigned to the primary endpoint.",
    "rationale": "No multiplicity adjustment is claimed for exploratory secondary endpoints."
  },
  "interim_analysis": {
    "planned": false,
    "timing_or_reason": "No interim analysis in the fixed-sample illustrative design.",
    "alpha_spending_or_reason": "Not applicable because no interim hypothesis test is planned."
  },
  "stopping_rule": {
    "rule_type": "fixed-sample",
    "criteria": "Analyze after all planned evaluable biological units reach the endpoint or an authorized safety stop occurs.",
    "decision_authority": "The responsible investigator and applicable oversight body, not BMAT."
  },
  "sensitivity_analyses": [],
  "sample_size_method": "Two-group standardized-effect calculation using the stated alpha, power, effect size, and dropout allowance.",
  "sample_size_artifact_status": "not-produced",
  "sample_size_code_ref": null,
  "sample_size_output_ref": null,
  "sample_size_output_sha256": null,
  "go_no_go_gates": ["Advance only if the prespecified effect and feasibility boundaries are met."],
  "design_scope": "conceptual",
  "safety_ethics_privacy_boundary": {
    "operational_details_included": false,
    "risk_triggers": ["none"],
    "required_oversight": ["not-applicable for this conceptual example; reassess before execution"],
    "privacy_boundary": "No private or participant-level information is included.",
    "dual_use_boundary": "No operational dual-use detail is included.",
    "patent_sensitive_boundary": "No confidential or patent-sensitive detail is included.",
    "limitations": "This artifact is research planning support and is not authorization to start an experiment.",
    "bmat_role": "research-assistance-only"
  },
  "reagent_provenance_policy": "Mark every reagent/catalog statement verified through an eligible source row or unknown with limitations.",
  "reagent_specific_claims": [],
  "source_ids": [],
  "claim_ids_supported": [],
  "limitations": ["Illustrative values require study-specific replacement and scientific review."]
}
```

When a sample-size script or output exists, set
`sample_size_artifact_status` to `produced`, use bundle-relative paths, and set
`sample_size_output_sha256` to the hash recomputed from the exact output file.

When randomization, analysis, and biological units differ, replace `null` with:

```json
{
  "justification": "Why the declared units differ.",
  "analysis_adjustment": "How clustering, repeated measures, or pseudoreplication is handled.",
  "effective_sample_size_considered": true
}
```

Reagent-specific statements use structured entries:

```json
{
  "reagent_claim_id": "RG-001",
  "statement": "Bounded manufacturer or catalog-specific statement.",
  "manufacturer": "Recorded manufacturer",
  "catalog_identifier": "Recorded catalog identifier",
  "verification_status": "unknown",
  "source_ids": [],
  "limitations": "Not verified; do not use as a high-confidence design premise."
}
```

BMAT validates the process contract and artifact integrity. It does not certify
scientific truth or replace human scientific, institutional, or clinical review.
