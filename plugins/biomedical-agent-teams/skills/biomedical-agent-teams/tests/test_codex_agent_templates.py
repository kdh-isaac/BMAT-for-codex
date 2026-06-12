from __future__ import annotations

import json
from pathlib import Path
import tomllib


SKILL_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = SKILL_ROOT / "codex-agents"
AGENT_ROOT = SKILL_ROOT / "agents"
REGISTRY_PATH = SKILL_ROOT / "agent-registry.json"
EXPECTED_SPAWNABLE_TEMPLATES = {
    "biostats-repro-auditor",
    "causal-inference-confounder-analyst",
    "citation-verifier",
    "claim-level-evidence-verifier",
    "contradiction-red-team",
    "omics-code-reviewer",
    "omics-provenance-validator",
    "post-write-final-validator",
    "provenance-traceability-architect",
    "risk-of-bias-study-quality-auditor",
    "safety-ethics-privacy-dual-use-auditor",
}
GLOBAL_SPAWNED_OUTPUT_FIELDS = {
    "objective",
    "assigned_scope",
    "inputs_checked",
    "tools_skills_commands_or_databases_used",
    "key_findings",
    "contradictions_or_risks",
    "confidence",
    "files_changed_or_none",
    "checks_run_or_skipped",
    "recommended_handoff",
    "affected_claim_ids",
    "verdict",
    "ledger_handoff",
}


def load_template(path: Path) -> dict[str, object]:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def load_registry() -> dict[str, object]:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def registry_agents() -> dict[str, dict[str, object]]:
    registry = load_registry()
    agents = registry.get("agents", [])
    assert isinstance(agents, list)
    out: dict[str, dict[str, object]] = {}
    for agent in agents:
        assert isinstance(agent, dict)
        agent_id = agent.get("agent_id")
        assert isinstance(agent_id, str)
        out[agent_id] = agent
    return out


def test_codex_agent_templates_include_global_spawned_output_contract() -> None:
    templates = sorted(TEMPLATE_ROOT.glob("*.toml"))
    assert templates, "expected at least one Codex reviewer-agent template"

    for path in templates:
        payload = load_template(path)
        fields = set(payload.get("required_output_fields", []))
        missing = GLOBAL_SPAWNED_OUTPUT_FIELDS - fields
        assert not missing, f"{path.name} missing required output fields: {sorted(missing)}"
        output_contract = payload.get("output_contract_schema")
        assert isinstance(output_contract, str)
        assert (path.parent / output_contract).resolve().exists(), f"{path.name} output contract missing: {output_contract}"


def test_codex_agent_template_role_prompts_exist() -> None:
    for path in sorted(TEMPLATE_ROOT.glob("*.toml")):
        payload = load_template(path)
        role_prompt = payload.get("role_prompt")
        assert isinstance(role_prompt, str)
        assert (path.parent / role_prompt).resolve().exists(), f"{path.name} role_prompt missing: {role_prompt}"


def test_agent_registry_covers_all_role_prompt_files() -> None:
    agents = registry_agents()
    prompt_ids = {path.stem for path in AGENT_ROOT.glob("*.md")}

    assert set(agents) == prompt_ids
    for agent_id, agent in agents.items():
        prompt_path = agent.get("prompt_path")
        output_schema = agent.get("required_output_schema")
        assert isinstance(prompt_path, str)
        assert (SKILL_ROOT / prompt_path).exists(), f"{agent_id} prompt missing: {prompt_path}"
        assert isinstance(output_schema, str)
        assert (SKILL_ROOT / output_schema).exists(), f"{agent_id} output schema missing: {output_schema}"


def test_spawnable_registry_entries_have_matching_toml_templates() -> None:
    agents = registry_agents()
    spawnable_agents = {
        agent_id
        for agent_id, agent in agents.items()
        if agent.get("spawnable") is True
    }
    template_agent_ids: set[str] = set()
    for path in sorted(TEMPLATE_ROOT.glob("*.toml")):
        payload = load_template(path)
        agent_id = payload.get("agent_id")
        assert isinstance(agent_id, str), f"{path.name} missing agent_id"
        template_agent_ids.add(agent_id)
        assert agent_id in agents, f"{path.name} references unknown agent_id {agent_id}"
        assert agents[agent_id].get("spawnable") is True, f"{path.name} agent is not marked spawnable"

    assert spawnable_agents == EXPECTED_SPAWNABLE_TEMPLATES
    assert template_agent_ids == EXPECTED_SPAWNABLE_TEMPLATES
