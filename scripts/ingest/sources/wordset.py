"""Wordset dictionary source (StevensDeptECE/Dictionaries wordset-dictionary)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

from ..models import DetailEntry

SHORT_DEF_MAX_CHARS = 100
WORDSET_REPO_URL = "https://github.com/StevensDeptECE/Dictionaries.git"

# Normalize speech_part to schema style (lowercase, common abbreviations).
POS_NORMALIZE: dict[str, str] = {
    "adjective": "adj",
    "adverb": "adv",
    "noun": "noun",
    "verb": "verb",
    "conjunction": "conj",
    "preposition": "prep",
    "interjection": "interj",
    "pronoun": "pron",
    "abbreviation": "abbr",
}


def _normalize_pos(speech_part: str | None) -> str:
    if not speech_part:
        return "n/a"
    key = speech_part.strip().lower()
    return POS_NORMALIZE.get(key, key)


def _is_single_word(word: str) -> bool:
    w = (word or "").strip()
    return bool(w) and " " not in w and w.isprintable()


def parse_wordset_file(path: Path) -> Iterator[DetailEntry]:
    """Parse one wordset data/*.json file; yield one DetailEntry per (word, part_of_speech)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    for raw_head, obj in data.items():
        if not isinstance(obj, dict):
            continue
        word = (obj.get("word") or raw_head or "").strip()
        if not _is_single_word(word):
            continue
        meanings = obj.get("meanings") or []
        if not meanings:
            continue
        # Group definitions by normalized POS
        by_pos: dict[str, list[str]] = {}
        for m in meanings:
            if not isinstance(m, dict):
                continue
            pos = _normalize_pos(m.get("speech_part"))
            defn = (m.get("def") or "").strip()
            if defn:
                by_pos.setdefault(pos, []).append(defn)
        for pos, defs in by_pos.items():
            short = defs[0]
            if len(short) > SHORT_DEF_MAX_CHARS:
                short = short[: SHORT_DEF_MAX_CHARS - 3].rstrip() + "..."
            full = "\n".join(f"{i + 1}. {d}" for i, d in enumerate(defs))
            yield DetailEntry(
                headword=word,
                sort_key=word.lower(),
                leading_key=word,
                pronunciation=None,
                short_definition=short or None,
                full_definition=full or None,
                part_of_speech=pos,
                is_phrase=False,
                phrases=None,
            )


def iter_wordset_data(data_dir: Path, exclude_misc: bool = True) -> Iterator[DetailEntry]:
    """Iterate all data/*.json in data_dir (excluding misc.json if exclude_misc)."""
    for path in sorted(data_dir.glob("*.json")):
        if exclude_misc and path.name.lower() == "misc.json":
            continue
        yield from parse_wordset_file(path)
