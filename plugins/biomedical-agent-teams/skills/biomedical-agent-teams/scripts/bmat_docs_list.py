#!/usr/bin/env python3
"""List BMAT markdown resources and optional routing metadata."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


RESOURCE_DIRS = ("commands", "references", "loops", "templates")
UTF8_BOM = "\ufeff"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="List BMAT markdown resources.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="BMAT skill root.",
    )
    return parser.parse_args()


def resolve_skill_root(root: Path) -> Path:
    root = root.resolve()
    candidates = [
        root,
        root / "skills" / "biomedical-agent-teams",
        root / "plugins" / "biomedical-agent-teams" / "skills" / "biomedical-agent-teams",
    ]
    for candidate in candidates:
        if (candidate / "SKILL.md").exists() and (candidate / "commands").is_dir():
            return candidate
    print(f"ERROR: could not resolve BMAT skill root from {root}", file=sys.stderr)
    raise SystemExit(2)


def strip_bom(text: str) -> str:
    return text[1:] if text.startswith(UTF8_BOM) else text


def read_markdown(path: Path) -> str:
    return strip_bom(path.read_text(encoding="utf-8-sig"))


def _first_heading(text: str) -> str:
    text = strip_bom(text)
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return ""


def _body_after_frontmatter(text: str) -> str:
    text = strip_bom(text)
    match = re.match(r"\A---\r?\n.*?\r?\n---[ \t]*(?:\r?\n|\Z)", text, re.S)
    if match:
        return text[match.end() :]
    return text


def _first_prose_sentence(text: str) -> str:
    body = _body_after_frontmatter(text)
    paragraph: list[str] = []
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line:
            if paragraph:
                break
            continue
        if line.startswith(("#", "|", "-", "`")):
            if paragraph:
                break
            continue
        paragraph.append(line)
    if paragraph:
        summary = " ".join(paragraph)
        if len(summary) > 180:
            return summary[:177].rstrip() + "..."
        return summary
    return ""


def fallback_summary(text: str, path: Path) -> str:
    heading = _first_heading(text)
    prose = _first_prose_sentence(text)
    if prose:
        return prose
    if heading:
        return f"{heading}."
    return f"{path.stem.replace('-', ' ').title()}."


def frontmatter(text: str) -> dict[str, list[str] | str]:
    text = strip_bom(text)
    match = re.match(r"\A---\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", text, re.S)
    if not match:
        return {}
    block = match.group(1)
    out: dict[str, list[str] | str] = {}
    summary = re.search(r"^summary:\s*['\"]?(.*?)['\"]?\s*$", block, re.M)
    description = re.search(r"^description:\s*['\"]?(.*?)['\"]?\s*$", block, re.M)
    if summary and summary.group(1).strip():
        out["summary"] = summary.group(1).strip()
    elif description and description.group(1).strip():
        out["summary"] = description.group(1).strip()
    read_when: list[str] = []
    collecting = False
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if line.startswith("read_when:"):
            collecting = True
            continue
        if collecting and line.startswith("- "):
            item = line[2:].strip().strip("'\"")
            if item:
                read_when.append(item)
        elif collecting and line and not line.startswith("- "):
            collecting = False
    if read_when:
        out["read_when"] = read_when
    return out


def main() -> int:
    args = parse_args()
    root = resolve_skill_root(args.root)
    print("# BMAT Markdown Resource Inventory")
    for folder in RESOURCE_DIRS:
        folder_path = root / folder
        if not folder_path.exists():
            continue
        print(f"\n## {folder.replace('-', ' ').title()}")
        for path in sorted(folder_path.glob("*.md")):
            text = read_markdown(path)
            meta = frontmatter(text)
            rel = path.relative_to(root)
            summary = meta.get("summary")
            if isinstance(summary, str):
                print(f"- `{rel}` - {summary}")
            else:
                print(f"- `{rel}` - {fallback_summary(text, path)}")
            read_when = meta.get("read_when")
            if isinstance(read_when, list) and read_when:
                print(f"  - Read when: {'; '.join(read_when)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
