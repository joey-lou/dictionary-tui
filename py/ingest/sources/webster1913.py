"""Webster's Unabridged 1913 Dictionary from Project Gutenberg.

Parses the plain-text Gutenberg edition (ebook #29765) into structured
``HeadEntry`` objects with headword, pronunciation, part of speech,
and definitions.
"""

from __future__ import annotations

import re
import urllib.request
from pathlib import Path

from ..models import HeadEntry

_GUTENBERG_URL = "https://www.gutenberg.org/cache/epub/29765/pg29765.txt"
_SHORT_DEF_MAX = 80

# POS tokens found in first line of an entry body.
_POS_MAP: dict[str, str] = {
    "n.": "noun",
    "a.": "adj.",
    "v. t.": "v.t.",
    "v. i.": "v.i.",
    "v. t. & i.": "v.",
    "v.": "v.",
    "adv.": "adv.",
    "prep.": "prep.",
    "conj.": "conj.",
    "interj.": "interj.",
    "pron.": "pron.",
    "p. p.": "p.p.",
    "p. a.": "p.a.",
    "imp.": "imp.",
    "pl.": "pl.",
    "superl.": "superl.",
}

# Regex: POS token appearing after the pronunciation+comma on the first line.
_POS_RE = re.compile(
    r",\s+((?:" + "|".join(re.escape(k) for k in sorted(_POS_MAP, key=len, reverse=True)) + r"))",
)

# Entry headword line: all uppercase (letters, hyphens, apostrophes, spaces).
_HEADWORD_RE = re.compile(r"^([A-Z][A-Z\-' ]{0,60})$", re.MULTILINE)

# Pronunciation is the first token on the body's first line, before the comma.
_PRON_RE = re.compile(r"^([A-Za-z*\"\-`']+(?:\s*\([^)]*\))?)\s*,")

# Definition line starting with "Defn:" or a number.
_DEF_LINE_RE = re.compile(r"(?:^|\n)\s*(?:Defn:\s*|(\d+)\.\s*)")


def _strip_etymology(text: str) -> str:
    """Remove ``Etym: [...]`` blocks without crossing paragraph boundaries."""
    result = text
    while True:
        idx = result.find("Etym: [")
        if idx < 0:
            break
        # Find matching ']' without crossing a blank line.
        depth = 0
        end = None
        for i in range(idx + 6, min(idx + 1000, len(result))):
            if result[i] == "[":
                depth += 1
            elif result[i] == "]":
                if depth == 1:
                    end = i + 1
                    # Skip trailing period.
                    if end < len(result) and result[end] == ".":
                        end += 1
                    break
                depth -= 1
            elif result[i : i + 2] == "\n\n":
                break  # paragraph boundary — stop
        if end is None:
            # Malformed: remove just "Etym: " and the unclosed bracket text up to newline.
            line_end = result.find("\n", idx)
            if line_end < 0:
                line_end = len(result)
            result = result[:idx] + result[line_end:]
        else:
            result = result[:idx] + result[end:]
    return result


# Diacritical pronunciation → readable form.
_STRESS_CHARS = re.compile(r'["`*]')


def download_source(cache_dir: Path) -> Path:
    """Download the Gutenberg text if not already cached."""
    path = cache_dir / "pg29765.txt"
    if not path.exists():
        cache_dir.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(_GUTENBERG_URL, path)
    return path


_PAREN_CRUFT_RE = re.compile(r"\s*\([^)]*\)\s*$")


def _clean_pronunciation(raw: str) -> str:
    """Convert Webster diacritical pronunciation to a readable string.

    ``Ab"stract`` → ``Ab·stract``, ``Dic"tion*a*ry`` → ``Dic·tion·a·ry``
    """
    s = raw.strip().rstrip(",").strip()
    # Remove trailing parenthetical like "(#; 277)" or "(115)"
    s = _PAREN_CRUFT_RE.sub("", s)
    s = s.replace("*", "\u00b7")  # middle dot for syllable breaks
    s = s.replace('"', "\u02c8")  # modifier letter turned comma = primary stress
    return s.replace("`", "")


_DEFN_CRUFT_RE = re.compile(r"^(?:Defn:\s*)+")


def _extract_first_definition(body: str) -> str:
    """Pull the first definition text from the entry body."""
    cleaned = _strip_etymology(body)

    # Look for "Defn:" or numbered definition "1."
    m = _DEF_LINE_RE.search(cleaned)
    if m:
        rest = cleaned[m.end() :].strip()
    else:
        lines = cleaned.split("\n")
        rest = " ".join(lines[1:]).strip() if len(lines) > 1 else cleaned

    rest = " ".join(rest.split())
    # Cut at next definition number or Note:/Syn: markers.
    rest = re.split(r"\s+(?:\d+\.\s|Note:|Syn\.\s|--)", rest)[0]
    return _DEFN_CRUFT_RE.sub("", rest).strip().rstrip(".")


def _short(text: str) -> str:
    if len(text) <= _SHORT_DEF_MAX:
        return text
    return text[: _SHORT_DEF_MAX - 1].rstrip() + "\u2026"


def parse_webster(source_path: Path) -> list[HeadEntry]:
    """Parse the Gutenberg Webster 1913 text into ``HeadEntry`` list."""
    text = source_path.read_text(encoding="utf-8")

    # Find dictionary content boundaries.
    body_start = text.find("\nA\n")
    body_end = text.rfind("End of the Project Gutenberg")
    if body_end < 0:
        body_end = text.rfind("*** END OF THE PROJECT GUTENBERG")
    if body_end < 0:
        body_end = len(text)
    content = text[body_start:body_end]

    # Split into entries by headword lines.
    matches = list(_HEADWORD_RE.finditer(content))
    entries: list[HeadEntry] = []

    for i, m in enumerate(matches):
        headword_raw = m.group(1).strip()
        # Skip prefix entries like "A-", "AB-"
        if headword_raw.endswith("-") or len(headword_raw) == 0:
            continue

        body_start_idx = m.end()
        body_end_idx = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        body = content[body_start_idx:body_end_idx].strip()
        if not body:
            continue

        first_line = body.split("\n")[0].strip()
        if not first_line:
            continue

        # Extract pronunciation.
        pron_match = _PRON_RE.match(first_line)
        pron = _clean_pronunciation(pron_match.group(1)) if pron_match else None

        # Extract POS.
        pos_match = _POS_RE.search(first_line)
        pos_raw = pos_match.group(1) if pos_match else None
        pos = _POS_MAP.get(pos_raw, pos_raw) if pos_raw else None

        # Extract definition.
        full_def = _extract_first_definition(body)
        short_def = _short(full_def) if full_def else None

        # Title-case the headword.
        headword = headword_raw.title().replace("'S", "'s")

        entries.append(
            HeadEntry(
                headword=headword,
                sort_key=headword.lower(),
                leading_key=headword,
                pronunciation=pron,
                part_of_speech=pos,
                short_definition=short_def,
                full_definition=full_def,
            )
        )

    return entries
