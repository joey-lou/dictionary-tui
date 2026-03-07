"""Filesystem and serialization helpers for pack ingest."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List

from .models import DetailEntry, PackManifest, PhraseItem


def collapse_phrases_into_heads(entries: Iterable[DetailEntry]) -> List[DetailEntry]:
    """
    Keep only head entries (is_phrase=False); attach phrase entries (is_phrase=True)
    to the matching head's `phrases` list. Index = single word/字 only; phrases
    are nested under the head, not separate lines.
    """
    heads: List[DetailEntry] = []
    phrase_list: List[DetailEntry] = []
    for e in entries:
        if getattr(e, "is_phrase", False):
            phrase_list.append(e)
        else:
            heads.append(e)

    key = lambda e: (_leading_key(e) or "", getattr(e, "part_of_speech") or "")
    phrase_by_key: dict[tuple[str, str], list[DetailEntry]] = {}
    for p in phrase_list:
        k = key(p)
        phrase_by_key.setdefault(k, []).append(p)

    out: List[DetailEntry] = []
    for h in heads:
        k = key(h)
        matching = phrase_by_key.get(k, [])
        phrase_items: List[PhraseItem] = [
            (p.headword, (p.short_definition or p.full_definition or "").strip())
            for p in matching
        ]
        new_entry = DetailEntry(
            headword=h.headword,
            sort_key=h.sort_key,
            pronunciation=h.pronunciation,
            short_definition=h.short_definition,
            full_definition=h.full_definition,
            part_of_speech=h.part_of_speech,
            leading_key=getattr(h, "leading_key", None),
            is_phrase=False,
            phrases=tuple(phrase_items) if phrase_items else None,
        )
        out.append(new_entry)
    return out


def _leading_key(entry: DetailEntry) -> str:
    """First token of sort_key for prefix-tree grouping (word-level)."""
    return (
        getattr(entry, "leading_key", None)
        or (entry.sort_key.split()[0] if entry.sort_key.strip() else "")
    )


def write_pack(output_dir: Path, manifest: PackManifest, entries: Iterable[DetailEntry]) -> int:
    """Write a complete pack to ``output_dir`` and return entry count. Sorts by (leading_key, sort_key) for prefix-tree grouping."""
    output_dir.mkdir(parents=True, exist_ok=True)
    entries_path = output_dir / manifest.data_file
    sorted_entries = sorted(
        entries,
        key=lambda e: (_leading_key(e), e.sort_key),
    )

    with entries_path.open("w", encoding="utf-8") as fp:
        for entry in sorted_entries:
            lead = _leading_key(entry)
            payload = {
                "headword": entry.headword,
                "sort_key": entry.sort_key,
                "pronunciation": entry.pronunciation,
                "short_definition": entry.short_definition,
                "full_definition": entry.full_definition,
            }
            if lead:
                payload["leading_key"] = lead
            if getattr(entry, "is_phrase", None) is not None:
                payload["is_phrase"] = entry.is_phrase
            if getattr(entry, "part_of_speech", None) is not None:
                payload["part_of_speech"] = entry.part_of_speech
            phrases = getattr(entry, "phrases", None)
            if phrases:
                payload["phrases"] = [{"form": f, "definition": d} for f, d in phrases]
            fp.write(json.dumps(payload, ensure_ascii=False))
            fp.write("\n")

    manifest_payload = {
        "id": manifest.id,
        "name": manifest.name,
        "language": manifest.language,
        "sort": manifest.sort,
        "entry_count": len(sorted_entries),
        "data_file": manifest.data_file,
        "license": manifest.license,
        "source_url": manifest.source_url,
    }
    with (output_dir / "manifest.json").open("w", encoding="utf-8") as fp:
        json.dump(manifest_payload, fp, ensure_ascii=False, indent=2)
        fp.write("\n")

    return len(sorted_entries)
