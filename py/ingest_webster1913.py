#!/usr/bin/env python3
"""Build EN dictionary pack from Webster's Unabridged 1913 (Project Gutenberg #29765).

Output: manifest.json + entries.jsonl under --out (default packs/webster1913-en/).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ingest.io_utils import write_pack
from ingest.models import PackManifest
from ingest.sources.webster1913 import download_source, parse_webster


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default="packs/webster1913-en",
        help="Output pack directory (default: packs/webster1913-en).",
    )
    parser.add_argument(
        "--cache-dir",
        default=".cache/webster1913",
        help="Directory for downloaded source text.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out)
    cache_dir = Path(args.cache_dir)

    source = download_source(cache_dir)
    entries = parse_webster(source)
    if not entries:
        raise SystemExit("No entries produced from Webster 1913 data.")

    manifest = PackManifest(
        id="webster1913-en",
        name="Webster's 1913",
        language="en",
        sort="alphabetical",
        entry_count=len(entries),
        license="Public Domain",
        source_url="https://www.gutenberg.org/ebooks/29765",
    )
    count = write_pack(out_dir, manifest, entries)
    print(f"Wrote {count} entries to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
