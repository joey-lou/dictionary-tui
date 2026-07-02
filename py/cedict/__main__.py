"""CLI: build CC-CEDICT ZH-EN pack via ETL pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path

from cedict.extractor import DEFAULT_CEDICT_URL, CEDICTExtractor, download_source
from cedict.loader import PackLoader
from cedict.transformers import get_transformers
from common.etl import Pipeline
from common.models import PackManifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Chinese–English pack from CC-CEDICT.")
    parser.add_argument("--source-file", metavar="PATH", help="Use local CEDICT file instead of downloading.")
    parser.add_argument("--source-url", default=DEFAULT_CEDICT_URL, help="URL to CEDICT file.")
    parser.add_argument(
        "--cache-file",
        default=".cache/cedict/cedict_1_0_ts_utf-8_mdbg.txt.gz",
        help="Path to downloaded CEDICT cache.",
    )
    parser.add_argument("--output-dir", default="packs/cc-cedict", help="Output pack directory.")
    parser.add_argument("--traditional", action="store_true", help="Use traditional Chinese as headword.")
    args = parser.parse_args()

    cache_path = Path(args.cache_file)
    output_dir = Path(args.output_dir)

    if args.source_file:
        source_path = Path(args.source_file)
        if not source_path.exists():
            raise SystemExit(f"Source file not found: {source_path}")
    else:
        source_path = download_source(args.source_url, cache_path)
        head = source_path.read_bytes()[:200]
        if head.startswith((b"<!", b"<html")):
            source_path.unlink(missing_ok=True)
            raise SystemExit(
                "Download returned HTML (URL may be broken). "
                "Download CEDICT manually and run with --source-file /path/to/cedict_*.txt.gz"
            )

    pipeline = Pipeline(
        extractor=CEDICTExtractor(use_simplified=not args.traditional),
        transformers=get_transformers(),
        loader=PackLoader(),
    )
    manifest = PackManifest(
        id="cc-cedict",
        name="CC-CEDICT (中英)",
        language="zh",
        sort="pinyin",
        entry_count=0,
        license="CC BY-SA 4.0",
        source_url=args.source_url,
    )
    count = pipeline.run(source_path, output_dir, manifest)
    if count == 0:
        raise SystemExit("No entries parsed from CEDICT source.")
    print(f"Wrote {count} entries to {output_dir}")
    return 0
