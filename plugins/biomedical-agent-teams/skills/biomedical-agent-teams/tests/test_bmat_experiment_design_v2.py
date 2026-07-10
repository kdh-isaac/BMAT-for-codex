from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import subprocess
import sys
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from pathlib import Path

import pytest


SKILL_ROOT = Path(__file__).resolve().parents[1]
CHECKER = SKILL_ROOT / "scripts" / "bmat_experiment_design_check.py"
SCHEMA = SKILL_ROOT / "contracts" / "experiment-design.schema.json"


CHECKER_SPEC = importlib.util.spec_from_file_location(
    "bmat_experiment_design_check_v2_test_module", CHECKER
)
assert CHECKER_SPEC is not None and CHECKER_SPEC.loader is not None
CHECKER_MODULE = importlib.util.module_from_spec(CHECKER_SPEC)
sys.modules[CHECKER_SPEC.name] = CHECKER_MODULE
CHECKER_SPEC.loader.exec_module(CHECKER_MODULE)


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def valid_design() -> dict:
    return {
        "schema_version": "2.0",
        "design_id": "exp-test-v2",
        "plugin_version": "1.2.0",
        "workflow_run_id": "run-test-v2",
        "created_at": "2026-07-10T00:00:00Z",
        "design_stage": "exploratory",
        "recommendation_confidence": "moderate",
        "decision_authority": "research-assistance-only",
        "hypothesis": "A bounded synthetic hypothesis.",
        "experimental_objective": "Estimate a prespecified synthetic effect.",
        "primary_estimand": {
            "population_or_model": "synthetic model",
            "treatment_or_exposure": "synthetic intervention",
            "comparator": "synthetic comparator",
            "outcome": "synthetic endpoint",
            "summary_measure": "difference in means",
        },
        "primary_endpoint": {
            "endpoint_id": "EP-1",
            "name": "synthetic endpoint",
            "measurement_scale": "continuous",
            "measurement_unit": "arbitrary unit",
            "assessment_timepoint": "day 7",
            "direction_of_benefit": "higher",
        },
        "secondary_endpoints": [],
        "expected_effect_size": {
            "measure": "standardized mean difference",
            "value": 0.5,
            "unit": "standard-deviation units",
            "direction": "increase",
            "assumption_basis": "simulation",
            "rationale": "Synthetic test assumption.",
            "source_ids": [],
        },
        "variance_or_event_rate_assumption": {
            "assumption_type": "standard-deviation",
            "value": 1.0,
            "unit": "standard-deviation units",
            "assumption_basis": "simulation",
            "rationale": "Synthetic test assumption.",
            "source_ids": [],
        },
        "alpha": 0.05,
        "power": 0.8,
        "sidedness": "two-sided",
        "planned_n": 40,
        "dropout_or_failure_allowance": 0.1,
        "positive_controls": ["positive control"],
        "negative_controls": ["negative control"],
        "vehicle_or_mock_controls": ["mock control"],
        "biological_replicates": {
            "planned_n": 40,
            "allocation": "20 per group",
            "rationale": "Matches the sample-size assumptions.",
        },
        "technical_replicates": {
            "planned_n": 0,
            "rationale": "Not needed for the synthetic test.",
        },
        "randomization_unit": "biological unit",
        "analysis_unit": "biological unit",
        "biological_unit": "biological unit",
        "unit_mismatch_handling": None,
        "randomization_plan": {
            "planned": True,
            "method_or_reason": "Seeded computer allocation.",
            "allocation_concealment_or_reason": "Concealed until assignment.",
        },
        "blocking_factors": [],
        "blinding_plan": {
            "planned": True,
            "masked_roles": ["analyst"],
            "method_or_reason": "Coded groups.",
        },
        "exclusion_criteria": ["Prespecified technical failure"],
        "confounders": ["batch"],
        "causal_kill_tests": ["Prespecified null-pattern kill test"],
        "statistical_plan": {
            "model": "linear model",
            "covariates": ["batch"],
            "clustering_or_repeated_measures": "Not applicable.",
            "effect_size_reporting": "Estimate and 95% CI.",
        },
        "multiplicity_plan": {
            "method": "none-prespecified",
            "family_definition": "One primary endpoint.",
            "alpha_allocation": "All alpha assigned to the primary endpoint.",
            "rationale": "Secondary endpoints are exploratory.",
        },
        "interim_analysis": {
            "planned": False,
            "timing_or_reason": "No interim analysis.",
            "alpha_spending_or_reason": "Not applicable.",
        },
        "stopping_rule": {
            "rule_type": "fixed-sample",
            "criteria": "Analyze after the fixed sample is complete.",
            "decision_authority": "Responsible investigator.",
        },
        "sensitivity_analyses": [],
        "sample_size_method": "Synthetic two-group calculation.",
        "sample_size_artifact_status": "not-produced",
        "sample_size_code_ref": None,
        "sample_size_output_ref": None,
        "sample_size_output_sha256": None,
        "go_no_go_gates": ["Prespecified feasibility gate"],
        "design_scope": "conceptual",
        "safety_ethics_privacy_boundary": {
            "operational_details_included": False,
            "risk_triggers": ["none"],
            "required_oversight": ["reassess before execution"],
            "privacy_boundary": "No private data.",
            "dual_use_boundary": "No operational dual-use detail.",
            "patent_sensitive_boundary": "No confidential detail.",
            "limitations": "Research planning only.",
            "bmat_role": "research-assistance-only",
        },
        "reagent_provenance_policy": "Verify or mark unknown.",
        "reagent_specific_claims": [],
        "source_ids": [],
        "claim_ids_supported": [],
        "limitations": ["Synthetic fixture."],
    }


def run_checker(
    tmp_path: Path,
    design: dict,
    *,
    release: bool = True,
    source_verification: dict | None = None,
) -> tuple[subprocess.CompletedProcess[str], dict]:
    design_path = tmp_path / "experiment_design.json"
    out_path = tmp_path / "experiment_design_check.json"
    write_json(design_path, design)
    command = [
        sys.executable,
        str(CHECKER),
        "--experiment-design",
        str(design_path),
        "--bundle-root",
        str(tmp_path),
        "--out",
        str(out_path),
        "--json",
    ]
    if release:
        command.append("--release")
    if source_verification is not None:
        source_path = tmp_path / "source_verification.json"
        write_json(source_path, source_verification)
        command.extend(["--source-verification", str(source_path)])
    stdout = io.StringIO()
    stderr = io.StringIO()
    previous_argv = sys.argv
    try:
        sys.argv = [str(CHECKER), *command[2:]]
        with redirect_stdout(stdout), redirect_stderr(stderr):
            returncode = CHECKER_MODULE.main()
    finally:
        sys.argv = previous_argv
    result = subprocess.CompletedProcess(
        command,
        returncode,
        stdout=stdout.getvalue(),
        stderr=stderr.getvalue(),
    )
    return result, json.loads(out_path.read_text(encoding="utf-8"))


def finding_codes(payload: dict) -> set[str]:
    return {finding["code"] for finding in payload["findings"]}


def test_v2_schema_is_draft_2020_12_and_accepts_valid_design() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.FormatChecker()
    ).validate(valid_design())


def test_release_valid_v2_design_passes_and_hashes_checked_artifact(tmp_path: Path) -> None:
    result, payload = run_checker(tmp_path, valid_design())

    assert result.returncode == 0, result.stdout + result.stderr
    assert payload["status"] == "pass"
    assert payload["schema_version"] == "2.0"
    assert payload["design_artifact_sha256"] == hashlib.sha256(
        (tmp_path / "experiment_design.json").read_bytes()
    ).hexdigest()


def test_release_rejects_planned_n_placeholder(tmp_path: Path) -> None:
    design = valid_design()
    design["planned_n"] = "TBD"
    design["biological_replicates"]["planned_n"] = "TBD"

    result, payload = run_checker(tmp_path, design)

    assert result.returncode == 1
    assert "EXPERIMENT_DESIGN_PLANNED_N_PLACEHOLDER" in finding_codes(payload)
    finding = next(
        item
        for item in payload["findings"]
        if item["code"] == "EXPERIMENT_DESIGN_PLANNED_N_PLACEHOLDER"
    )
    assert finding["level"] == "ERROR"
    assert finding["path"] == "$.planned_n"
    assert finding["fix_hint"]


def test_high_confidence_requires_quantitative_assumptions(tmp_path: Path) -> None:
    design = valid_design()
    design["recommendation_confidence"] = "high"
    design["expected_effect_size"].pop("value")

    result, payload = run_checker(tmp_path, design)

    assert result.returncode == 1
    assert (
        "EXPERIMENT_DESIGN_HIGH_CONFIDENCE_WITHOUT_QUANTITATIVE_ASSUMPTIONS"
        in finding_codes(payload)
    )


def test_release_rejects_model_without_multiplicity_plan(tmp_path: Path) -> None:
    design = valid_design()
    design["multiplicity_plan"] = {}

    result, payload = run_checker(tmp_path, design)

    assert result.returncode == 1
    assert "EXPERIMENT_DESIGN_MULTIPLICITY_PLAN_MISSING" in finding_codes(payload)


def test_release_rejects_unexplained_unit_mismatch(tmp_path: Path) -> None:
    design = valid_design()
    design["randomization_unit"] = "cluster"
    design["analysis_unit"] = "individual"
    design["unit_mismatch_handling"] = None

    result, payload = run_checker(tmp_path, design)

    assert result.returncode == 1
    assert "EXPERIMENT_DESIGN_UNIT_MISMATCH_UNEXPLAINED" in finding_codes(payload)


def test_release_accepts_explained_unit_mismatch(tmp_path: Path) -> None:
    design = valid_design()
    design["randomization_unit"] = "cluster"
    design["analysis_unit"] = "individual"
    design["biological_unit"] = "individual"
    design["unit_mismatch_handling"] = {
        "justification": "Allocation occurs by cluster while outcomes occur by individual.",
        "analysis_adjustment": "Cluster-robust variance with cluster-level degrees of freedom.",
        "effective_sample_size_considered": True,
    }

    result, payload = run_checker(tmp_path, design)

    assert result.returncode == 0, result.stdout + result.stderr
    assert payload["status"] == "pass"


def test_release_rejects_operational_design_without_safety_boundary(tmp_path: Path) -> None:
    design = valid_design()
    design["design_scope"] = "animal"
    design["safety_ethics_privacy_boundary"]["operational_details_included"] = True
    design["safety_ethics_privacy_boundary"]["risk_triggers"] = ["none"]

    result, payload = run_checker(tmp_path, design)

    assert result.returncode == 1
    assert (
        "EXPERIMENT_DESIGN_OPERATIONAL_SAFETY_BOUNDARY_INCOMPLETE"
        in finding_codes(payload)
    )


def test_reagent_claim_must_be_verified_or_explicitly_unknown(tmp_path: Path) -> None:
    design = valid_design()
    design["reagent_specific_claims"] = [
        {
            "reagent_claim_id": "RG-1",
            "statement": "Synthetic catalog-specific statement.",
            "verification_status": "unknown",
            "source_ids": [],
            "limitations": "",
        }
    ]

    result, payload = run_checker(tmp_path, design)

    assert result.returncode == 1
    assert (
        "EXPERIMENT_DESIGN_REAGENT_UNKNOWN_WITHOUT_LIMITATION"
        in finding_codes(payload)
    )


def test_verified_reagent_requires_release_eligible_non_fixture_source(tmp_path: Path) -> None:
    design = valid_design()
    design["source_ids"] = ["SRC-1"]
    design["reagent_specific_claims"] = [
        {
            "reagent_claim_id": "RG-1",
            "statement": "Synthetic catalog-specific statement.",
            "verification_status": "verified",
            "source_ids": ["SRC-1"],
            "limitations": "",
        }
    ]
    fixture_verification = {
        "rows": [
            {
                "source_id": "SRC-1",
                "identifier_status": "not-checked",
                "release_eligible": False,
                "fixture_only": True,
                "verification_mode": "fixture",
                "integrity_status": "unknown",
            }
        ]
    }

    result, payload = run_checker(
        tmp_path, design, source_verification=fixture_verification
    )

    assert result.returncode == 1
    assert "EXPERIMENT_DESIGN_REAGENT_SOURCE_NOT_ELIGIBLE" in finding_codes(payload)


def test_sample_size_output_hash_is_recomputed(tmp_path: Path) -> None:
    design = valid_design()
    output = tmp_path / "sample_size_output.json"
    output.write_text('{"planned_n": 40}\n', encoding="utf-8")
    design["sample_size_artifact_status"] = "produced"
    design["sample_size_output_ref"] = output.name
    design["sample_size_output_sha256"] = hashlib.sha256(output.read_bytes()).hexdigest()

    passing, passing_payload = run_checker(tmp_path, deepcopy(design))
    assert passing.returncode == 0, passing.stdout + passing.stderr
    assert passing_payload["status"] == "pass"

    design["sample_size_output_sha256"] = "0" * 64
    failing, failing_payload = run_checker(tmp_path, design)
    assert failing.returncode == 1
    assert "EXPERIMENT_DESIGN_SAMPLE_SIZE_HASH_MISMATCH" in finding_codes(
        failing_payload
    )


def test_sample_size_artifact_path_cannot_escape_bundle(tmp_path: Path) -> None:
    design = valid_design()
    design["sample_size_artifact_status"] = "produced"
    design["sample_size_output_ref"] = "../outside.json"
    design["sample_size_output_sha256"] = "0" * 64

    result, payload = run_checker(tmp_path, design)

    assert result.returncode == 1
    assert "EXPERIMENT_DESIGN_SAMPLE_SIZE_PATH_INVALID" in finding_codes(payload)


def test_legacy_design_warns_non_release_and_blocks_release(tmp_path: Path) -> None:
    legacy = {
        "design_id": "legacy",
        "workflow_run_id": "legacy-run",
        "positive_controls": ["positive"],
        "negative_controls": ["negative"],
        "vehicle_or_mock_controls": ["mock"],
        "biological_replicates": {"planned_n": 3, "rationale": "legacy"},
        "statistical_plan": {
            "model": "legacy model",
            "multiplicity": "legacy adjustment",
            "effect_size_or_decision_threshold": "legacy threshold",
        },
        "safety_ethics_privacy_boundary": "legacy boundary",
    }

    non_release, warning_payload = run_checker(
        tmp_path, legacy, release=False
    )
    assert non_release.returncode == 0
    assert "LEGACY_SCHEMA_V1_NOT_RELEASE_ELIGIBLE" in finding_codes(warning_payload)

    release, release_payload = run_checker(tmp_path, legacy, release=True)
    assert release.returncode == 1
    assert "EXPERIMENT_DESIGN_SCHEMA_VERSION_UNSUPPORTED" in finding_codes(
        release_payload
    )
