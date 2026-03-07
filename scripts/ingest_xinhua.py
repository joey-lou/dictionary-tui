#!/usr/bin/env python3
"""Build ZH-ZH dictionary pack from chinese-xinhua (pwxcoo/chinese-xinhua).

Head entries from word.json (single characters with pinyin, definitions).
Phrases from idiom.json (成语) and ci.json (词语), grouped under leading char.
Output: manifest.json + entries.jsonl under --out (default packs/xinhua-zh-zh/).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ingest.io_utils import write_pack
from ingest.models import PackManifest
from ingest.sources.xinhua import parse_xinhua


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default="packs/xinhua-zh-zh",
        help="Output pack directory (default: packs/xinhua-zh-zh).",
    )
    parser.add_argument(
        "--cache-dir",
        default=".cache/xinhua",
        help="Directory for downloaded JSON files.",
    )
    parser.add_argument(
        "--no-ci",
        action="store_true",
        help="Exclude ci.json (词语) phrases; keep only word.json heads + idiom.json phrases.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out)
    cache_dir = Path(args.cache_dir)

    entries = parse_xinhua(cache_dir, include_ci=not args.no_ci)
    if not entries:
        raise SystemExit("No entries produced from xinhua data.")

    manifest = PackManifest(
        id="xinhua-zh-zh",
        name="新华字典 Xinhua (中中)",
        language="zh",
        sort="pinyin",
        entry_count=len(entries),
        license="MIT",
        source_url="https://github.com/pwxcoo/chinese-xinhua",
    )
    count = write_pack(out_dir, manifest, entries)
    print(f"Wrote {count} entries to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
