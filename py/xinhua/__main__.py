"""CLI: build Xinhua ZH-ZH pack via ETL pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path

from common.etl import Pipeline
from common.models import PackManifest
from xinhua.extractor import XinhuaExtractor
from xinhua.loader import PackLoader
from xinhua.transformers import get_transformers


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build ZH-ZH pack from chinese-xinhua (word.json, idiom.json, ci.json)."
    )
    parser.add_argument("--out", default="packs/xinhua-zh-zh", help="Output pack directory.")
    parser.add_argument("--cache-dir", default=".cache/xinhua", help="Directory for downloaded JSON files.")
    parser.add_argument("--no-ci", action="store_true", help="Exclude ci.json phrases.")
    args = parser.parse_args()

    out_dir = Path(args.out)
    cache_dir = Path(args.cache_dir)

    pipeline = Pipeline(
        extractor=XinhuaExtractor(include_ci=not args.no_ci),
        transformers=get_transformers(),
        loader=PackLoader(),
    )
    manifest = PackManifest(
        id="xinhua-zh-zh",
        name="新华字典 Xinhua (中中)",
        language="zh",
        sort="pinyin",
        entry_count=0,
        license="MIT",
        source_url="https://github.com/pwxcoo/chinese-xinhua",
    )
    count = pipeline.run(cache_dir, out_dir, manifest)
    if count == 0:
        raise SystemExit("No entries produced from xinhua data.")
    print(f"Wrote {count} entries to {out_dir}")
    return 0
