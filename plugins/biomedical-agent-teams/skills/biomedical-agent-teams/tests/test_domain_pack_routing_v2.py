from __future__ import annotations

import json
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
PACKS_ROOT = SKILL_ROOT / "domain-packs"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def command_workflow(command_name: str, next_heading: str) -> str:
    text = (SKILL_ROOT / "commands" / command_name).read_text(encoding="utf-8")
    return text.split("## Workflow", 1)[1].split(next_heading, 1)[0].casefold()


def test_domain_pack_manifests_have_one_neutral_default_and_lazy_load() -> None:
    manifests = {
        path.parent.name: read_json(path)
        for path in PACKS_ROOT.glob("*/domain-pack.json")
    }

    assert set(manifests) == {
        "generic-biomedical",
        "cell-therapy",
        "immuno-oncology",
    }
    assert [name for name, pack in manifests.items() if pack["default"]] == [
        "generic-biomedical"
    ]
    for name, pack in manifests.items():
        assert pack["pack_id"] == name
        assert pack["schema_version"] == "1.0"
        assert pack["domain_pack_version"]
        assert pack["lazy_load"] is True
        assert pack["resource_load_order"][0] == "entity-normalization-rules.json"

    assert manifests["generic-biomedical"]["requires_explicit_selection"] is False
    assert manifests["generic-biomedical"]["domain_specific_assumptions"] == []
    assert manifests["cell-therapy"]["requires_explicit_selection"] is True
    assert manifests["immuno-oncology"]["requires_explicit_selection"] is True
    assert manifests["cell-therapy"]["domain_specific_assumptions"]
    assert manifests["immuno-oncology"]["domain_specific_assumptions"]

    cell_assumptions = " ".join(
        manifests["cell-therapy"]["domain_specific_assumptions"]
    )
    immuno_assumptions = " ".join(
        manifests["immuno-oncology"]["domain_specific_assumptions"]
    )
    assert "CAR-T-intrinsic" in cell_assumptions
    assert "product-intrinsic" in cell_assumptions
    assert "tumor-intrinsic" in immuno_assumptions
    assert "TME-intrinsic" in immuno_assumptions


def test_generic_pack_contains_no_specialty_axes() -> None:
    generic_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((PACKS_ROOT / "generic-biomedical").iterdir())
        if path.is_file() and path.name != "golden-tasks.jsonl"
    ).casefold()

    for forbidden in (
        "car-t",
        "car cell",
        "tumor-intrinsic",
        "tme-intrinsic",
        "product-intrinsic",
        "tumor microenvironment",
    ):
        assert forbidden not in generic_text

    golden_text = (
        PACKS_ROOT / "generic-biomedical" / "golden-tasks.jsonl"
    ).read_text(encoding="utf-8")
    assert "domain_pack_misapplication" in golden_text
    assert "specialty_axis_leakage" in golden_text


def test_generic_workflow_sections_are_domain_neutral() -> None:
    idea_workflow = command_workflow(
        "idea-discovery-team.md", "## Hypothesis Tournament"
    )
    experiment_workflow = command_workflow(
        "experiment-design-team.md", "## Release Policy"
    )

    for workflow in (idea_workflow, experiment_workflow):
        for forbidden in (
            "car-t-intrinsic",
            "product-intrinsic",
            "tumor-intrinsic",
            "tme-intrinsic",
            "car cell therapy relevance",
        ):
            assert forbidden not in workflow


def test_commands_require_structured_pack_selection_and_single_pack_loading() -> None:
    required_fields = (
        "selected_domain_pack",
        "domain_pack_version",
        "selection_reason",
        "domain_specific_assumptions",
    )
    for command_name in ("idea-discovery-team.md", "experiment-design-team.md"):
        text = (SKILL_ROOT / "commands" / command_name).read_text(encoding="utf-8")
        for field in required_fields:
            assert field in text
        assert "generic-biomedical" in text
        assert "Never load all" in text
        assert "domain-packs/<selected_domain_pack>/domain-pack.json" in text


def test_hypothesis_template_separates_judgment_dimensions() -> None:
    text = (
        SKILL_ROOT / "templates" / "hypothesis-tournament-template.md"
    ).read_text(encoding="utf-8")

    for token in (
        "candidate_order_randomization_method",
        "blinded_candidate_id",
        "Per-Judge Score Ledger",
        "judge_disagreement",
        "Order-Sensitivity Check",
        "Ranking Uncertainty",
        "evidence_strength",
        "execution_priority",
        "same_model_correlated_judgment_limitation",
    ):
        assert token in text
    assert "CAR_cell_relevance" not in text
