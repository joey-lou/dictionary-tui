"""Webster 1913 source download + parse helpers."""

from __future__ import annotations

import re
import urllib.request
from pathlib import Path

from ..models import DetailEntry

DEFAULT_WEBSTER_URL = "https://www.gutenberg.org/cache/epub/660/pg660.txt"

_NON_ALPHA_RE = re.compile(r"[^a-z0-9]+")
_HEADWORD_PATTERNS = [
    re.compile(r"^\|\|(?P<head>[A-Za-z][A-Za-z' -]{0,48})(?:\s|\(|,|\.|;|$)"),
    re.compile(r'^(?P<head>[A-Za-z][A-Za-z\' -]{0,48})(?:\s*\(|,\s|\. [A-Z]|;|:|\d+\.)'),
]


def download_source(url: str, target_file: Path) -> Path:
    """Download source text to ``target_file`` if missing."""
    target_file.parent.mkdir(parents=True, exist_ok=True)
    if target_file.exists():
        return target_file
    with urllib.request.urlopen(url, timeout=60) as response:
        body = response.read()
    target_file.write_bytes(body)
    return target_file


def parse_entries(source_text: str, max_entries: int | None = None) -> list[DetailEntry]:
    """Parse Gutenberg plain text into dictionary entries."""
    lines = [line.rstrip("\n") for line in source_text.splitlines()]
    entries: list[DetailEntry] = []
    seen_headwords: set[str] = set()
    for paragraph in _iter_body_paragraphs(lines):
        entry = _entry_from_paragraph(paragraph)
        if entry is None:
            continue
        key = entry.headword.lower()
        if key in seen_headwords:
            continue
        seen_headwords.add(key)
        entries.append(entry)
        if max_entries is not None and len(entries) >= max_entries:
            break
    return entries


def parse_file(path: Path, max_entries: int | None = None) -> list[DetailEntry]:
    """Read and parse entries from ``path``."""
    return parse_entries(path.read_text(encoding="utf-8", errors="ignore"), max_entries=max_entries)


def _iter_body_paragraphs(lines: list[str]) -> list[str]:
    in_body = False
    paragraph_lines: list[str] = []
    paragraphs: list[str] = []
    for raw_line in lines:
        line = raw_line.strip()
        if not in_body:
            if line.startswith("*** START OF THE PROJECT GUTENBERG EBOOK"):
                in_body = True
            continue
        if line.startswith("*** END OF THE PROJECT GUTENBERG EBOOK"):
            break
        if not line:
            if paragraph_lines:
                paragraphs.append(" ".join(paragraph_lines))
                paragraph_lines = []
            continue
        paragraph_lines.append(line)
    if paragraph_lines:
        paragraphs.append(" ".join(paragraph_lines))
    return paragraphs


def _entry_from_paragraph(paragraph: str) -> DetailEntry | None:
    if "PROJECT GUTENBERG" in paragraph:
        return None
    if paragraph.startswith("Begin file"):
        return None
    headword = _extract_headword(paragraph)
    if not headword:
        return None

    definition = paragraph[len(headword) :].lstrip(" .,:;-)(").strip()
    if not definition or len(definition) < 12:
        return None
    definition = definition.replace("Defn:", "").strip()
    short = _first_sentence(definition)
    if len(short) < 8:
        return None
    return DetailEntry(
        headword=headword,
        sort_key=_build_sort_key(headword),
        pronunciation=None,
        short_definition=short,
        full_definition=definition,
    )


def _extract_headword(paragraph: str) -> str:
    for pattern in _HEADWORD_PATTERNS:
        match = pattern.match(paragraph)
        if not match:
            continue
        headword = re.sub(r"\s+", " ", match.group("head")).strip(" -")
        if _is_valid_headword(headword):
            return headword.title()
    return ""


def _is_valid_headword(headword: str) -> bool:
    if not headword:
        return False
    words = headword.split()
    if len(words) > 4:
        return False
    return all(word and word[0].isalpha() for word in words)


def _first_sentence(text: str, max_len: int = 140) -> str:
    idx = text.find(".")
    if 0 < idx <= max_len:
        return text[: idx + 1]
    return text[:max_len].rstrip()


def _build_sort_key(headword: str) -> str:
    normalized = _NON_ALPHA_RE.sub(" ", headword.lower()).strip()
    return normalized
