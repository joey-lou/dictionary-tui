#!/usr/bin/env python3
"""Build an English dictionary pack from Princeton WordNet 3.0 (optionally + CMU pronunciation)."""

from __future__ import annotations

import argparse
from pathlib import Path

from ingest.io_utils import write_pack
from ingest.models import PackManifest
from ingest.sources.cmudict import (
    DEFAULT_CMUDICT_URL,
    download_cmudict,
    pronunciation_lookup_from_path,
)
from ingest.sources.wordnet import DEFAULT_WORDNET_URL, download_source, parse_tarball


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-url",
        default=DEFAULT_WORDNET_URL,
        help="WordNet tarball URL.",
    )
    parser.add_argument(
        "--cache-file",
        default=".cache/wordnet/WordNet-3.0.tar.gz",
        help="Path to downloaded WordNet tarball.",
    )
    parser.add_argument(
        "--no-pronunciation",
        action="store_true",
        help="Do not add pronunciation from CMU Pronouncing Dictionary.",
    )
    parser.add_argument(
        "--cmudict-url",
        default=DEFAULT_CMUDICT_URL,
        help="URL for CMU dict (used only when pronunciation is enabled).",
    )
    parser.add_argument(
        "--cmudict-file",
        metavar="PATH",
        default=".cache/cmudict/cmudict-0.7b",
        help="Local CMU dict file (download from --cmudict-url if missing).",
    )
    parser.add_argument(
        "--output-dir",
        default="packs/wordnet",
        help="Output pack directory.",
    )
    parser.add_argument(
        "--max-entries",
        type=int,
        default=None,
        metavar="N",
        help="Maximum number of entries (default: no limit, full dictionary).",
    )
    parser.add_argument(
        "--pack-id",
        default="wordnet",
        help="Pack id to write to manifest.",
    )
    parser.add_argument(
        "--pack-name",
        default="WordNet 3.0",
        help="Display name in manifest.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_path = download_source(args.source_url, Path(args.cache_file))
    pronunciation_lookup: dict[str, str] = {}
    if not args.no_pronunciation:
        cmu_path = Path(args.cmudict_file)
        if not cmu_path.exists():
            try:
                download_cmudict(cmu_path, url=args.cmudict_url)
            except Exception as e:
                print(f"Warning: could not download CMU dict: {e}. Building without pronunciation.")
        pronunciation_lookup = pronunciation_lookup_from_path(cmu_path)
    entries = parse_tarball(
        source_path,
        max_entries=args.max_entries,
        pronunciation_lookup=pronunciation_lookup,
    )
    if not entries:
        raise RuntimeError("No entries parsed from WordNet source.")

    manifest = PackManifest(
        id=args.pack_id,
        name=args.pack_name,
        language="en",
        sort="alphabetical",
        entry_count=len(entries),
        data_file="entries.jsonl",
        license="WordNet License",
        source_url=args.source_url,
    )
    count = write_pack(Path(args.output_dir), manifest, entries)
    print(f"Wrote {count} entries to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
