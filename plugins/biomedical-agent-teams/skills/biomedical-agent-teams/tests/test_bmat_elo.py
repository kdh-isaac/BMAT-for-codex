from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
ELO_SCRIPT = SKILL_ROOT / "scripts" / "bmat_elo.py"


def run_elo(input_path: Path, output_path: Path | None = None) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(ELO_SCRIPT), "--input", str(input_path)]
    if output_path is not None:
        cmd.extend(["--output", str(output_path)])
    return subprocess.run(cmd, text=True, capture_output=True, check=False)


def test_bmat_elo_deterministic_stdout(tmp_path: Path) -> None:
    payload = {
        "tournament_id": "HT-test",
        "initial_rating": 1000,
        "k_factor": 32,
        "matches": [
            {"match_id": "M1", "candidate_a": "H1", "candidate_b": "H2", "outcome": "a_wins"},
            {"match_id": "M2", "candidate_a": "H1", "candidate_b": "H3", "outcome": "tie"},
            {"match_id": "M3", "winner_id": "H3", "loser_id": "H2", "outcome": "win"},
        ],
    }
    input_path = tmp_path / "matches.json"
    input_path.write_text(json.dumps(payload), encoding="utf-8")

    first = run_elo(input_path)
    second = run_elo(input_path)

    assert first.returncode == 0, first.stdout + first.stderr
    assert second.returncode == 0, second.stdout + second.stderr
    assert first.stdout == second.stdout
    result = json.loads(first.stdout)
    assert result["rating_model"] == "elo"
    assert result["rating_interpretation"] == "prioritization-only; not evidence strength or biological validation"
    assert result["ratings"][0]["hypothesis_id"] in {"H1", "H3"}
    assert all(row["rating_is_prioritization_not_evidence"] is True for row in result["ratings"])


def test_bmat_elo_writes_output_file_with_unicode_path(tmp_path: Path) -> None:
    work = tmp_path / "unicode path 한글"
    work.mkdir()
    input_path = work / "matches.json"
    output_path = work / "ratings.json"
    input_path.write_text(
        json.dumps(
            {
                "tournament_id": "HT-unicode",
                "matches": [
                    {"match_id": "M1", "candidate_a": "H1", "candidate_b": "H2", "outcome": "b_wins"}
                ],
            }
        ),
        encoding="utf-8",
    )

    result = run_elo(input_path, output_path)

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["tournament_id"] == "HT-unicode"
    assert payload["ratings"][0]["hypothesis_id"] == "H2"


def test_bmat_elo_rejects_invalid_match_shape(tmp_path: Path) -> None:
    input_path = tmp_path / "bad.json"
    input_path.write_text(
        json.dumps({"matches": [{"candidate_a": "H1", "candidate_b": "H2", "outcome": "unknown"}]}),
        encoding="utf-8",
    )

    result = run_elo(input_path)

    assert result.returncode != 0
    assert "unsupported outcome" in result.stderr
