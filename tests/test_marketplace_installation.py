from pathlib import Path
import json

REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = REPO_ROOT / "plugins/biomedical-agent-teams"

def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))

def test_marketplace_entry_resolves_versioned_plugin_metadata() -> None:
    marketplace = read_json(REPO_ROOT / ".agents" / "plugins" / "marketplace.json")
    entries = {entry["name"]: entry for entry in marketplace["plugins"]}
    entry = entries["biomedical-agent-teams"]

    assert entry["source"] == {
        "source": "local",
        "path": "./plugins/biomedical-agent-teams",
    }
    assert read_json(PLUGIN_ROOT / ".codex-plugin" / "plugin.json")["version"] == "1.2.1"

