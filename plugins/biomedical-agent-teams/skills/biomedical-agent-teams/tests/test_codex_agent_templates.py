from __future__ import annotations

import json
import re
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 uses the supported backport.
    import tomli as tomllib


SKILL_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = SKILL_ROOT / "codex-agents"
AGENT_ROOT = SKILL_ROOT / "agents"
REGISTRY_PATH = SKILL_ROOT / "agent-registry.json"
UTF8_BOM_BYTES = b"\xef\xbb\xbf"
EXPECTED_SPAWNABLE_TEMPLATES = {
    "biostats-repro-auditor",
    "bulk-rnaseq-pipeline-specialist",
    "causal-inference-confounder-analyst",
    "citation-verifier",
    "claim-level-evidence-verifier",
    "contradiction-red-team",
    "meta-review-synthesizer",
    "omics-code-reviewer",
    "omics-provenance-validator",
    "post-write-final-validator",
    "provenance-traceability-architect",
    "risk-of-bias-study-quality-auditor",
    "safety-ethics-privacy-dual-use-auditor",
    "tenx-singlecell-specialist",
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


def read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig").lstrip("\ufeff")


def load_template(path: Path) -> dict[str, object]:
    return tomllib.loads(read_text_file(path))


def load_registry() -> dict[str, object]:
    return json.loads(read_text_file(REGISTRY_PATH))


def load_schema(path: Path) -> dict[str, object]:
    return json.loads(read_text_file(path))


def sample_value_for_schema(property_schema: dict[str, object], field_name: str) -> object:
    enum_values = property_schema.get("enum")
    if isinstance(enum_values, list) and enum_values:
        return enum_values[0]

    field_type = property_schema.get("type")
    if field_type == "array":
        return [f"{field_name} fixture"]
    if field_type == "object":
        return {}
    if field_type == "boolean":
        return True
    if field_type == "integer":
        minimum = property_schema.get("minimum")
        return minimum if isinstance(minimum, int) else 1
    return f"{field_name} fixture"


def assert_portable_schema_sample_is_valid(sample: dict[str, object], schema: dict[str, object]) -> None:
    properties = schema.get("properties")
    assert isinstance(properties, dict)
    for field, value in sample.items():
        property_schema = properties[field]
        assert isinstance(property_schema, dict)
        field_type = property_schema.get("type")
        if field_type == "array":
            assert isinstance(value, list) and value
            assert all(isinstance(item, str) and item for item in value)
        elif field_type == "object":
            assert isinstance(value, dict)
        elif field_type == "boolean":
            assert isinstance(value, bool)
        elif field_type == "integer":
            assert isinstance(value, int) and not isinstance(value, bool)
        else:
            assert isinstance(value, str) and value

        enum_values = property_schema.get("enum")
        if isinstance(enum_values, list):
            assert value in enum_values


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


def test_codex_agent_template_loader_accepts_utf8_bom_prefix(tmp_path: Path) -> None:
    source = TEMPLATE_ROOT / "citation-verifier.toml"
    template = tmp_path / source.name
    template.write_bytes(UTF8_BOM_BYTES + source.read_bytes())

    payload = load_template(template)

    assert payload["agent_id"] == "citation-verifier"


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


def frontmatter_fields(text: str) -> dict[str, str]:
    assert text.startswith("---\n")
    frontmatter = text.split("---\n", 2)[1]
    fields: dict[str, str] = {}
    for line in frontmatter.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip('"')
    return fields


def test_agent_role_prompts_have_router_metadata_and_handoff_contracts() -> None:
    agents = registry_agents()
    for agent_id, agent in sorted(agents.items()):
        prompt_path = agent.get("prompt_path")
        assert isinstance(prompt_path, str)
        text = read_text_file(SKILL_ROOT / prompt_path)
        fields = frontmatter_fields(text)

        assert fields.get("name") == agent_id
        assert fields.get("description"), f"{agent_id} missing frontmatter description"
        assert fields.get("tools"), f"{agent_id} missing frontmatter tools"
        assert (
            "Return contract:" in text
            or "Return a structured spawned-review report" in text
            or "Return a structured" in text
        ), f"{agent_id} missing explicit return contract"
        assert any(
            marker in text.lower()
            for marker in ("claim", "scope", "evidence", "provenance", "verdict", "ledger")
        ), f"{agent_id} missing claim/scope/provenance handoff language"


def test_command_recipes_reference_only_registered_allowed_agents() -> None:
    agents = registry_agents()
    for command in sorted((SKILL_ROOT / "commands").glob("*.md")):
        workflow = command.stem
        text = read_text_file(command)
        referenced_agents = set(re.findall(r"agents/([a-z0-9-]+)\.md", text))
        referenced_agents.update(
            agent_id
            for agent_id in agents
            if re.search(r"`" + re.escape(agent_id) + r"`|\b" + re.escape(agent_id) + r"\b", text)
        )

        unknown = sorted(agent_id for agent_id in referenced_agents if agent_id not in agents)
        assert not unknown, f"{command.name} references unknown agents: {unknown}"

        not_allowed = sorted(
            agent_id
            for agent_id in referenced_agents
            if workflow not in agents[agent_id].get("allowed_workflows", [])
        )
        assert not not_allowed, f"{command.name} references agents not allowed for {workflow}: {not_allowed}"


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


def test_spawnable_templates_match_registry_paths_and_schema_required_fields() -> None:
    agents = registry_agents()
    for agent_id, agent in sorted(agents.items()):
        if agent.get("spawnable") is not True:
            continue

        template_rel = agent.get("toml_template_path")
        prompt_rel = agent.get("prompt_path")
        schema_rel = agent.get("required_output_schema")
        assert isinstance(template_rel, str)
        assert isinstance(prompt_rel, str)
        assert isinstance(schema_rel, str)

        template_path = SKILL_ROOT / template_rel
        assert template_path.exists(), f"{agent_id} template missing: {template_rel}"
        payload = load_template(template_path)

        assert payload.get("agent_id") == agent_id
        assert (template_path.parent / str(payload.get("role_prompt"))).resolve() == (SKILL_ROOT / prompt_rel).resolve()
        assert (template_path.parent / str(payload.get("output_contract_schema"))).resolve() == (
            SKILL_ROOT / schema_rel
        ).resolve()

        required_output_fields = payload.get("required_output_fields")
        assert isinstance(required_output_fields, list)
        assert all(isinstance(field, str) and field.strip() for field in required_output_fields)

        schema = load_schema(SKILL_ROOT / schema_rel)
        required = schema.get("required")
        properties = schema.get("properties")
        assert isinstance(required, list)
        assert isinstance(properties, dict)

        missing = set(required) - set(required_output_fields)
        assert not missing, f"{agent_id} template omits schema-required fields: {sorted(missing)}"

        sample = {}
        for field in required:
            assert isinstance(field, str)
            assert field in properties, f"{agent_id} schema required field lacks property: {field}"
            property_schema = properties[field]
            assert isinstance(property_schema, dict)
            sample[field] = sample_value_for_schema(property_schema, field)
        assert_portable_schema_sample_is_valid(sample, schema)
