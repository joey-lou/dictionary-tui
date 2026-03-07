#!/usr/bin/env python3
"""Build a Chinese–English dictionary pack from CC-CEDICT.

Unified structure: single-character entries become heads; multi-character
entries become phrases grouped under the leading character.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ingest.io_utils import write_pack
from ingest.models import PackManifest
from ingest.sources.cedict import DEFAULT_CEDICT_URL, download_source, parse_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-file",
        metavar="PATH",
        help="Use local CEDICT file instead of downloading (text or .gz).",
    )
    parser.add_argument(
        "--source-url",
        default=DEFAULT_CEDICT_URL,
        help="URL to CEDICT file (UTF-8 text or .gz); used if --source-file not set.",
    )
    parser.add_argument(
        "--cache-file",
        default=".cache/cedict/cedict_1_0_ts_utf-8_mdbg.txt.gz",
        help="Path to downloaded CEDICT cache.",
    )
    parser.add_argument(
        "--output-dir",
        default="packs/cc-cedict",
        help="Output pack directory.",
    )
    parser.add_argument(
        "--traditional",
        action="store_true",
        help="Use traditional Chinese as headword (default: simplified).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cache_path = Path(args.cache_file)
    output_dir = Path(args.output_dir)

    if args.source_file:
        source_path = Path(args.source_file)
        if not source_path.exists():
            raise SystemExit(f"Source file not found: {source_path}")
    else:
        source_path = download_source(args.source_url, cache_path)
        head = source_path.read_bytes()[:200]
        if head.startswith(b"<!") or head.startswith(b"<html"):
            source_path.unlink(missing_ok=True)
            raise SystemExit(
                "Download returned HTML (URL may be broken or require a browser). "
                "Download CEDICT manually from https://cc-cedict.org/wiki/start or "
                "https://www.mdbg.net/chinese/dictionary?page=cc-cedict and run:\n"
                "  python3 scripts/ingest_cedict.py --source-file /path/to/cedict_*.txt.gz"
            )

    entries = parse_file(source_path, use_simplified=not args.traditional)
    if not entries:
        raise SystemExit("No entries parsed from CEDICT source.")

    manifest = PackManifest(
        id="cc-cedict",
        name="CC-CEDICT (中英)",
        language="zh",
        sort="pinyin",
        entry_count=len(entries),
        license="CC BY-SA 4.0",
        source_url=args.source_url,
    )
    count = write_pack(output_dir, manifest, entries)
    print(f"Wrote {count} entries to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
