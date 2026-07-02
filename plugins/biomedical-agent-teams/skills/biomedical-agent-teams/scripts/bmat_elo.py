#!/usr/bin/env python3
"""Deterministically aggregate BMAT pairwise hypothesis matches with Elo.

This helper is local and dependency-free. Elo ratings are prioritization aids
for tournament transparency, not evidence strength or biological validation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_INITIAL_RATING = 1000.0
DEFAULT_K_FACTOR = 32.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate BMAT pairwise matches with Elo.")
    parser.add_argument("--input", type=Path, required=True, help="Input JSON file with matches.")
    parser.add_argument("--output", type=Path, help="Optional output JSON file.")
    parser.add_argument("--initial-rating", type=float, default=None)
    parser.add_argument("--k-factor", type=float, default=None)
    return parser.parse_args()


def load_payload(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("input JSON must be an object")
    return payload


def expected_score(rating_a: float, rating_b: float) -> float:
    return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))


def normalized_outcome(match: dict[str, Any]) -> tuple[str, str, float, float]:
    outcome = str(match.get("outcome", "")).strip()
    candidate_a = str(match.get("candidate_a") or match.get("winner_id") or "").strip()
    candidate_b = str(match.get("candidate_b") or match.get("loser_id") or "").strip()
    winner = str(match.get("winner_id", "")).strip()
    loser = str(match.get("loser_id", "")).strip()

    if outcome == "tie":
        if not candidate_a or not candidate_b:
            raise ValueError("tie matches require candidate_a and candidate_b")
        return candidate_a, candidate_b, 0.5, 0.5
    if outcome == "a_wins":
        if not candidate_a or not candidate_b:
            raise ValueError("a_wins matches require candidate_a and candidate_b")
        return candidate_a, candidate_b, 1.0, 0.0
    if outcome == "b_wins":
        if not candidate_a or not candidate_b:
            raise ValueError("b_wins matches require candidate_a and candidate_b")
        return candidate_a, candidate_b, 0.0, 1.0
    if outcome == "win":
        if not winner or not loser:
            raise ValueError("win matches require winner_id and loser_id")
        return winner, loser, 1.0, 0.0
    raise ValueError(f"unsupported outcome: {outcome!r}")


def aggregate(payload: dict[str, Any], initial_rating: float | None = None, k_factor: float | None = None) -> dict[str, Any]:
    initial = float(payload.get("initial_rating", initial_rating or DEFAULT_INITIAL_RATING))
    k = float(payload.get("k_factor", k_factor or DEFAULT_K_FACTOR))
    matches = payload.get("matches", [])
    if not isinstance(matches, list):
        raise SystemExit("matches must be a list")

    ratings: dict[str, float] = {}
    stats: dict[str, dict[str, int]] = {}
    processed: list[dict[str, Any]] = []

    def ensure(candidate: str) -> None:
        ratings.setdefault(candidate, initial)
        stats.setdefault(candidate, {"matches": 0, "wins": 0, "losses": 0, "ties": 0})

    for index, raw_match in enumerate(matches, start=1):
        if not isinstance(raw_match, dict):
            raise SystemExit(f"matches[{index}] must be an object")
        try:
            a_id, b_id, score_a, score_b = normalized_outcome(raw_match)
        except ValueError as exc:
            raise SystemExit(f"matches[{index}]: {exc}") from exc
        if not a_id or not b_id or a_id == b_id:
            raise SystemExit(f"matches[{index}]: candidates must be non-empty and distinct")

        ensure(a_id)
        ensure(b_id)
        before_a = ratings[a_id]
        before_b = ratings[b_id]
        expected_a = expected_score(before_a, before_b)
        expected_b = 1.0 - expected_a
        ratings[a_id] = before_a + k * (score_a - expected_a)
        ratings[b_id] = before_b + k * (score_b - expected_b)

        stats[a_id]["matches"] += 1
        stats[b_id]["matches"] += 1
        if score_a == score_b:
            stats[a_id]["ties"] += 1
            stats[b_id]["ties"] += 1
        elif score_a > score_b:
            stats[a_id]["wins"] += 1
            stats[b_id]["losses"] += 1
        else:
            stats[a_id]["losses"] += 1
            stats[b_id]["wins"] += 1
        processed.append(
            {
                "match_id": str(raw_match.get("match_id", f"M-{index:03d}")),
                "candidate_a": a_id,
                "candidate_b": b_id,
                "score_a": score_a,
                "score_b": score_b,
                "rating_a_before": round(before_a, 6),
                "rating_b_before": round(before_b, 6),
                "rating_a_after": round(ratings[a_id], 6),
                "rating_b_after": round(ratings[b_id], 6),
            }
        )

    table = [
        {
            "hypothesis_id": candidate,
            "elo_rating": round(rating, 6),
            "matches": stats[candidate]["matches"],
            "wins": stats[candidate]["wins"],
            "losses": stats[candidate]["losses"],
            "ties": stats[candidate]["ties"],
            "rating_is_prioritization_not_evidence": True,
        }
        for candidate, rating in sorted(ratings.items(), key=lambda item: (-item[1], item[0]))
    ]
    return {
        "tournament_id": payload.get("tournament_id", ""),
        "rating_model": "elo",
        "initial_rating": initial,
        "k_factor": k,
        "ratings": table,
        "processed_matches": processed,
        "rating_interpretation": "prioritization-only; not evidence strength or biological validation",
    }


def main() -> int:
    args = parse_args()
    result = aggregate(load_payload(args.input), args.initial_rating, args.k_factor)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
