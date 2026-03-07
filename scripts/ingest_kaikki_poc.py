#!/usr/bin/env python3
"""Build POC dictionary packs from Kaikki/Wiktextract for EN, Chinese→English, and Chinese→Chinese.

Variants:
  en       — English (Wiktionary); headwords and definitions in English.
  zh-en    — Chinese → English (enwiktionary Chinese); headwords in Chinese, definitions in English.
  zh-zh    — Chinese → Chinese (zhwiktionary zh-extract); headwords and definitions in Chinese.

Streams from Kaikki URLs by default; use --source-file for a local JSONL/.gz file.

Run from project root: python3 scripts/ingest_kaikki_poc.py en
Or from scripts/:     python3 ingest_kaikki_poc.py zh-zh --max-entries 2000
"""

from __future__ import annotations

import argparse
import sys
import gzip
import io
import urllib.request
from pathlib import Path

from ingest.io_utils import collapse_phrases_into_heads, write_pack
from ingest.models import PackManifest
from ingest.sources.kaikki import _stream_entries_from_lines

# Kaikki raw/postprocessed JSONL (plain or gzip).
KAIKKI_EN_URL = "https://kaikki.org/dictionary/English/kaikki.org-dictionary-English.jsonl"
KAIKKI_ZH_EN_URL = "https://kaikki.org/dictionary/Chinese/kaikki.org-dictionary-Chinese.jsonl"
KAIKKI_ZH_ZH_URL = "https://kaikki.org/dictionary/downloads/zh/zh-extract.jsonl.gz"

VARIANT_CONFIG = {
    "en": {
        "lang_code": "en",
        "language": "en",
        "pack_id": "kaikki-en-poc",
        "pack_name": "English (Wiktionary) POC",
        "sort": "alphabetical",
        "default_url": KAIKKI_EN_URL,
        "gzip": False,
    },
    "zh-en": {
        "lang_code": "zh",
        "language": "zh",
        "pack_id": "kaikki-zh-en-poc",
        "pack_name": "Chinese → English (Wiktionary) POC",
        "sort": "alphabetical",
        "default_url": KAIKKI_ZH_EN_URL,
        "gzip": False,
    },
    "zh-zh": {
        "lang_code": "zh",
        "language": "zh",
        "pack_id": "kaikki-zh-zh-poc",
        "pack_name": "Chinese → Chinese (zhwiktionary) POC",
        "sort": "alphabetical",
        "default_url": KAIKKI_ZH_ZH_URL,
        "gzip": True,
    },
}


def _stream_lines_from_url(url: str, gzipped: bool = False, encoding: str = "utf-8"):
    """Stream text lines from URL; decompress gzip if requested."""
    with urllib.request.urlopen(url, timeout=60) as resp:
        if not gzipped:
            buffer = b""
            for chunk in iter(lambda: resp.read(1 << 16), b""):
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    yield line.decode(encoding, errors="replace").strip()
            if buffer.strip():
                yield buffer.decode(encoding, errors="replace").strip()
            return
        with gzip.GzipFile(fileobj=resp, mode="rb") as gz:
            with io.TextIOWrapper(gz, encoding=encoding, errors="replace") as text:
                for line in text:
                    line = line.rstrip("\n\r")
                    if line.strip():
                        yield line


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "variant",
        choices=list(VARIANT_CONFIG),
        help="Pack variant: en, zh-en, or zh-zh.",
    )
    parser.add_argument(
        "--source-file",
        metavar="PATH",
        help="Local JSONL or .jsonl.gz path. If omitted, stream from default URL.",
    )
    parser.add_argument(
        "--source-url",
        help="Override URL when not using --source-file.",
    )
    parser.add_argument(
        "--output-dir",
        help="Output pack directory (default: packs/<pack_id>).",
    )
    parser.add_argument(
        "--max-entries",
        type=int,
        default=3000,
        metavar="N",
        help="Max entries to ingest (default: 3000).",
    )
    return parser.parse_args()


def main() -> int:
    # Allow running from project root (scripts/ingest_kaikki_poc.py) or scripts/ (ingest_kaikki_poc.py).
    scripts_dir = Path(__file__).resolve().parent
    if scripts_dir.name == "scripts" and str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    args = parse_args()
    cfg = VARIANT_CONFIG[args.variant]
    lang_code = cfg["lang_code"]
    pack_id = cfg["pack_id"]
    output_dir = Path(args.output_dir or f"packs/{pack_id}")

    if args.source_file:
        source_path = Path(args.source_file)
        if not source_path.exists():
            raise SystemExit(f"Source file not found: {source_path}")
        from ingest.sources.kaikki import stream_kaikki_entries

        entries = list(
            stream_kaikki_entries(
                source_path,
                lang_code=lang_code,
                max_entries=args.max_entries,
            )
        )
    else:
        url = args.source_url or cfg["default_url"]
        gzipped = cfg.get("gzip", False)
        print(f"Streaming from {url} (first {args.max_entries} entries, gzip={gzipped})...")
        lines = _stream_lines_from_url(url, gzipped=gzipped)
        entries = list(
            _stream_entries_from_lines(
                lines,
                lang_code=lang_code,
                max_entries=args.max_entries,
            )
        )

    if not entries:
        raise SystemExit("No entries parsed. Check source and --variant.")

    # Index = single word/字 only; collapse phrase entries under head's phrases[].
    entries = collapse_phrases_into_heads(entries)

    manifest = PackManifest(
        id=pack_id,
        name=cfg["pack_name"],
        language=cfg["language"],
        sort=cfg["sort"],
        entry_count=len(entries),
        data_file="entries.jsonl",
        license="CC BY-SA 3.0",
        source_url="https://kaikki.org/dictionary/",
    )
    count = write_pack(output_dir, manifest, entries)
    print(f"Wrote {count} entries to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
