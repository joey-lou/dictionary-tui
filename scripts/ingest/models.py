"""Shared data models for dictionary pack ingest scripts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

# (form, definition) for a phrase under a head entry; matches Rust PhraseItem.
PhraseItem = tuple[str, str]


@dataclass(frozen=True, slots=True)
class PackManifest:
    """Dictionary pack metadata written to ``manifest.json``."""

    id: str
    name: str
    language: str
    sort: str
    entry_count: int
    data_file: str
    license: Optional[str] = None
    source_url: Optional[str] = None


@dataclass(frozen=True, slots=True)
class DetailEntry:
    """Entry payload for ``entries.jsonl`` compatible with the Rust schema."""

    headword: str
    sort_key: str
    pronunciation: Optional[str]
    short_definition: Optional[str]
    full_definition: Optional[str]
    part_of_speech: Optional[str] = None  # e.g. "noun", "verb", "adj", "adv"
    leading_key: Optional[str] = None  # index key: EN = first word, ZH = first character
    is_phrase: Optional[bool] = None  # true = phrase/词语; only heads written to pack, phrases in .phrases
    phrases: Optional[Sequence[PhraseItem]] = None  # phrases under this head (form, definition); only on head entries
