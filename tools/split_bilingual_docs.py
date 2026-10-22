#!/usr/bin/env python3
"""One-off helper: split bilingual specs/QA into .en.md / .ru.md and fix Docs/ paths."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RU_MARKER = "# ЧАСТЬ II — РУССКИЙ"
QA_SPLIT = re.compile(r"^# QA ", re.MULTILINE)


def bilingual_title_parts(line: str) -> tuple[str, str]:
    if " / " in line:
        en, ru = line.split(" / ", 1)
        return en.strip(), ru.strip()
    return line.strip(), line.strip()


def fix_paths(text: str, lang: str) -> str:
    text = text.replace("Docs/", "Docs/")
    # Spec/QA bare .md links -> language suffix
    if lang == "en":
        text = re.sub(
            r"\(issue-13-two-tier-plasticity\)\.md\)",
            "(issue-13-two-tier-plasticity.en.md)",
            text,
        )
        text = re.sub(
            r"\(issue-13-demo-colony\)\.md\)",
            "(issue-13-demo-colony.en.md)",
            text,
        )
        text = re.sub(
            r"\(issue-13-demo-tamagochi\)\.md\)",
            "(issue-13-demo-tamagochi.en.md)",
            text,
        )
        text = re.sub(
            r"\(fix-colony-no-rest\)\.md\)",
            "(fix-colony-no-rest.en.md)",
            text,
        )
        text = re.sub(
            r"`([^`]+\.md)`",
            lambda m: (
                f"`{m.group(1).removesuffix('.md')}.en.md`"
                if "PR-" in m.group(1) or "issue-13" in m.group(1) or "fix-colony" in m.group(1)
                else m.group(0)
            ),
            text,
        )
        text = re.sub(
            r"\]\(([^)]*?)(issue-13-[a-z0-9-]+|fix-colony-no-rest)\.md\)",
            r"](\1\2.en.md)",
            text,
        )
        text = re.sub(
            r"\]\(([^)]*?)(PR-[0-9]+-[a-z0-9-]+)\.md\)",
            r"](\1\2.en.md)",
            text,
        )
    else:
        text = re.sub(
            r"\]\(([^)]*?)(issue-13-[a-z0-9-]+|fix-colony-no-rest)\.md\)",
            r"](\1\2.ru.md)",
            text,
        )
        text = re.sub(
            r"\]\(([^)]*?)(PR-[0-9]+-[a-z0-9-]+)\.md\)",
            r"](\1\2.ru.md)",
            text,
        )
        text = re.sub(
            r"`([^`]+\.md)`",
            lambda m: (
                f"`{m.group(1).removesuffix('.md')}.ru.md`"
                if "PR-" in m.group(1) or "issue-13" in m.group(1) or "fix-colony" in m.group(1)
                else m.group(0)
            ),
            text,
        )
    return text


def split_spec(path: Path) -> None:
    raw = path.read_text(encoding="utf-8")
    if RU_MARKER not in raw:
        raise SystemExit(f"No Russian marker in {path}")
    head, ru_body = raw.split(RU_MARKER, 1)
    ru_body = ru_body.lstrip("\n")
    lines = head.splitlines()
    title_line = lines[0] if lines else ""
    en_title, ru_title = bilingual_title_parts(title_line.lstrip("# ").strip())
    en_title = f"# {en_title}" if not en_title.startswith("#") else en_title

    # Intro between title and PART I
    intro: list[str] = []
    body_start = 0
    for i, line in enumerate(lines):
        if line.startswith("# PART I"):
            body_start = i + 1
            break
        if i > 0:
            intro.append(line)

    en_body_lines = lines[body_start:]
    # trim trailing --- before split
    while en_body_lines and en_body_lines[-1].strip() in ("", "---"):
        en_body_lines.pop()
    while en_body_lines and en_body_lines[-1].strip() == "---":
        en_body_lines.pop()

    en_intro = "\n".join(intro).strip()
    en_content = "\n".join(en_body_lines).strip()
    en_md = f"{en_title}\n\n"
    if en_intro:
        en_md += f"{en_intro}\n\n---\n\n"
    en_md += en_content + "\n"
    en_md = fix_paths(en_md, "en")

    ru_md = f"# {ru_title}\n\n{ru_body}\n"
    ru_md = fix_paths(ru_md, "ru")

    stem = path.stem
    path.with_name(f"{stem}.en.md").write_text(en_md, encoding="utf-8")
    path.with_name(f"{stem}.ru.md").write_text(ru_md, encoding="utf-8")
    path.unlink()


def split_qa_bilingual(path: Path) -> None:
    raw = path.read_text(encoding="utf-8")
    matches = list(QA_SPLIT.finditer(raw))
    if len(matches) < 2:
        raise SystemExit(f"Expected bilingual QA headers in {path}")
    split_at = matches[1].start()
    en_raw = raw[:split_at].rstrip() + "\n"
    ru_raw = raw[split_at:].lstrip()
    stem = path.stem
    path.with_name(f"{stem}.en.md").write_text(fix_paths(en_raw, "en"), encoding="utf-8")
    path.with_name(f"{stem}.ru.md").write_text(fix_paths(ru_raw, "ru"), encoding="utf-8")
    path.unlink()


def main() -> None:
    for p in sorted((ROOT / "Docs/specs").glob("*.md")):
        split_spec(p)
    bilingual_qa = [
        "PR-37-labile-layer-qa.md",
        "PR-40-sleep-consolidation-qa.md",
        "PR-42-colony-two-tier-qa.md",
        "PR-44-tamagochi-two-tier-qa.md",
    ]
    for name in bilingual_qa:
        split_qa_bilingual(ROOT / "Docs/qa" / name)


if __name__ == "__main__":
    main()
