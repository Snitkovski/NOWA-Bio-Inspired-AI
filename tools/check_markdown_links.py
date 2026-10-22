#!/usr/bin/env python3
"""Verify relative markdown link and image targets exist in the repo."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
SKIP_PREFIXES = ("http://", "https://", "mailto:", "#")

IGNORE_DIRS = {".git", "node_modules", "__pycache__", ".serena"}


def iter_markdown_files() -> list[Path]:
    out: list[Path] = []
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        if any(part in IGNORE_DIRS for part in p.parts):
            continue
        if p.suffix.lower() in (".md", ".mdc"):
            out.append(p)
    return sorted(out)


def resolve_target(source: Path, target: str) -> Path | None:
    target = target.strip()
    if not target or target.startswith(SKIP_PREFIXES):
        return None
    # Drop optional title in angle brackets
    if " " in target and not target.startswith("<"):
        target = target.split()[0]
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    path_part = unquote(target.split("#", 1)[0])
    if not path_part:
        return None
    resolved = (source.parent / path_part).resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError:
        return None
    return resolved


def should_check_file(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    prefixes = (
        "Docs/",
        "README.md",
        "AGENTS.md",
        "Demo/",
        ".cursor/",
        ".serena/",
        ".github/",
    )
    return any(rel == p.rstrip("/") or rel.startswith(p) for p in prefixes)


def main() -> int:
    missing: list[tuple[Path, str, Path]] = []
    checked = 0
    for md in iter_markdown_files():
        if not should_check_file(md):
            continue
        checked += 1
        text = md.read_text(encoding="utf-8", errors="replace")
        for match in LINK_RE.finditer(text):
            raw = match.group(1)
            resolved = resolve_target(md, raw)
            if resolved is None:
                continue
            if not resolved.exists():
                missing.append((md, raw, resolved))
    if missing:
        for src, raw, res in missing:
            rel_src = src.relative_to(ROOT)
            print(f"MISSING {rel_src}: ({raw}) -> {res.relative_to(ROOT)}")
        print(f"\n{len(missing)} broken relative link(s)")
        return 1
    print(f"OK: checked {checked} markdown files (docs migration scope)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
