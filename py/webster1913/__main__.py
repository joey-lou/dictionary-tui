"""CLI: build Webster 1913 pack via ETL pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path

from common.etl import Pipeline
from common.models import PackManifest
from webster1913.extractor import WebsterExtractor, download_source
from webster1913.loader import PackLoader
from webster1913.transformers import get_transformers


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build EN pack from Webster's Unabridged 1913 (Project Gutenberg #29765)."
    )
    parser.add_argument("--out", default="packs/webster1913-en", help="Output pack directory.")
    parser.add_argument("--cache-dir", default=".cache/webster1913", help="Directory for downloaded source.")
    args = parser.parse_args()

    out_dir = Path(args.out)
    cache_dir = Path(args.cache_dir)
    source = download_source(cache_dir)

    pipeline = Pipeline(
        extractor=WebsterExtractor(),
        transformers=get_transformers(),
        loader=PackLoader(),
    )
    manifest = PackManifest(
        id="webster1913-en",
        name="Webster's 1913",
        language="en",
        sort="alphabetical",
        entry_count=0,
        license="Public Domain",
        source_url="https://www.gutenberg.org/ebooks/29765",
    )
    count = pipeline.run(source, out_dir, manifest)
    if count == 0:
        raise SystemExit("No entries produced from Webster 1913 data.")
    print(f"Wrote {count} entries to {out_dir}")
    return 0
