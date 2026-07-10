import json
import importlib.util
import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "plugins" / "biomedical-agent-teams" / "skills" / "biomedical-agent-teams"
RESOURCE_REF_RE = re.compile(
    r"`((?:agents|commands|contracts|templates|references)/[^`*]+\\.(?:md|json))`"
)


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def payload_from_test_factory(filename: str, factory_name: str) -> dict:
    path = SKILL_ROOT / "tests" / filename
    module_name = f"bmat_schema_sample_{path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load schema sample factory from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    payload = getattr(module, factory_name)()
    if not isinstance(payload, dict):
        raise AssertionError(f"{factory_name} in {path} did not return a JSON object")
    return payload


class BmatPackageTest(unittest.TestCase):
    def test_json_files_parse(self):
        for path in SKILL_ROOT.rglob("*.json"):
            with self.subTest(path=path):
                load_json(path)

    def test_manifest_counts_match_filesystem(self):
        manifest = load_json(SKILL_ROOT / "manifest.json")
        self.assertEqual(manifest["agent_count"], len(list((SKILL_ROOT / "agents").glob("*.md"))))
        self.assertEqual(manifest["command_count"], len(list((SKILL_ROOT / "commands").glob("*.md"))))
        self.assertEqual(manifest["contract_count"], len(list((SKILL_ROOT / "contracts").glob("*.json"))))
        self.assertEqual(manifest["template_count"], len(list((SKILL_ROOT / "templates").glob("*.md"))))
        self.assertEqual(manifest["reference_count"], len(list((SKILL_ROOT / "references").glob("*.md"))))

    def test_source_manifest_resources_exist(self):
        source_manifest = load_json(SKILL_ROOT / "source-manifest.json")
        for command in source_manifest["commands"]:
            self.assertTrue((SKILL_ROOT / "commands" / f"{command}.md").exists(), command)
        for agent in source_manifest["agent_roster"]:
            self.assertTrue((SKILL_ROOT / "agents" / f"{agent}.md").exists(), agent)
        for contract in source_manifest["contracts"]:
            self.assertTrue((SKILL_ROOT / "contracts" / f"{contract}.json").exists(), contract)
        for template in source_manifest["templates"]:
            self.assertTrue((SKILL_ROOT / "templates" / f"{template}.md").exists(), template)
        for reference in source_manifest["references"]:
            self.assertTrue((SKILL_ROOT / "references" / f"{reference}.md").exists(), reference)

    def test_version_files_are_aligned(self):
        version = (SKILL_ROOT / "VERSION").read_text(encoding="utf-8").strip()
        plugin = load_json(ROOT / "plugins" / "biomedical-agent-teams" / ".codex-plugin" / "plugin.json")
        manifest = load_json(SKILL_ROOT / "manifest.json")
        source_manifest = load_json(SKILL_ROOT / "source-manifest.json")
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        workflow_template = (SKILL_ROOT / "templates" / "workflow-run-template.md").read_text(
            encoding="utf-8"
        )
        passport_template = (SKILL_ROOT / "templates" / "biomedical-passport-template.md").read_text(
            encoding="utf-8"
        )
        self.assertEqual(plugin["version"], version)
        self.assertEqual(manifest["version"], version)
        self.assertEqual(manifest["adapter_version"], version)
        self.assertEqual(source_manifest["version"], version)
        self.assertIn(f'version: "{version}"', skill_text)
        self.assertIn(f"| plugin_version | {version} |", workflow_template)
        self.assertIn(f"| workflow_version | {version} |", passport_template)

    def test_workflow_label_vocabulary_is_consistent(self):
        expected_labels = {
            "Full protocol followed",
            "Contract-shaped artifact bundle",
            "Compact standard workflow",
            "Biomedical Agent Teams-informed narrative review",
            "Limited capability-downgraded workflow",
            "Partial workflow; formal gates skipped",
            "Blocked",
        }
        workflow_schema = load_json(SKILL_ROOT / "contracts" / "workflow-run.schema.json")
        workflow_labels = set(workflow_schema["properties"]["final_label"]["enum"])
        self.assertEqual(workflow_labels, expected_labels)

        surfaces = {
            "SKILL.md": SKILL_ROOT / "SKILL.md",
            "workflow-run-template.md": SKILL_ROOT / "templates" / "workflow-run-template.md",
            "integrity-gate-template.md": SKILL_ROOT / "templates" / "integrity-gate-template.md",
            "biomedical-research-council.md": SKILL_ROOT / "commands" / "biomedical-research-council.md",
            "bmat_validate.py": SKILL_ROOT / "scripts" / "bmat_validate.py",
        }
        for name, path in surfaces.items():
            text = path.read_text(encoding="utf-8")
            with self.subTest(surface=name):
                for label in expected_labels:
                    self.assertIn(label, text)
                self.assertNotIn("Limited / capability-downgraded workflow", text)

        for command in (SKILL_ROOT / "commands").glob("*.md"):
            text = command.read_text(encoding="utf-8")
            with self.subTest(command=command.name):
                self.assertNotIn("compact or partial workflow", text)
                self.assertNotIn("label the result as a compact or partial", text)

    def test_router_aliases_match_source_manifest_commands(self):
        source_manifest = load_json(SKILL_ROOT / "source-manifest.json")
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        for command in source_manifest["commands"]:
            with self.subTest(command=command):
                self.assertIn(f"commands/{command}.md", skill_text)

    def test_markdown_resource_references_resolve(self):
        for markdown in SKILL_ROOT.rglob("*.md"):
            text = markdown.read_text(encoding="utf-8")
            for ref in RESOURCE_REF_RE.findall(text):
                with self.subTest(markdown=markdown.relative_to(SKILL_ROOT), reference=ref):
                    self.assertTrue((SKILL_ROOT / ref).exists(), ref)

    def test_router_delegates_bundled_resource_inventory_to_manifest(self):
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        source_manifest = load_json(SKILL_ROOT / "source-manifest.json")

        self.assertIn("source-manifest.json", skill_text)
        self.assertIn("scripts/bmat_docs_list.py", skill_text)
        self.assertIn("scripts/bmat_package_check.py", skill_text)
        self.assertIn("Do not load every agent, command, reference, contract, or template by default.", skill_text)

        for collection in ("contracts", "templates", "references"):
            self.assertIsInstance(source_manifest[collection], list)
            self.assertGreater(len(source_manifest[collection]), 0)

    def test_package_maintenance_commands_are_repo_root_consistent(self):
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        root_readme = (ROOT / "README.md").read_text(encoding="utf-8")
        expected_commands = (
            "python plugins/biomedical-agent-teams/skills/biomedical-agent-teams/scripts/"
            "bmat_package_check.py --root plugins/biomedical-agent-teams",
            "python plugins/biomedical-agent-teams/skills/biomedical-agent-teams/scripts/"
            "bmat_selftest.py --root plugins/biomedical-agent-teams",
            "python plugins/biomedical-agent-teams/skills/biomedical-agent-teams/evals/"
            "validate_golden_eval_schema.py --tasks plugins/biomedical-agent-teams/skills/"
            "biomedical-agent-teams/evals/golden_tasks.jsonl --outputs plugins/"
            "biomedical-agent-teams/skills/biomedical-agent-teams/evals/sample_outputs.jsonl",
            "python plugins/biomedical-agent-teams/skills/biomedical-agent-teams/evals/"
            "run_golden_eval.py --tasks plugins/biomedical-agent-teams/skills/"
            "biomedical-agent-teams/evals/golden_tasks.jsonl --outputs plugins/"
            "biomedical-agent-teams/skills/biomedical-agent-teams/evals/sample_outputs.jsonl --strict --gate",
            "uvx --with pytest --with jsonschema python -B -m pytest -p no:cacheprovider "
            "tests plugins/biomedical-agent-teams/skills/biomedical-agent-teams/tests -q",
        )

        self.assertIn("from the repository or marketplace root", skill_text)
        for command in expected_commands:
            with self.subTest(command=command):
                self.assertIn(command, skill_text)

        self.assertIn(expected_commands[-1], root_readme)
        self.assertNotIn("python scripts/bmat_package_check.py --root <plugin-root>", skill_text)
        self.assertNotIn("pytest plugins/biomedical-agent-teams/skills/biomedical-agent-teams/tests tests -q", skill_text)

    def test_all_command_recipes_have_v03_preflight_language(self):
        for command in (SKILL_ROOT / "commands").glob("*.md"):
            text = command.read_text(encoding="utf-8")
            with self.subTest(command=command.name):
                self.assertIn("runtime capability preflight", text)
                self.assertIn("source", text.lower())
                self.assertIn("final workflow label", text)
                self.assertIn("skipped gates", text)

    def test_benchmark_hygiene_guard_is_present(self):
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        omics_text = (SKILL_ROOT / "commands" / "omics-analysis-team.md").read_text(encoding="utf-8")
        for text in (skill_text, omics_text):
            self.assertIn("truth files", text)
            self.assertIn("results", text)
            self.assertIn("scoring scripts", text)
            self.assertIn("Dockerfiles", text)

    def test_v034_hybrid_execution_policy_is_present(self):
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("inline_first_selective_review", skill_text)
        self.assertIn("team_level_selective_dag", skill_text)
        self.assertIn("Nested spawning is disabled by default", skill_text)
        self.assertTrue((SKILL_ROOT / "references" / "hybrid-execution-policy.md").exists())
        self.assertTrue((SKILL_ROOT / "templates" / "team-spawn-plan-template.md").exists())

        council_text = (SKILL_ROOT / "commands" / "biomedical-research-council.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Hybrid Execution Policy", council_text)
        self.assertIn("team_level_selective_dag", council_text)

        for command in (SKILL_ROOT / "commands").glob("*.md"):
            text = command.read_text(encoding="utf-8")
            with self.subTest(command=command.name):
                self.assertIn("execution_strategy", text)
                self.assertIn("nested_spawn_policy", text)

    def test_v034_hybrid_spine_order_separates_team_dag_from_review(self):
        source_manifest = load_json(SKILL_ROOT / "source-manifest.json")
        spine = source_manifest["workflow_spine"]
        self.assertLess(
            spine.index("execution-strategy-lock"),
            spine.index("team-level-selective-dag"),
        )
        self.assertLess(
            spine.index("team-level-selective-dag"),
            spine.index("central-claim-ledger-evidence-graph"),
        )
        self.assertLess(
            spine.index("audit-gates"),
            spine.index("selective-spawned-review"),
        )
        self.assertLess(
            spine.index("selective-spawned-review"),
            spine.index("claim-level-evidence-verifier"),
        )

        workflow_template = (SKILL_ROOT / "templates" / "workflow-run-template.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("| team_spawn_outputs |", workflow_template)
        self.assertIn("| selective_review_outputs |", workflow_template)
        self.assertIn("selective_review_outputs when used", workflow_template)

    def test_readme_workflow_structure_matches_current_model(self):
        version = (SKILL_ROOT / "VERSION").read_text(encoding="utf-8").strip()
        for readme in (ROOT / "README.md", ROOT / "plugins" / "biomedical-agent-teams" / "README.md"):
            text = readme.read_text(encoding="utf-8")
            with self.subTest(readme=readme.relative_to(ROOT)):
                self.assertIn(f"accTitle: BMAT v{version} Workflow Structure", text)
                self.assertIn("Runtime, scope, source, and strategy lock", text)
                self.assertIn("team_level_selective_dag", text)
                self.assertIn("team_output_artifacts", text)
                self.assertIn("selective spawned review", text)
                self.assertIn("spawned_agent_instances", text)
                self.assertIn("bmat_loop_check.py", text)

    @unittest.skipUnless(importlib.util.find_spec("jsonschema"), "jsonschema is not installed")
    def test_v03_schema_samples_validate(self):
        from jsonschema import Draft202012Validator

        version = (SKILL_ROOT / "VERSION").read_text(encoding="utf-8").strip()
        samples = {
            "biomedical-passport.schema.json": {
                "passport_id": "BP-20260610-001",
                "workflow_alias": "biomedical-research-council",
                "workflow_version": version,
                "created_at": "2026-06-10",
                "updated_at": "2026-06-10",
                "context_lock": {"question": "audit BMAT package"},
                "normalized_entities": [],
                "source_corpus": [],
                "workflow_run": {"run_id": "BMAT-RUN-20260610-001"},
                "stage_evaluation": {"overall_verdict": "pass"},
                "claim_ledger": {
                    "location_or_summary": "inline smoke sample",
                    "status": "pass",
                },
                "gate_status": [
                    {
                        "gate": "claim ledger",
                        "status": "pass",
                        "reason": "sample validates schema shape",
                    }
                ],
                "outputs": [],
                "resume_state": {
                    "current_stage": "complete",
                    "next_action": "none",
                    "open_questions": [],
                },
            },
            "preflight-contract.schema.json": {
                "runtime_capability_preflight_id": "RCP-20260610-001",
                "requested_alias": "biomedical-research-council",
                "selected_mode": "deep",
                "deliverable_type": "audit bundle",
                "evidence_scope": {
                    "source_types": ["PMID", "GEO"],
                    "species_or_model": "human",
                    "date_or_version_needs": "retrieval date required",
                },
                "risk_class": "moderate",
                "required_role_outputs": ["claim-level-evidence-verifier"],
                "skipped_role_outputs_with_reason": [],
                "external_tools_allowed": {
                    "allowed": True,
                    "limits": "public sources only",
                },
                "file_write_plan": {
                    "will_write_files": False,
                    "allowed_paths": [],
                },
                "stop_criteria": ["missing source corpus"],
                "checkpoint_plan": [
                    {
                        "checkpoint": "ledger built",
                        "required_before": "final writing",
                    }
                ],
                "execution_strategy": "inline_first_selective_review",
                "spawned_review_plan": {
                    "allowed": True,
                    "budget": 1,
                    "selected_roles": ["claim-level-evidence-verifier"],
                    "rationale": "independent claim audit",
                },
                "team_spawn_plan": {
                    "allowed": False,
                    "budget": 0,
                    "selected_teams": [],
                    "dependency_graph": [],
                    "nested_spawn_allowed": False,
                    "rationale": "single-axis audit",
                },
                "all_role_spawn_avoidance_reason": "role swarm adds coordination overhead",
                "nested_spawn_policy": {
                    "allowed": False,
                    "authorization": "not requested",
                    "limits": "spawned reviewers only",
                },
                "post_team_audit_plan": "merge accepted review findings into the central claim ledger",
            },
            "lead-decision.schema.json": {
                "schema_version": "1.0",
                "decision_id": "LD-20260610-001",
                "workflow_run_id": "BMAT-RUN-20260610-001",
                "lead_scientist_agent_id": "life-science-lead-scientist",
                "requested_alias": "evidence-audit-team",
                "selected_mode": "audit",
                "workflow_tier": "compact",
                "selected_playbook": "evidence-audit",
                "omics_subtrack": "not-applicable",
                "execution_strategy": "inline_first_selective_review",
                "lead_route_required": True,
                "mode_rule": "schema smoke sample requires lead route capture",
                "decision_rationale": "schema smoke sample locks the selected playbook and review lanes",
                "selected_lanes": ["claim-level-evidence-verifier"],
                "skipped_lanes": [],
                "spawned_review_plan": {
                    "allowed": True,
                    "budget": 1,
                    "selected_roles": ["claim-level-evidence-verifier"],
                    "rationale": "independent claim audit",
                },
                "team_spawn_plan": {
                    "allowed": False,
                    "budget": 0,
                    "selected_teams": [],
                    "dependency_graph": [],
                    "nested_spawn_allowed": False,
                    "rationale": "single-axis audit",
                },
                "post_team_audit_plan": "merge accepted review findings into the central claim ledger",
            },
            "runtime-capability-preflight.schema.json": {
                "runtime_id": "RCP-20260609-001",
                "codex_client": "Codex Desktop",
                "plugin_version": version,
                "workspace_root": "G:/work",
                "capabilities": {
                    "web_search_available": "yes",
                    "shell_available": "yes",
                    "file_read_available": "yes",
                    "file_write_available": "yes",
                    "network_available": "yes",
                },
                "external_bio_tools_available": {"pubmed": "unknown"},
                "spawned_subagents_supported": "unknown",
                "sandbox_profile": "unrestricted",
                "downgrade_rule": "Downgrade if a required capability is unavailable.",
            },
            "workflow-run.schema.json": {
                "run_id": "BMAT-RUN-20260609-001",
                "alias": "omics-analysis-team",
                "mode": "run",
                "plugin_version": version,
                "execution_strategy": "inline_first_selective_review",
                "nested_spawn_allowed": False,
                "spawned_review_lanes": [
                    {
                        "role": "omics-provenance-validator",
                        "status": "planned",
                        "rationale": "review run provenance",
                        "ledger_handoff": "pending",
                    }
                ],
                "team_spawn_lanes": [],
                "stages": [
                    {
                        "id": "runtime_capability_preflight",
                        "required": True,
                        "status": "pass",
                        "evidence": "checked",
                    }
                ],
                "final_label": "Compact standard workflow",
                "downgrade_reasons": [],
            },
            "source-corpus.schema.json": {
                "corpus_id": "SC-20260609-001",
                "created_at": "2026-06-09",
                "sources": [
                    {
                        "source_id": "S-001",
                        "source_type": "PMID",
                        "identifier": "123456",
                        "version_or_retrieval_date": "2026-06-09",
                        "inclusion_status": "included",
                        "claim_use": "background",
                        "checked_by": "citation-verifier",
                        "limitations": "none material",
                        "evidence_spans": [
                            {
                                "span_id": "span1",
                                "location": "schema smoke excerpt",
                                "evidence_span_ref": "S-001:span1",
                                "scope_note": "schema smoke sample",
                            }
                        ],
                    }
                ],
            },
            "claim-ledger.schema.json": {
                "claims": [
                    {
                        "claim_id": "CL-001",
                        "atomic_claim": "Schema smoke claim.",
                        "claim_type": "source-backed",
                        "source_backed": True,
                        "source_ids": ["S-001"],
                        "audit_status": "pass",
                        "claim_strength": "exploratory",
                        "tool_backed": True,
                        "tool_ids": ["local-bmat-validators"],
                        "result_ids": ["RI-ROW-001"],
                        "entity_ids": {
                            "gene": ["HGNC:0000"],
                            "publication": ["PMID:123456"]
                        },
                        "evidence_edges": [
                            {
                                "subject": "schema subject",
                                "predicate": "supports",
                                "object": "schema object",
                                "source_id": "S-001",
                                "evidence_span_ref": "S-001:span1"
                            }
                        ],
                        "scope_match": {
                            "species": "match",
                            "cell_type": "not-applicable",
                            "assay": "not-applicable",
                            "endpoint": "match"
                        },
                        "entailment_verdict": "supports",
                        "allowed_final_wording": "Schema smoke claim."
                    }
                ]
            },
            "tool-call-ledger.schema.json": {
                "schema_version": "1.0",
                "ledger_id": "TCL-20260610-001",
                "plugin_version": version,
                "workflow_run_id": "BMAT-RUN-20260610-001",
                "calls": [
                    {
                        "call_id": "TC-001",
                        "tool_id": "local-bmat-validators",
                        "status": "success",
                        "inputs_digest": "schema smoke",
                        "output_ref": "results_integration:RI-ROW-001",
                        "retrieval_date": "not-applicable",
                        "affected_claim_ids": ["CL-001"],
                        "provenance": {
                            "source_id": "S-001",
                            "url_or_accession": "local-fixture"
                        }
                    }
                ]
            },
            "workflow-dag.schema.json": {
                "workflow_id": "evidence-audit-team.audit",
                "runtime": "codex",
                "alias": "evidence-audit-team",
                "mode": "audit",
                "track": "claim-evidence-audit",
                "nodes": [
                    {
                        "id": "S0_context_lock",
                        "agent": "protocol-context-locker",
                        "outputs": ["runtime_capability_preflight"],
                        "blocking": True
                    },
                    {
                        "id": "S1_review",
                        "agent": "claim-level-evidence-verifier",
                        "requires": ["S0_context_lock"],
                        "outputs": ["results_integration"],
                        "blocking": True,
                        "spawnable": True,
                        "toml_template_path": "codex-agents/claim-level-evidence-verifier.toml",
                        "independence_required": True
                    }
                ],
                "release_gates": ["bmat_validate", "bmat_tool_ledger_check"]
            },
            "hypothesis-tournament.schema.json": {
                "tournament_id": "HT-20260609-001",
                "context_lock": "CAR-T idea discovery",
                "candidates": [
                    {
                        "hypothesis_id": "H-001",
                        "hypothesis": "testable idea",
                        "status": "active",
                    }
                ],
                "rounds": [
                    {
                        "round_id": "R0",
                        "round_type": "generation",
                        "output_summary": "generated",
                    }
                ],
                "final_ranking": [
                    {
                        "rank": 1,
                        "hypothesis_id": "H-001",
                        "verdict": "advance",
                        "rationale": "high EIG",
                    }
                ],
            },
            "omics-run-manifest.schema.json": {
                "schema_version": "2.0",
                "analysis_id": "OMICS-20260610-001",
                "workflow_run_id": "BMAT-RUN-20260610-001",
                "track": "bulk-rnaseq",
                "data_sources": [{"source_id": "local-smoke"}],
                "sample_sheet": "samples.csv",
                "assay_metadata": {
                    "organism": "Homo sapiens",
                    "genome_build": "GRCh38",
                    "annotation_release": "GENCODE v44",
                    "quantifier": "salmon",
                    "transcriptome_reference": "GENCODE v44 transcriptome",
                    "tx_to_gene_method": "tximeta",
                    "read_layout": "paired-end",
                },
                "biological_unit_policy": {
                    "unit": "sample",
                    "replicate_key": "sample_id",
                    "pseudobulk_required": False,
                },
                "contrast_or_endpoint": "case vs control",
                "software_versions": ["salmon 1.10", "DESeq2 1.42"],
                "qc_decisions": {
                    "fastq_qc": "FastQC",
                    "multiqc_ref": "multiqc.html",
                    "low_count_filter": "keep genes with >=10 counts in >=2 samples",
                    "outlier_policy": "Cook distance review",
                },
                "de_strategy": {
                    "cross_sample_method": "DESeq2",
                    "multiplicity_method": "BH-FDR",
                    "design_formula": "~ batch + condition",
                    "design_matrix_rank_checked": True,
                    "count_model": "negative binomial",
                },
                "stage_evaluation": {"S1": "pass"},
                "generated_artifacts": {
                    "multiqc_html": "multiqc.html",
                    "count_matrix": "counts.tsv",
                    "design_matrix": "design.tsv",
                    "de_results_table": "de.tsv",
                },
                "review_status": {
                    "code_review": "pass",
                    "provenance_review": "pass",
                    "biostats_review": "not-applicable",
                },
            },
            "post-write-validation.schema.json": {
                "final_validator_verdict": "pass",
                "unsupported_final_claims": [],
                "citation_or_provenance_mismatches": [],
                "missing_uncertainty_or_limitations": [],
                "safety_ethics_privacy_issues": [],
                "failure_mode_checklist": [
                    {
                        "failure_mode": "self-ratification",
                        "status": "not-applicable",
                        "reason": "schema smoke sample",
                    }
                ],
                "excluded_claim_handling": "none",
                "independent_review_status": "not-applicable",
                "minimal_required_corrections": [],
                "release_ready_claim_strength": "low",
            },
            "results-integration.schema.json": {
                "schema_version": "0.8",
                "integration_id": "RI-20260610-001",
                "plugin_version": version,
                "workflow_run_id": "BMAT-RUN-20260610-001",
                "source_corpus_lock": "locked",
                "input_artifacts": ["source-corpus.json", "claim-ledger.tsv"],
                "tool_use_log": [
                    {
                        "tool_id": "local-bmat-validators",
                        "invocation_surface": "local script",
                        "status": "used",
                        "used": True,
                        "retrieval_date": "not-applicable",
                        "source_corpus_rows": ["SC-001"],
                        "result_rows": ["RI-ROW-001"],
                        "downgrade_reason": "",
                    }
                ],
                "rows": [
                    {
                        "result_id": "RI-ROW-001",
                        "result_type": "tool-output",
                        "source_ref": "SC-001",
                        "claim_ids": ["CL-001"],
                        "status": "support",
                        "evidence_direction": "supports",
                        "confidence": "moderate",
                        "effect_or_observation": "schema smoke result",
                        "sample_or_model_scope": "not-applicable",
                        "statistical_support": "not-applicable",
                        "interpretation": "Sample maps a validator result to a bounded claim.",
                        "limitations": "Schema smoke sample, not a real audit.",
                        "ledger_action": "update",
                        "reviewer_or_human_gate": "not-needed",
                    }
                ],
                "final_claim_policy": "ledger-only",
                "human_review_status": "not-needed",
                "release_notes": ["schema smoke sample"],
            },
            "source-verification.schema.json": {
                "schema_version": "1.0",
                "verification_id": "SV-20260709-001",
                "plugin_version": version,
                "workflow_run_id": "BMAT-RUN-20260610-001",
                "checked_at": "2026-07-09",
                "rows": [
                    {
                        "source_id": "S-001",
                        "source_type": "PMID",
                        "identifier": "123456",
                        "identifier_status": "verified",
                        "metadata_match": "pass",
                        "canonical_title": "schema smoke source",
                        "retrieval_surface": "local fixture",
                        "source_corpus_row_status": "present",
                        "claim_ids_checked": ["CL-001"],
                        "verification_limitations": "schema smoke sample",
                    }
                ],
            },
            "claim-support-matrix.schema.json": {
                "schema_version": "1.0",
                "support_matrix_id": "CSM-20260709-001",
                "plugin_version": version,
                "workflow_run_id": "BMAT-RUN-20260610-001",
                "rows": [
                    {
                        "claim_id": "CL-001",
                        "source_id": "S-001",
                        "evidence_span_ref": "S-001:span1",
                        "support_verdict": "supports",
                        "scope_match": {
                            "species": "match",
                            "cell_type": "not-applicable",
                            "assay": "not-applicable",
                            "endpoint": "match",
                        },
                        "overclaim_risk": "low",
                        "allowed_in_final": True,
                        "allowed_final_wording": "Schema smoke claim.",
                        "review_surface": "local fixture",
                        "independent_review_required": False,
                        "limitations": "schema smoke sample",
                    }
                ],
            },
            "omics-metadata-check.schema.json": {
                "schema_version": "1.0",
                "check_id": "OMC-20260709-001",
                "plugin_version": version,
                "workflow_run_id": "BMAT-RUN-20260610-001",
                "track": "bulk-rnaseq",
                "status": "pass",
                "blocking_issues": [],
                "warnings": [],
                "artifact_refs": ["omics_run_manifest.json"],
                "claim_ids_affected": ["CL-001"],
                "downgrade_recommendations": [],
            },
            "experiment-design.schema.json": {
                "design_id": "ED-20260709-001",
                "workflow_run_id": "BMAT-RUN-20260610-001",
                "plugin_version": version,
                "hypothesis": "Schema smoke hypothesis.",
                "experimental_objective": "Validate schema shape for experiment design.",
                "experimental_unit": {
                    "unit_type": "donor",
                    "justification": "biological unit smoke sample",
                },
                "primary_endpoint": "bounded schema validation outcome",
                "positive_controls": ["known-positive control"],
                "negative_controls": ["untreated negative control"],
                "vehicle_or_mock_controls": ["mock transduction control"],
                "biological_replicates": {"n": 3, "unit": "donor"},
                "technical_replicates": {"n": 2, "unit": "well"},
                "randomization": {"plan": "randomize plate position"},
                "blinding": {"plan": "blind endpoint quantification"},
                "exclusion_criteria": ["predefined QC failure"],
                "confounders": ["batch"],
                "causal_kill_tests": ["orthogonal perturbation"],
                "statistical_plan": {"test": "two-sided test with FDR where needed"},
                "go_no_go_gates": ["positive control passes"],
                "safety_ethics_privacy_boundary": "public-only schema smoke sample",
                "reagent_provenance_policy": "record vendor, catalog, lot, and validation status",
                "source_ids": ["S-001"],
                "claim_ids_supported": ["CL-001"],
            },
            "review-artifact-manifest.schema.json": {
                "schema_version": "1.0",
                "workflow_run_id": "BMAT-RUN-20260610-001",
                "plugin_version": version,
                "review_instances": [
                    {
                        "instance_id": "REV-001",
                        "agent_id": "claim-level-evidence-verifier",
                        "execution_surface": "local fixture",
                        "input_scope": "schema smoke sample",
                        "input_digest": "schema-smoke",
                        "output_artifact": "post_write_validation.json",
                        "output_sha256": "0" * 64,
                        "checks_run": ["jsonschema validation"],
                        "ledger_handoff": "none",
                        "results_integration_rows": [],
                        "changed_claim_ids": [],
                        "limitations": "schema smoke sample",
                    }
                ],
            },
            "role-output.schema.json": {
                "role": "claim-level-evidence-verifier",
                "task_scope": "schema smoke sample",
                "inputs_checked": ["none"],
                "methods_or_tools_used": ["jsonschema"],
                "key_findings": ["sample validates schema shape"],
                "limitations": ["not a real audit"],
                "handoff": {"claim_ids": []},
                "verdict": "pass",
            },
            "stage-evaluation.schema.json": {
                "evaluation_id": "SE-20260609-001",
                "workflow_alias": "omics-analysis-team",
                "stages": [
                    {
                        "stage_id": "S1",
                        "stage_name": "Plan",
                        "status": "pass",
                        "evidence": "locked",
                        "blocking_issues": [],
                    }
                ],
                "overall_verdict": "pass",
            },
            "agent-registry.schema.json": {
                "version": version,
                "runtime": "codex",
                "agents": [
                    {
                        "agent_id": "claim-level-evidence-verifier",
                        "prompt_path": "agents/claim-level-evidence-verifier.md",
                        "spawnable": True,
                        "default_execution_surface": "spawned_reviewer",
                        "allowed_workflows": ["evidence-audit-team"],
                        "required_output_schema": "contracts/spawned-agent-output.schema.json",
                        "privacy_level": "public_only",
                        "recommended_modes": ["audit"],
                        "toml_template_path": "codex-agents/claim-level-evidence-verifier.toml",
                    }
                ],
            },
            "spawned-agent-output.schema.json": {
                "objective": "schema smoke sample",
                "assigned_scope": "validate output contract shape",
                "inputs_checked": ["none"],
                "tools_skills_commands_or_databases_used": ["jsonschema"],
                "key_findings": ["sample validates schema shape"],
                "contradictions_or_risks": [],
                "confidence": "not-assessable",
                "files_changed_or_none": "none",
                "checks_run_or_skipped": ["jsonschema validation"],
                "recommended_handoff": "none",
                "affected_claim_ids": [],
                "verdict": "pass",
                "ledger_handoff": "none",
            },
            "loop-state.schema.json": {
                "loop_id": "LOOP-20260610-001",
                "loop_name": "schema smoke loop",
                "loop_type": "weekly_literature_watch",
                "plugin_version": version,
                "status": "complete",
                "public_only": True,
                "private_context_allowed": False,
                "external_tools_allowed": True,
                "connectors_allowed": ["pubmed"],
                "human_review_required": False,
                "human_gate_status": "not-required",
                "state_path": "loop_state.json",
                "source_delta_status": "none",
                "cycle_count": 1,
                "cycle_budget": 1,
                "open_items": [],
                "reviewer_objections": [],
                "stop_conditions": ["schema smoke complete"],
                "stop_status": "stop",
                "output_artifacts": [
                    {
                        "artifact_id": "ART-001",
                        "path": "source_delta.md",
                        "artifact_type": "source_delta",
                        "status": "reviewed",
                    }
                ],
                "privacy_boundary": "public-only schema smoke sample",
            },
        }

        release_fixture = (
            SKILL_ROOT / "tests" / "fixtures" / "valid_full_protocol_bundle"
        )
        fixture_schema_files = {
            "preflight-contract.schema.json": "runtime_capability_preflight.json",
            "lead-decision.schema.json": "lead_decision.json",
            "workflow-run.schema.json": "run_state.json",
            "source-corpus.schema.json": "source_corpus.json",
            "claim-ledger.schema.json": "claim_ledger.json",
            "tool-call-ledger.schema.json": "tool_call_ledger.json",
            "post-write-validation.schema.json": "post_write_validation.json",
            "results-integration.schema.json": "results_integration.json",
            "source-verification.schema.json": "source_verification.json",
            "claim-support-matrix.schema.json": "claim_support_matrix.json",
            "review-artifact-manifest.schema.json": "review_artifact_manifest.json",
            "review-runtime-receipt.schema.json": "review/review-runtime-receipt.json",
            "stage-evaluation.schema.json": "stage_evaluation.json",
            "bundle-manifest.schema.json": "bundle_manifest.json",
        }
        for schema_name, fixture_name in fixture_schema_files.items():
            samples[schema_name] = load_json(release_fixture / fixture_name)

        review_row = samples["review-artifact-manifest.schema.json"][
            "review_instances"
        ][0]
        samples["spawned-agent-output.schema.json"] = {
            "schema_version": "2.0",
            "workflow_run_id": "release-fixture-run-001",
            "plugin_version": version,
            **{
                key: review_row[key]
                for key in (
                    "instance_id",
                    "agent_id",
                    "actor_type",
                    "provider",
                    "model",
                    "model_version",
                    "authoring_provider",
                    "authoring_model",
                    "authoring_model_version",
                    "authoring_execution_session_id",
                    "authoring_identity_available",
                    "execution_surface",
                    "execution_session_id",
                    "spawn_event_id",
                    "input_scope",
                    "input_artifact_refs",
                    "input_artifact_sha256",
                    "prompt_template_ref",
                    "prompt_template_sha256",
                    "output_artifact",
                    "output_sha256",
                    "changed_claim_ids",
                    "ledger_handoff",
                    "independence_class",
                    "independent_review_eligible",
                    "fixture_only",
                    "authoring_context_shared",
                    "started_at",
                    "completed_at",
                    "runtime_receipt_ref",
                    "runtime_receipt_sha256",
                    "limitations",
                )
            },
            "objective": "Perform a deterministic claim-support review.",
            "assigned_scope": "Review one bounded claim and its exact source span.",
            "inputs_checked": ["claim ledger", "source corpus", "source verification"],
            "tools_skills_commands_or_databases_used": ["bmat_claim_support_check.py"],
            "key_findings": ["The bounded wording is contract-consistent."],
            "contradictions_or_risks": [],
            "confidence": "high",
            "files_changed_or_none": "none",
            "checks_run": review_row["checks_run"],
            "checks_run_or_skipped": review_row["checks_run"],
            "recommended_handoff": "Integrate RI-REVIEW-001.",
            "affected_claim_ids": ["CL-001"],
            "verdict": "pass",
        }

        samples["experiment-design.schema.json"] = payload_from_test_factory(
            "test_bmat_experiment_design_v2.py", "valid_design"
        )
        samples["hypothesis-tournament.schema.json"] = payload_from_test_factory(
            "test_bmat_tournament_v2.py", "valid_tournament"
        )
        samples["agent-registry.schema.json"] = load_json(
            SKILL_ROOT / "agent-registry.json"
        )
        samples["workflow-dag.schema.json"].update(
            {
                "schema_version": "2.0",
                "plugin_version": version,
                "workflow_run_id": "BMAT-RUN-20260610-001",
                "created_at": "2026-07-10T00:00:00Z",
            }
        )
        samples["omics-run-manifest.schema.json"].update(
            {
                "plugin_version": version,
                "created_at": "2026-07-10T00:00:00Z",
            }
        )
        samples["omics-metadata-check.schema.json"].update(
            {
                "schema_version": "2.0",
                "checked_at": "2026-07-10T00:00:00Z",
            }
        )

        self.assertEqual(
            set(samples),
            {path.name for path in (SKILL_ROOT / "contracts").glob("*.schema.json")},
        )

        for filename, sample in samples.items():
            with self.subTest(schema=filename):
                schema = load_json(SKILL_ROOT / "contracts" / filename)
                Draft202012Validator.check_schema(schema)
                Draft202012Validator(schema).validate(sample)


if __name__ == "__main__":
    unittest.main()
