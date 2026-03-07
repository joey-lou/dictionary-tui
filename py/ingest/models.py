"""Shared data models for dictionary pack ingest scripts.

Every ``entries.jsonl`` line is a **head** entry — one per
(headword, pronunciation, part_of_speech) tuple. Multi-word/multi-char
entries are stored as ``PhraseItem`` objects inside the head's ``phrases``
list and never appear as top-level rows.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class PackManifest:
    """Dictionary pack metadata written to ``manifest.json``."""

    id: str
    name: str
    language: str
    sort: str
    entry_count: int
    data_file: str = "entries.jsonl"
    license: str | None = None
    source_url: str | None = None


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
    pronunciation: str | None
    part_of_speech: str | None
    short_definition: str | None
    full_definition: str | None
    phrases: tuple[PhraseItem, ...] = field(default_factory=tuple)
