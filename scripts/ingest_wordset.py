#!/usr/bin/env python3
"""Build EN dictionary pack from Wordset (StevensDeptECE/Dictionaries wordset-dictionary).

Reads data/*.json: one JSONL line per (word, part_of_speech); single-word headwords only;
excludes misc.json. Output: manifest.json + entries.jsonl under --out (default packs/wordset-en/).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

# Script runs from repo root; ingest is in scripts/
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ingest.io_utils import write_pack
from ingest.models import PackManifest
from ingest.sources.wordset import WORDSET_REPO_URL, iter_wordset_data


def get_data_dir(source: Path | None, cache_dir: Path) -> Path:
    """Resolve wordset data directory: from --source or clone into cache."""
    if source is not None:
        source = source.resolve()
        if not source.is_dir():
            raise SystemExit(f"Source path is not a directory: {source}")
        # Repo root: has wordset-dictionary/data/
        data_candidate = source / "wordset-dictionary" / "data"
        if data_candidate.is_dir():
            return data_candidate
        # wordset-dictionary root: has data/
        if (source / "data").is_dir() and list((source / "data").glob("*.json")):
            return source / "data"
        # Direct path to data/ (has *.json)
        if list(source.glob("*.json")):
            return source
        raise SystemExit(f"Source path has no wordset data/*.json: {source}")
    # Clone repo into cache
    cache_dir.mkdir(parents=True, exist_ok=True)
    repo_dir = cache_dir / "Dictionaries"
    if not (repo_dir / "wordset-dictionary" / "data").is_dir():
        subprocess.run(
            ["git", "clone", "--depth", "1", WORDSET_REPO_URL, str(repo_dir)],
            check=True,
            capture_output=True,
        )
    return repo_dir / "wordset-dictionary" / "data"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        metavar="PATH",
        help="Path to wordset-dictionary repo root or to data/ (skip clone).",
    )
    parser.add_argument(
        "--out",
        default="packs/wordset-en",
        help="Output pack directory (default: packs/wordset-en).",
    )
    parser.add_argument(
        "--cache-dir",
        default=".cache/wordset",
        help="Directory for cloning repo when --source not set.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = Path(args.source) if args.source else None
    cache_dir = Path(args.cache_dir)
    out_dir = Path(args.out)

    data_dir = get_data_dir(source, cache_dir)
    entries = list(iter_wordset_data(data_dir, exclude_misc=True))
    if not entries:
        raise SystemExit("No entries produced from wordset data.")

    manifest = PackManifest(
        id="wordset-en",
        name="Wordset Dictionary",
        language="en",
        sort="alphabetical",
        entry_count=len(entries),
        data_file="entries.jsonl",
        license="CC BY 4.0",
        source_url="https://github.com/StevensDeptECE/Dictionaries/tree/master/wordset-dictionary",
    )
    count = write_pack(out_dir, manifest, entries)
    print(f"Wrote {count} entries to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
