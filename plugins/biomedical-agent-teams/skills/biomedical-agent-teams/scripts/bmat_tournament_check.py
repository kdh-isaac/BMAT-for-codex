#!/usr/bin/env python3
"""Deterministically check BMAT hypothesis-tournament process integrity."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Finding:
    level: str
    code: str
    message: str
    path: str = "hypothesis_tournament.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check BMAT hypothesis tournament artifact consistency.")
    parser.add_argument("--tournament", type=Path, required=True)
    parser.add_argument("--run-state", type=Path, help="Optional run_state.json for domain-pack/run identity cross-checks.")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise SystemExit("tournament artifact must be a JSON object")
    return payload


def check(payload: dict[str, Any], run_state: dict[str, Any] | None = None) -> list[Finding]:
    findings: list[Finding] = []
    candidates = [row for row in payload.get("candidates", []) if isinstance(row, dict)]
    hypothesis_ids = [str(row.get("hypothesis_id", "")).strip() for row in candidates]
    blinded_ids = [str(row.get("blinded_candidate_id", "")).strip() for row in candidates]
    if len(set(hypothesis_ids)) != len(hypothesis_ids):
        findings.append(Finding("ERROR", "TOURNAMENT_DUPLICATE_HYPOTHESIS_ID", "hypothesis IDs must be unique"))
    if not blinded_ids or any(not value for value in blinded_ids) or len(set(blinded_ids)) != len(blinded_ids):
        findings.append(Finding("ERROR", "TOURNAMENT_BLINDED_IDS_INVALID", "blinded candidate IDs must be present and unique"))
    if set(hypothesis_ids) & set(blinded_ids):
        findings.append(Finding("ERROR", "TOURNAMENT_BLINDING_LEAK", "blinded IDs must not expose hypothesis IDs"))
    order = payload.get("candidate_order_randomization", {}).get("randomized_order", [])
    if not isinstance(order, list) or set(map(str, order)) != set(blinded_ids):
        findings.append(Finding("ERROR", "TOURNAMENT_RANDOMIZED_ORDER_INCOMPLETE", "randomized order must contain every blinded candidate exactly once"))
    judge_scores = [row for row in payload.get("judge_scores", []) if isinstance(row, dict)]
    score_ids = {str(row.get("blinded_candidate_id", "")) for row in judge_scores}
    if set(blinded_ids) - score_ids:
        findings.append(Finding("ERROR", "TOURNAMENT_CANDIDATE_MISSING_JUDGE_SCORE", "every candidate requires preserved judge-level scores"))
    seen_judgments: set[tuple[str, str]] = set()
    candidates_by_judge: dict[str, set[str]] = {}
    for row in judge_scores:
        judge_id = str(row.get("judge_id", "")).strip()
        blinded_id = str(row.get("blinded_candidate_id", "")).strip()
        pair = (judge_id, blinded_id)
        if pair in seen_judgments:
            findings.append(Finding("ERROR", "TOURNAMENT_DUPLICATE_JUDGE_SCORE", f"duplicate score for judge {judge_id} and candidate {blinded_id}"))
        seen_judgments.add(pair)
        candidates_by_judge.setdefault(judge_id, set()).add(blinded_id)
    expected_blinded_ids = set(blinded_ids)
    for judge_id, scored_ids in candidates_by_judge.items():
        if scored_ids != expected_blinded_ids:
            findings.append(Finding("ERROR", "TOURNAMENT_JUDGE_SCORE_MATRIX_INCOMPLETE", f"judge {judge_id} did not score every blinded candidate exactly once"))
    aggregate_ids = [str(row.get("blinded_candidate_id", "")) for row in payload.get("aggregate_scores", []) if isinstance(row, dict)]
    disagreement_ids = [str(row.get("blinded_candidate_id", "")) for row in payload.get("judge_disagreement", []) if isinstance(row, dict)]
    if set(aggregate_ids) != expected_blinded_ids or len(aggregate_ids) != len(set(aggregate_ids)):
        findings.append(Finding("ERROR", "TOURNAMENT_AGGREGATE_SCORE_COVERAGE_INVALID", "aggregate scores must cover each blinded candidate exactly once"))
    if set(disagreement_ids) != expected_blinded_ids or len(disagreement_ids) != len(set(disagreement_ids)):
        findings.append(Finding("ERROR", "TOURNAMENT_DISAGREEMENT_COVERAGE_INVALID", "judge disagreement must cover each blinded candidate exactly once"))
    if payload.get("aggregate_scores") == payload.get("judge_disagreement"):
        findings.append(Finding("ERROR", "TOURNAMENT_AGGREGATE_DISAGREEMENT_CONFLATED", "aggregate scores and judge disagreement must be distinct outputs"))
    sensitivity = payload.get("order_sensitivity_check", {})
    if not isinstance(sensitivity, dict) or sensitivity.get("performed") is not True:
        findings.append(Finding("ERROR", "TOURNAMENT_ORDER_SENSITIVITY_REQUIRED", "order sensitivity check is required"))
    for candidate in candidates:
        if candidate.get("status") == "merged" and not str(candidate.get("duplicate_collapse_rationale", "")).strip():
            findings.append(Finding("ERROR", "TOURNAMENT_DUPLICATE_COLLAPSE_RATIONALE_REQUIRED", f"merged candidate {candidate.get('hypothesis_id')} requires rationale"))
    if payload.get("ranking_model") != "qualitative" and not payload.get("model_based_ranking"):
        findings.append(Finding("ERROR", "TOURNAMENT_MODEL_RANKING_MISSING", "model-based ranking must be retained separately"))
    if not payload.get("qualitative_ranking"):
        findings.append(Finding("ERROR", "TOURNAMENT_QUALITATIVE_RANKING_MISSING", "qualitative ranking must be retained separately"))
    known_hypotheses = set(hypothesis_ids)
    qualitative = [str(value) for value in payload.get("qualitative_ranking", [])]
    model_based = [str(value) for value in payload.get("model_based_ranking", [])]
    if any(value not in known_hypotheses for value in qualitative + model_based):
        findings.append(Finding("ERROR", "TOURNAMENT_RANKING_UNKNOWN_CANDIDATE", "qualitative/model-based ranking references an unknown hypothesis"))
    limitation = str(payload.get("same_model_correlated_judgment_limitation", "")).casefold()
    if "correlat" not in limitation or "limit" not in limitation:
        findings.append(Finding("ERROR", "TOURNAMENT_SAME_MODEL_CORRELATION_LIMIT_MISSING", "same-model correlated-judgment limitation must be explicit"))
    boundary = str(payload.get("winner_interpretation_boundary", "")).lower()
    if not boundary or ("not" not in boundary and "does not" not in boundary):
        findings.append(Finding("ERROR", "TOURNAMENT_WINNER_BOUNDARY_REQUIRED", "winner boundary must state that ranking is not biological validation or proof"))
    final_rows = [row for row in payload.get("final_ranking", []) if isinstance(row, dict)]
    final_ids = [str(row.get("hypothesis_id", "")) for row in final_rows]
    final_ranks = [row.get("rank") for row in final_rows]
    if len(final_ids) != len(set(final_ids)) or any(value not in known_hypotheses for value in final_ids):
        findings.append(Finding("ERROR", "TOURNAMENT_FINAL_RANKING_INVALID_CANDIDATE", "final ranking must reference known hypotheses without duplicates"))
    if len(final_ranks) != len(set(final_ranks)):
        findings.append(Finding("ERROR", "TOURNAMENT_FINAL_RANK_DUPLICATE", "final ranking values must be unique"))
    evidence_scores: dict[str, list[float]] = {}
    blinded_to_hypothesis = {blinded: hypothesis for blinded, hypothesis in zip(blinded_ids, hypothesis_ids)}
    for score in judge_scores:
        blinded_id = str(score.get("blinded_candidate_id", ""))
        value = score.get("evidence_strength")
        if isinstance(value, (int, float)) and not isinstance(value, bool) and blinded_id in blinded_to_hypothesis:
            evidence_scores.setdefault(blinded_to_hypothesis[blinded_id], []).append(float(value))
    for row in final_rows:
        if not isinstance(row, dict):
            continue
        text = " ".join(str(row.get(key, "")) for key in ("verdict", "rationale", "rating_interpretation")).lower()
        decision_text = " ".join(str(row.get(key, "")) for key in ("verdict", "rationale")).lower()
        if "biological proof" in text or "biologically validated" in text:
            findings.append(Finding("ERROR", "TOURNAMENT_WINNER_OVERCLAIM", f"ranked candidate {row.get('hypothesis_id')} is described as proof/validation"))
        if row.get("rank") == 1 and "novel" in decision_text and not any(term in decision_text for term in ("evidence", "feasib", "assay", "information", "safety", "mechan")):
            findings.append(Finding("ERROR", "TOURNAMENT_NOVELTY_ONLY_WINNER", f"winner {row.get('hypothesis_id')} is justified only by novelty"))
        scores = evidence_scores.get(str(row.get("hypothesis_id", "")), [])
        if row.get("evidence_strength") == "high" and (not scores or sum(scores) / len(scores) < 0.67):
            findings.append(Finding("ERROR", "TOURNAMENT_UNSUPPORTED_HIGH_EVIDENCE_STRENGTH", f"ranked candidate {row.get('hypothesis_id')} has unsupported high evidence strength"))
        rating_text = str(row.get("rating_interpretation", "")).casefold()
        if (
            row.get("rating") is not None
            and "evidence strength" in rating_text
            and "not evidence strength" not in rating_text
            and "not a measure of evidence strength" not in rating_text
        ):
            findings.append(Finding("ERROR", "TOURNAMENT_RATING_AS_EVIDENCE_STRENGTH", f"ranked candidate {row.get('hypothesis_id')} conflates model rating with evidence strength"))
    if run_state is not None:
        expected_pack = str(run_state.get("selected_domain_pack", run_state.get("domain_pack", ""))).strip()
        if expected_pack and str(payload.get("selected_domain_pack", "")).strip() != expected_pack:
            findings.append(Finding("ERROR", "TOURNAMENT_DOMAIN_PACK_MISMATCH", "tournament selected_domain_pack does not match run_state"))
        expected_run = str(run_state.get("run_id", "")).strip()
        if expected_run and str(payload.get("workflow_run_id", "")).strip() != expected_run:
            findings.append(Finding("ERROR", "TOURNAMENT_WORKFLOW_RUN_ID_MISMATCH", "tournament workflow_run_id does not match run_state"))
    return findings


def main() -> int:
    args = parse_args()
    run_state = read_json(args.run_state) if args.run_state else None
    findings = check(read_json(args.tournament), run_state)
    if args.json:
        print(json.dumps([asdict(item) for item in findings], indent=2))
    else:
        for finding in findings:
            print(f"{finding.level} {finding.code}: {finding.message}")
        if not findings:
            print("BMAT hypothesis tournament check passed")
    return 1 if any(item.level == "ERROR" for item in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
