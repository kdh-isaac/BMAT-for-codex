from __future__ import annotations

import importlib.util
import json
import sys
from copy import deepcopy
from pathlib import Path

import pytest


SKILL_ROOT = Path(__file__).resolve().parents[1]
CHECKER = SKILL_ROOT / "scripts" / "bmat_tournament_check.py"
SCHEMA = SKILL_ROOT / "contracts" / "hypothesis-tournament.schema.json"

SPEC = importlib.util.spec_from_file_location("bmat_tournament_check_test_module", CHECKER)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def valid_tournament() -> dict:
    scores = []
    for judge_index, judge_id in enumerate(("judge-a", "judge-b"), start=1):
        for candidate_index, candidate_id in enumerate(("blind-17", "blind-42"), start=1):
            scores.append(
                {
                    "judgment_id": f"judgment-{judge_index}-{candidate_index}",
                    "judge_id": judge_id,
                    "independence_class": "same-model-separate-context",
                    "blinded_candidate_id": candidate_id,
                    "presentation_order": candidate_index,
                    "novelty": 0.7,
                    "evidence_strength": 0.75 if candidate_id == "blind-17" else 0.55,
                    "mechanistic_specificity": 0.7,
                    "assayability": 0.8,
                    "feasibility": 0.7,
                    "safety": 0.9,
                    "expected_information_gain": 0.8,
                    "execution_priority": 0.8 if candidate_id == "blind-17" else 0.6,
                    "rationale": "Bounded multi-axis synthetic judgment.",
                }
            )
    return {
        "schema_version": "2.0",
        "tournament_id": "tournament-test-v2",
        "plugin_version": "1.2.0",
        "workflow_run_id": "run-test-v2",
        "created_at": "2026-07-10T00:00:00Z",
        "selected_domain_pack": "generic-biomedical",
        "context_lock": "Domain-neutral synthetic comparison.",
        "candidate_order_randomization": {
            "method": "seeded shuffle",
            "seed": 17,
            "randomized_order": ["blind-42", "blind-17"],
        },
        "judge_scores": scores,
        "aggregate_scores": [
            {"blinded_candidate_id": "blind-17", "aggregate_score": 0.78, "evidence_strength": 0.75, "execution_priority": 0.8},
            {"blinded_candidate_id": "blind-42", "aggregate_score": 0.58, "evidence_strength": 0.55, "execution_priority": 0.6},
        ],
        "judge_disagreement": [
            {"blinded_candidate_id": "blind-17", "method": "range", "evidence_strength_dispersion": 0.0, "execution_priority_dispersion": 0.0},
            {"blinded_candidate_id": "blind-42", "method": "range", "evidence_strength_dispersion": 0.0, "execution_priority_dispersion": 0.0},
        ],
        "order_sensitivity_check": {
            "performed": True,
            "alternate_seed": 42,
            "rank_stability": 1.0,
            "limitations": "Two seeded orders cannot exclude all order effects.",
        },
        "ranking_uncertainty": {
            "method": "qualitative",
            "resamples": None,
            "summary": "Both seeded orders retained the qualitative order.",
            "limitations": "Synthetic two-candidate comparison.",
        },
        "same_model_correlated_judgment_limitation": "Same-model judgments remain correlated and this limits independence.",
        "winner_interpretation_boundary": "Priority rank is not biological validation or proof.",
        "iteration_budget": 2,
        "compute_budget_status": "within-budget",
        "candidates": [
            {"hypothesis_id": "H-001", "blinded_candidate_id": "blind-17", "hypothesis": "Synthetic hypothesis one.", "status": "winner"},
            {"hypothesis_id": "H-002", "blinded_candidate_id": "blind-42", "hypothesis": "Synthetic hypothesis two.", "status": "active"},
        ],
        "rounds": [{"round_id": "round-1", "round_type": "pairwise-debate", "output_summary": "Blinded multi-axis comparison."}],
        "ranking_model": "elo",
        "qualitative_ranking": ["H-001", "H-002"],
        "model_based_ranking": ["H-001", "H-002"],
        "final_ranking": [
            {
                "rank": 1,
                "hypothesis_id": "H-001",
                "verdict": "advance",
                "rationale": "Evidence, feasibility, assayability, safety, and information gain jointly support priority.",
                "rating": 1016.0,
                "rating_interpretation": "Pairwise preference rating, not evidence strength.",
                "evidence_strength": "high",
                "execution_priority": "high",
                "expected_information_gain": "high",
            },
            {
                "rank": 2,
                "hypothesis_id": "H-002",
                "verdict": "hold",
                "rationale": "Lower evidence and execution priority.",
                "rating": 984.0,
                "rating_interpretation": "Pairwise preference rating only.",
                "evidence_strength": "moderate",
                "execution_priority": "moderate",
                "expected_information_gain": "moderate",
            },
        ],
    }


def codes(payload: dict, run_state: dict | None = None) -> set[str]:
    return {finding.code for finding in MODULE.check(payload, run_state)}


def test_v2_tournament_schema_and_checker_accept_separate_axes() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    payload = valid_tournament()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(payload)
    assert codes(payload) == set()


def test_checker_rejects_incomplete_or_duplicate_judge_matrix() -> None:
    payload = valid_tournament()
    payload["judge_scores"].pop()
    payload["judge_scores"].append(deepcopy(payload["judge_scores"][0]))
    found = codes(payload)
    assert "TOURNAMENT_DUPLICATE_JUDGE_SCORE" in found
    assert "TOURNAMENT_JUDGE_SCORE_MATRIX_INCOMPLETE" in found


def test_checker_rejects_novelty_only_and_unsupported_high_strength() -> None:
    payload = valid_tournament()
    payload["final_ranking"][0]["rationale"] = "Most novel candidate."
    for score in payload["judge_scores"]:
        if score["blinded_candidate_id"] == "blind-17":
            score["evidence_strength"] = 0.2
    found = codes(payload)
    assert "TOURNAMENT_NOVELTY_ONLY_WINNER" in found
    assert "TOURNAMENT_UNSUPPORTED_HIGH_EVIDENCE_STRENGTH" in found


def test_checker_rejects_rating_as_evidence_strength_and_weak_correlation_limit() -> None:
    payload = valid_tournament()
    payload["final_ranking"][0]["rating_interpretation"] = "Elo evidence strength."
    payload["same_model_correlated_judgment_limitation"] = "not applicable"
    found = codes(payload)
    assert "TOURNAMENT_RATING_AS_EVIDENCE_STRENGTH" in found
    assert "TOURNAMENT_SAME_MODEL_CORRELATION_LIMIT_MISSING" in found


def test_checker_cross_checks_domain_pack_and_run_identity() -> None:
    payload = valid_tournament()
    run_state = {"run_id": "run-test-v2", "selected_domain_pack": "cell-therapy"}
    assert "TOURNAMENT_DOMAIN_PACK_MISMATCH" in codes(payload, run_state)
    run_state["run_id"] = "stale-run"
    assert "TOURNAMENT_WORKFLOW_RUN_ID_MISMATCH" in codes(payload, run_state)
