"""Generate a BibTeX-safe, MDPI-template-friendly bibliography.

Preferred mode:
    Extract only the entries cited in manuscript/main.tex from scopus.bib, strip
    problematic/unused fields (e.g. abstracts, URLs), and normalise text to ASCII
    so that BibTeX/pdfTeX can process it reliably.

Fallback mode (when scopus.bib is missing):
    Re-sanitise the existing manuscript/references.bib in-place (still filtered
    to cited keys).

Usage:
    ./.venv/bin/python scripts/make_mdpi_bib.py

Output:
    manuscript/references.bib
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN_TEX = ROOT / "manuscript" / "main.tex"
SCOPUS_BIB = ROOT / "scopus.bib"
OUT_BIB = ROOT / "manuscript" / "references.bib"


STRIP_FIELDS = {
    "abstract",
    "keywords",
    "author_keywords",
    "url",  # contains %2f etc in Scopus exports; breaks BibTeX
    "note",  # often contains © and long boilerplate
    "funding",
    "funding-text",
    "publisher",
    "language",
    "document_type",
    "source",
    "ref",
    "references",
    "art_number",
    "eid",
    "pii",
    "scopus",
    "affiliation",
    "correspondence_address",
    "editor",
    "isbn",
    "issn",
    "coden",
    "chemicals",
    "tradenames",
    "manufacturer",
    "sponsor",
    "conference",
}

FIELD_START_RE = re.compile(r"^\s*([A-Za-z][A-Za-z0-9_\-]*)\s*=\s*\{", re.ASCII)


def to_ascii_latex(line: str) -> str:
    line = (
        line.replace("–", "--")
        .replace("—", "--")
        .replace("−", "-")
        .replace("…", "...")
        .replace("“", '"')
        .replace("”", '"')
        .replace("’", "'")
        .replace("‘", "'")
        .replace("©", "(c)")
    )

    # Strip diacritics: UTF-8 → ASCII
    line = unicodedata.normalize("NFKD", line)
    line = "".join(ch for ch in line if not unicodedata.combining(ch))
    line = line.encode("ascii", errors="ignore").decode("ascii", errors="ignore")

    # A few LaTeX specials should be escaped in BibTeX values.
    # Keep it conservative; we already strip URL/abstract fields.
    line = line.replace("&", r"\\&")
    line = line.replace("%", r"\\%")

    return line


def extract_citekeys(tex: str) -> set[str]:
    # Remove LaTeX comments so template examples don't get picked up as citations.
    # Keep literal \% intact.
    tex = re.sub(r"(?m)(?<!\\\\)%.*$", "", tex)
    keys: set[str] = set()
    for m in re.finditer(r"\\cite\w*\s*\{([^}]*)\}", tex):
        for k in m.group(1).split(","):
            k = k.strip()
            if k:
                keys.add(k)
    return keys


def parse_bib_entries(lines: list[str]) -> dict[str, list[str]]:
    entries: dict[str, list[str]] = {}
    i = 0
    while i < len(lines):
        if lines[i].lstrip().startswith("@"):  # @article{Key,
            start = i
            depth = 0
            while i < len(lines):
                depth += lines[i].count("{") - lines[i].count("}")
                if depth == 0:
                    break
                i += 1
            block = lines[start : i + 1]
            m = re.match(r"\s*@\w+\s*\{\s*([^,\s]+)\s*,", block[0])
            if m:
                entries[m.group(1)] = block
        i += 1
    return entries


def strip_fields_and_normalise(block: list[str]) -> str:
    new_lines: list[str] = []
    skipping = False
    skip_depth = 0

    for idx, raw_line in enumerate(block):
        if idx == 0:
            new_lines.append(to_ascii_latex(raw_line))
            continue

        line = raw_line

        if skipping:
            skip_depth += line.count("{") - line.count("}")
            if skip_depth <= 0 and ("}," in line or line.strip().endswith("}")):
                skipping = False
                skip_depth = 0
            continue

        m = FIELD_START_RE.match(line)
        if m and m.group(1).lower() in STRIP_FIELDS:
            skipping = True
            skip_depth = line.count("{") - line.count("}")
            if skip_depth <= 0 and ("}," in line or line.strip().endswith("}")):
                skipping = False
                skip_depth = 0
            continue

        new_lines.append(to_ascii_latex(line))

    return "\n".join(new_lines)


def main() -> None:
    tex = MAIN_TEX.read_text(encoding="utf-8", errors="replace")
    citekeys = extract_citekeys(tex)

    if SCOPUS_BIB.exists():
        source_bib = SCOPUS_BIB
    elif OUT_BIB.exists():
        source_bib = OUT_BIB
    else:
        raise SystemExit(
            "No bibliography source found. Expected scopus.bib (preferred) or manuscript/references.bib (fallback)."
        )

    bib_lines = source_bib.read_text(encoding="utf-8", errors="replace").splitlines()
    entries = parse_bib_entries(bib_lines)

    missing = sorted(citekeys - set(entries))
    if missing:
        missing_str = ", ".join(missing)
        raise SystemExit(f"Missing citekeys in {source_bib.name}: {missing_str}")

    blocks = []
    for key in sorted(citekeys):
        blocks.append(strip_fields_and_normalise(entries[key]))

    header_lines = [
        "% Auto-generated for MDPI template (BibTeX, ASCII, stripped fields when possible)",
        f"% Source: {source_bib.name}",
        "",
    ]
    header = "\n".join(to_ascii_latex(l) for l in header_lines)
    out = header + "\n\n".join(blocks) + "\n"

    # Ensure output is BibTeX-friendly ASCII.
    out.encode("ascii", errors="strict")

    OUT_BIB.write_text(out, encoding="ascii")
    print(f"Wrote {OUT_BIB.relative_to(ROOT)} with {len(blocks)} entries (source: {source_bib.name})")


if __name__ == "__main__":
    main()
