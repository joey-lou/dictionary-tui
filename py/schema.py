"""Output schema for dictionary packs: one line per head, optional phrases."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence


@dataclass(frozen=True)
class PackManifest:
    id: str
    name: str
    language: str
    sort: str
    entry_count: int
    data_file: str = "entries.jsonl"
    license: Optional[str] = None
    source_url: Optional[str] = None


@dataclass(frozen=True)
class PhraseItem:
    form: str
    definition: str


@dataclass(frozen=True)
class HeadEntry:
    """One pack line: index head (single word EN / single char ZH) with optional phrases."""

    headword: str
    sort_key: str
    leading_key: str
    pronunciation: Optional[str]
    short_definition: Optional[str]
    full_definition: Optional[str]
    part_of_speech: Optional[str]
    phrases: Sequence[PhraseItem] = ()
