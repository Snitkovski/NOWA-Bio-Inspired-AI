# Split one documentation file into two language files

Repository root: `E:\git\NOWA-Cognitive`

For every path in your batch list:

1. Read the entire source file.
2. Write two complete files in the same directory:
   - `NAME.en.md` — the whole document in English
   - `NAME.ru.md` — the whole document in Russian
3. Delete the source `NAME.md` only after both new files exist and each contains the full document, not a summary.
4. Do not edit `README.md` at the repository root.
5. Do not edit any file whose name already ends with `.en.md` or `.ru.md`.
6. Do not edit `Docs/arxiv_NOWA_en.md` or `Docs/arxiv_NOWA_ru.md`.

## What “complete” means

- Every section, table, list, formula, and code block of the source appears in both outputs.
- Do not summarize, shorten, or replace the body with an abstract.
- Fenced code, commands, identifiers, numbers, file paths, and formulas stay verbatim.
- Prose is translated. Academic register. No emoji.
- If the source prose is already in the target language, keep that prose (you may remove only the bilingual banner described below). Do not rewrite technical content for style.

## One language per file

- `NAME.en.md` contains no Russian prose.
- `NAME.ru.md` contains no English prose, except identifiers, code, and the single cross-link line.
- If the source starts with a bilingual preface (Russian abstract and English abstract, or a bilingual status block with `<a id="ru">` and `<a id="en">`), keep only the matching language’s preface in each output, then the rest of the document in that language.
- Delete the bilingual machinery: language anchors, “Русский · English” navigation, and HTML comments such as `bilingual-abstract`.

## Header

English file, immediately after the first heading:

`Russian version: [NAME.ru.md](NAME.ru.md)`

Russian file, immediately after the first heading:

`English version: [NAME.en.md](NAME.en.md)`

Leave other markdown links unchanged. A later pass retargets them.

## Encoding

Write UTF-8. Use `\n` line endings.
