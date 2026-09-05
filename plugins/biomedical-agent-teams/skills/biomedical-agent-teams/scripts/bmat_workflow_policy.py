"""Shared workflow planning and artifact-presence policy.

Plans describe required work, never completed execution or runtime capability.
Deep, audit, run, and full-tier plans retain all scientific/review gates.
"""
from __future__ import annotations

import copy
from typing import Any


OUTPUT_ALIASES = {
    "workflow_run": "run_state",
    "runtime_capability_preflight": "preflight",
}


def declared_artifacts(dag: dict[str, Any]) -> set[str]:
    return {
        OUTPUT_ALIASES.get(str(output), str(output))
        for node in dag.get("nodes", []) if isinstance(node, dict)
        for output in node.get("outputs", [])
    }


def plan_workflow(template: dict[str, Any], mode: str, tier: str) -> dict[str, Any]:
    dag = copy.deepcopy(template)
    dag["mode"] = mode
    dag["workflow_id"] = f"{dag['alias']}.{mode}"
    if tier == "full" or mode in {"deep", "audit", "run"}:
        return dag
    nodes = dag["nodes"]
    if mode == "quick":
        # Conceptual quick work has no claim of formal tournament/review execution.
        specialist = copy.deepcopy(nodes[1])
        specialist["outputs"] = ["source_corpus", "claim_ledger"]
        final = copy.deepcopy(nodes[-1])
        final["outputs"] = ["post_write_validation", "final_text"]
        nodes = [nodes[0], specialist, final]
        if dag.get("track") == "hypothesis-tournament":
            dag["track"] = "hypothesis-ideation"
    else:
        # Specialist and source stages remain; dedicated reviewer lanes become
        # optional follow-up work for a compact, non-release plan.
        nodes = [node for node in nodes[:-1] if not node.get("independence_required")]
        nodes.append(dag["nodes"][-1])
    for index, node in enumerate(nodes):
        node["requires"] = [nodes[index - 1]["id"]] if index else []
        node["independence_required"] = False
        node["spawnable"] = False
        node.pop("toml_template_path", None)
        node["outputs"] = [output for output in node["outputs"] if output != "review_artifact_manifest"]
    dag["nodes"] = nodes
    return dag


def tournament_required(artifacts: dict[str, Any]) -> bool:
    dag = artifacts.get("workflow_dag")
    state = artifacts.get("run_state") or {}
    if isinstance(dag, dict):
        if "hypothesis_tournament" in declared_artifacts(dag) or dag.get("track") == "hypothesis-tournament":
            return True
    return state.get("alias") == "idea-discovery-team" and not (
        state.get("mode") == "quick" and state.get("workflow_tier", "compact") == "compact"
    )


def missing_declared_artifacts(artifacts: dict[str, Any], registry: dict[str, str]) -> list[str]:
    dag = artifacts.get("workflow_dag")
    if not isinstance(dag, dict):
        return []
    return sorted(key for key in declared_artifacts(dag) if key in registry and artifacts.get(key) is None)
