"""Shared data models for dictionary pack ingest scripts.

Unified schema: every ``entries.jsonl`` line is a **head** entry (single word
for EN, single character for ZH).  Multi-word/multi-char entries are stored
as ``PhraseItem`` objects inside the head's ``phrases`` list and never appear
as top-level index rows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence


@dataclass(frozen=True, slots=True)
class PackManifest:
    """Dictionary pack metadata written to ``manifest.json``."""

    id: str
    name: str
    language: str
    sort: str
    entry_count: int
    data_file: str = "entries.jsonl"
    license: Optional[str] = None
    source_url: Optional[str] = None


@dataclass(frozen=True, slots=True)
class PhraseItem:
    """One phrase/idiom nested under a head entry."""

    form: str
    definition: str


@dataclass(frozen=True, slots=True)
class HeadEntry:
    """One index line in ``entries.jsonl``.

    Represents exactly one (headword, pronunciation, part_of_speech) tuple.
    Phrases and idioms are attached via ``phrases``, never as separate lines.
    """

    headword: str
    sort_key: str
    leading_key: str
    pronunciation: Optional[str]
    part_of_speech: Optional[str]
    short_definition: Optional[str]
    full_definition: Optional[str]
    phrases: tuple[PhraseItem, ...] = field(default_factory=tuple)
