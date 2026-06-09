import json
import importlib.util
import re
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
        manifest = load_json(SKILL_ROOT / "manifest.json")
        source_manifest = load_json(SKILL_ROOT / "source-manifest.json")
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertEqual(manifest["version"], version)
        self.assertEqual(manifest["adapter_version"], version)
        self.assertEqual(source_manifest["version"], version)
        self.assertIn(f'version: "{version}"', skill_text)

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

    def test_bundled_resources_are_advertised_by_router(self):
        source_manifest = load_json(SKILL_ROOT / "source-manifest.json")
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        for contract in source_manifest["contracts"]:
            self.assertIn(f"contracts/{contract}.json", skill_text)
        for template in source_manifest["templates"]:
            self.assertIn(f"templates/{template}.md", skill_text)
        for reference in source_manifest["references"]:
            self.assertIn(f"references/{reference}.md", skill_text)

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

    @unittest.skipUnless(importlib.util.find_spec("jsonschema"), "jsonschema is not installed")
    def test_v03_schema_samples_validate(self):
        from jsonschema import Draft202012Validator

        version = (SKILL_ROOT / "VERSION").read_text(encoding="utf-8").strip()
        samples = {
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
                    }
                ],
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
        }

        for filename, sample in samples.items():
            with self.subTest(schema=filename):
                schema = load_json(SKILL_ROOT / "contracts" / filename)
                Draft202012Validator.check_schema(schema)
                Draft202012Validator(schema).validate(sample)


if __name__ == "__main__":
    unittest.main()
