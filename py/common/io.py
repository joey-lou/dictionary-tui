"""Filesystem and serialization helpers for pack ingest."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from .models import HeadEntry, PackManifest, PhraseItem

# Pinyin sort: base letter + tone digit so a<b<c and, for same syllable, 1st<2nd<3rd<4th tone.
# ɡ (U+0261) → g. Used when manifest.sort == "pinyin".
_PINYIN_TONE_TO_SORT: dict[str, str] = {
    "ā": "a1",
    "á": "a2",
    "ǎ": "a3",
    "à": "a4",
    "ē": "e1",
    "é": "e2",
    "ě": "e3",
    "è": "e4",
    "ī": "i1",
    "í": "i2",
    "ǐ": "i3",
    "ì": "i4",
    "ō": "o1",
    "ó": "o2",
    "ǒ": "o3",
    "ò": "o4",
    "ū": "u1",
    "ú": "u2",
    "ǔ": "u3",
    "ù": "u4",
    "ǖ": "v1",
    "ǘ": "v2",
    "ǚ": "v3",
    "ǜ": "v4",
    "ü": "v5",
    "Ü": "v5",  # neutral
}
_PINYIN_SPECIAL = {"ɡ": "g"}  # U+0261 → ASCII g


def _pinyin_sort_key(s: str) -> str:
    """Normalized pinyin for sort: correct a<b<c and tone order (1st<2nd<3rd<4th)."""
    if not s:
        return s
    out: list[str] = []
    for c in s:
        if c in _PINYIN_TONE_TO_SORT:
            out.append(_PINYIN_TONE_TO_SORT[c])
        elif c in _PINYIN_SPECIAL:
            out.append(_PINYIN_SPECIAL[c])
        else:
            out.append(c)
    return "".join(out).lower()


def merge_phrases_into_heads(
    heads: Iterable[HeadEntry],
    phrases: Iterable[PhraseItem],
    leading_key_fn: callable,
) -> list[HeadEntry]:
    """Attach *phrases* to matching heads by ``leading_key_fn(phrase.form)``."""
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
    """Write manifest and entries.jsonl to output_dir; return entry count."""
    output_dir.mkdir(parents=True, exist_ok=True)
    entries_path = output_dir / manifest.data_file
    if manifest.sort == "pinyin":
        sorted_entries = sorted(
            entries,
            key=lambda e: (_pinyin_sort_key(e.sort_key), e.sort_key, e.headword),
        )
    else:
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
                payload["phrases"] = [{"form": p.form, "definition": p.definition} for p in entry.phrases]
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
