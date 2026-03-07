#!/usr/bin/env python3
"""Build an English dictionary pack from Kaikki/Wiktextract (Wiktionary) JSONL.

Richer than WordNet: includes IPA pronunciation, multiple senses, and detailed definitions.
Without --source-file, streams from Kaikki's English JSONL (stops after --max-entries).
With --source-file, reads from a local .jsonl or .jsonl.gz (e.g. from
https://kaikki.org/dictionary/rawdata.html or https://kaikki.org/dictionary/English/).
"""

from __future__ import annotations

import argparse
import urllib.request
from pathlib import Path

from ingest.io_utils import collapse_phrases_into_heads, write_pack
from ingest.models import PackManifest
from ingest.sources.kaikki import stream_kaikki_entries, _stream_entries_from_lines

DEFAULT_KAIKKI_EN_URL = "https://kaikki.org/dictionary/English/kaikki.org-dictionary-English.jsonl"


def _stream_lines_from_url(url: str, encoding: str = "utf-8"):
    """Stream text lines from URL without loading the full response."""
    with urllib.request.urlopen(url, timeout=30) as resp:
        resp.read  # ensure we have a response
        buffer = b""
        for chunk in iter(lambda: resp.read(1 << 16), b""):
            buffer += chunk
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                yield line.decode(encoding, errors="replace").strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-file",
        metavar="PATH",
        help="Path to Kaikki/Wiktextract JSONL or .jsonl.gz. If omitted, stream from --source-url.",
    )
    parser.add_argument(
        "--source-url",
        default=DEFAULT_KAIKKI_EN_URL,
        help="URL of English JSONL when not using --source-file.",
    )
    parser.add_argument(
        "--output-dir",
        default="packs/kaikki-en",
        help="Output pack directory.",
    )
    parser.add_argument(
        "--max-entries",
        type=int,
        default=3000,
        metavar="N",
        help="Maximum entries (default: 3000).",
    )
    parser.add_argument(
        "--lang",
        default="en",
        help="Language code to filter (default: en).",
    )
    parser.add_argument(
        "--pack-id",
        default="kaikki-en",
        help="Pack id for manifest.",
    )
    parser.add_argument(
        "--pack-name",
        default="English (Wiktionary)",
        help="Display name for manifest.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.source_file:
        source_path = Path(args.source_file)
        if not source_path.exists():
            raise SystemExit(f"Source file not found: {source_path}")
        entries = list(
            stream_kaikki_entries(
                source_path,
                lang_code=args.lang,
                max_entries=args.max_entries,
            )
        )
    else:
        print(f"Streaming from {args.source_url} (first {args.max_entries} entries)...")
        lines = _stream_lines_from_url(args.source_url)
        entries = list(
            _stream_entries_from_lines(
                lines,
                lang_code=args.lang,
                max_entries=args.max_entries,
            )
        )

    if not entries:
        raise SystemExit("No entries parsed. Check --source-file/--source-url and --lang.")

    # Index = single word only; collapse phrase entries under head's phrases[].
    entries = collapse_phrases_into_heads(entries)

    manifest = PackManifest(
        id=args.pack_id,
        name=args.pack_name,
        language="en",
        sort="alphabetical",
        entry_count=len(entries),
        data_file="entries.jsonl",
        license="CC BY-SA 3.0",
        source_url="https://kaikki.org/dictionary/",
    )
    count = write_pack(Path(args.output_dir), manifest, entries)
    print(f"Wrote {count} entries to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
