#!/usr/bin/env python3
"""Build a Webster 1913 pack from a direct downloadable source file."""

from __future__ import annotations

import argparse
from pathlib import Path

from ingest.io_utils import write_pack
from ingest.models import PackManifest
from ingest.sources.webster1913 import DEFAULT_WEBSTER_URL, download_source, parse_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-url",
        default=DEFAULT_WEBSTER_URL,
        help="Download URL for the Webster source text.",
    )
    parser.add_argument(
        "--cache-file",
        default=".cache/webster-1913/pg660.txt",
        help="Path to the downloaded raw source file cache.",
    )
    parser.add_argument(
        "--output-dir",
        default="packs/webster-1913",
        help="Output pack directory.",
    )
    parser.add_argument(
        "--max-entries",
        type=int,
        default=3000,
        help="Maximum number of parsed entries to include.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cache_file = Path(args.cache_file)
    output_dir = Path(args.output_dir)

    source_path = download_source(args.source_url, cache_file)
    entries = parse_file(source_path, max_entries=args.max_entries)
    if not entries:
        raise RuntimeError("No entries were parsed from source file.")

    manifest = PackManifest(
        id="webster-1913",
        name="Webster's 1913 (Parsed)",
        language="en",
        sort="alphabetical",
        entry_count=len(entries),
        data_file="entries.jsonl",
        license="Public Domain",
        source_url=args.source_url,
    )
    count = write_pack(output_dir, manifest, entries)
    print(f"Wrote {count} entries to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
