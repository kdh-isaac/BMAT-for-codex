"""Shared workflow planning and artifact-presence policy.

Plans describe required work, never completed execution or runtime capability.
Deep, audit, run, and full-tier plans retain all scientific/review gates.
"""
from __future__ import annotations

import copy
import heapq
from typing import Any


OUTPUT_ALIASES = {
    "workflow_run": "run_state",
    "runtime_capability_preflight": "preflight",
}


def graph_errors(dag: dict[str, Any], agents: set[str] | None = None) -> list[tuple[str, str]]:
    """Check graph topology independently of its serialized node order."""
    errors = []
    nodes = dag.get('nodes', [])
    if not isinstance(nodes, list) or not nodes:
        return [('WORKFLOW_DAG_NODES_MISSING', 'A non-empty node list is required.')]
    ids = [str(n.get('id', '')) for n in nodes if isinstance(n, dict)]
    if len(ids) != len(nodes) or any(not x for x in ids):
        return [('WORKFLOW_DAG_NODE_INVALID', 'Nodes require non-empty IDs.')]
    if len(ids) != len(set(ids)):
        errors.append(('WORKFLOW_DAG_DUPLICATE_NODE', 'Node IDs must be unique.'))
    known = set(ids)
    for node in nodes:
        if agents is not None and node.get('agent') not in agents:
            errors.append(('WORKFLOW_DAG_UNKNOWN_AGENT', f"Unknown agent for {node['id']}."))
        deps = node.get('requires', [])
        if not isinstance(deps, list) or any(not isinstance(d, str) for d in deps):
            errors.append(('WORKFLOW_DAG_DEPENDENCY_INVALID', f"Invalid dependencies for {node['id']}."))
        elif len(deps) != len(set(deps)) or not set(deps) <= known:
            errors.append(('WORKFLOW_DAG_DEPENDENCY_INVALID', f"Duplicate or missing dependency for {node['id']}."))
    if not errors:
        try:
            topological_nodes(dag)
        except ValueError:
            errors.append(('WORKFLOW_DAG_CYCLE', 'Dependencies contain a cycle, including possible self-dependency.'))
    return errors


def topological_nodes(dag: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = {n['id']: n for n in dag['nodes']}
    indegree = {key: len(node.get('requires', [])) for key, node in nodes.items()}
    children = {key: [] for key in nodes}
    for key, node in nodes.items():
        for parent in node.get('requires', []):
            if parent not in children:
                raise ValueError('Unknown dependency')
            children[parent].append(key)
    ready = [key for key, degree in indegree.items() if degree == 0]
    heapq.heapify(ready)
    ordered = []
    while ready:
        key = heapq.heappop(ready)
        ordered.append(nodes[key])
        for child in children[key]:
            indegree[child] -= 1
            if indegree[child] == 0:
                heapq.heappush(ready, child)
    if len(ordered) != len(nodes):
        raise ValueError('Cyclic DAG')
    return ordered


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
    nodes = topological_nodes(dag)
    if tier == "full" or mode in {"deep", "audit", "run"}:
        dag['nodes'] = nodes
        return dag
    if mode == "quick":
        # Conceptual quick work has no claim of formal tournament/review execution.
        specialist = copy.deepcopy(next(n for n in nodes if n.get('phase') == 'specialist'))
        specialist["outputs"] = ["source_corpus", "claim_ledger"]
        writer = copy.deepcopy(next(n for n in nodes if n.get('phase') == 'write'))
        writer['outputs'] = ['final_text']
        final = copy.deepcopy(next(n for n in nodes if n.get('phase') == 'post-write'))
        final["outputs"] = ["post_write_validation"]
        nodes = [next(n for n in nodes if n.get('phase') == 'context'), specialist, writer, final]
        if dag.get("track") == "hypothesis-tournament":
            dag["track"] = "hypothesis-ideation"
    else:
        # Specialist and source stages remain; dedicated reviewer lanes become
        # optional follow-up work for a compact, non-release plan.
        nodes = [node for node in nodes if not node.get("independence_required") or node.get('phase') == 'post-write']
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
