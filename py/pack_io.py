"""Write dictionary pack: manifest.json + entries.jsonl."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .schema import HeadEntry, PackManifest


def write_pack(
    out_dir: Path,
    manifest: PackManifest,
    entries: Iterable[HeadEntry],
) -> int:
    """Write manifest and entries.jsonl; sort by (leading_key, sort_key). Returns entry count."""
    out_dir.mkdir(parents=True, exist_ok=True)
    sorted_entries = sorted(
        entries,
        key=lambda e: (e.leading_key, e.sort_key),
    )

    path = out_dir / manifest.data_file
    with path.open("w", encoding="utf-8") as f:
        for e in sorted_entries:
            payload = {
                "headword": e.headword,
                "sort_key": e.sort_key,
                "leading_key": e.leading_key,
                "pronunciation": e.pronunciation,
                "short_definition": e.short_definition,
                "full_definition": e.full_definition,
                "part_of_speech": e.part_of_speech,
            }
            if e.phrases:
                payload["phrases"] = [{"form": p.form, "definition": p.definition} for p in e.phrases]
            f.write(json.dumps(payload, ensure_ascii=False))
            f.write("\n")

    manifest_path = out_dir / "manifest.json"
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
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest_payload, f, ensure_ascii=False, indent=2)
        f.write("\n")

    return len(sorted_entries)
