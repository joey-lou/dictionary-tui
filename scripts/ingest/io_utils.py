"""Filesystem and serialization helpers for pack ingest."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from .models import HeadEntry, PackManifest, PhraseItem


def merge_phrases_into_heads(
    heads: Iterable[HeadEntry],
    phrases: Iterable[PhraseItem],
    leading_key_fn: callable,
) -> list[HeadEntry]:
    """Attach *phrases* to matching heads by ``leading_key_fn(phrase.form)``.

    ``leading_key_fn`` extracts the grouping key from a phrase form
    (e.g. first word for EN, first character for ZH).  Phrases whose
    leading key has no matching head are dropped.
    """
    from collections import defaultdict

    bucket: dict[str, list[PhraseItem]] = defaultdict(list)
    for p in phrases:
        bucket[leading_key_fn(p.form)].append(p)

    out: list[HeadEntry] = []
    for h in heads:
        matching = bucket.get(h.leading_key, ())
        merged_phrases = (*h.phrases, *matching) if matching else h.phrases
        if merged_phrases != h.phrases:
            h = HeadEntry(
                headword=h.headword,
                sort_key=h.sort_key,
                leading_key=h.leading_key,
                pronunciation=h.pronunciation,
                part_of_speech=h.part_of_speech,
                short_definition=h.short_definition,
                full_definition=h.full_definition,
                phrases=tuple(merged_phrases),
            )
        out.append(h)
    return out


def write_pack(
    output_dir: Path,
    manifest: PackManifest,
    entries: Iterable[HeadEntry],
) -> int:
    """Write a complete pack to *output_dir* and return entry count.

    Sorts by ``(leading_key, sort_key)`` for prefix-tree grouping.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    entries_path = output_dir / manifest.data_file
    sorted_entries = sorted(entries, key=lambda e: (e.leading_key, e.sort_key))

    with entries_path.open("w", encoding="utf-8") as fp:
        for entry in sorted_entries:
            payload: dict = {
                "headword": entry.headword,
                "sort_key": entry.sort_key,
                "leading_key": entry.leading_key,
                "pronunciation": entry.pronunciation,
                "short_definition": entry.short_definition,
                "full_definition": entry.full_definition,
            }
            if entry.part_of_speech is not None:
                payload["part_of_speech"] = entry.part_of_speech
            if entry.phrases:
                payload["phrases"] = [
                    {"form": p.form, "definition": p.definition}
                    for p in entry.phrases
                ]
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
