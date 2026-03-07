"""
CLI to build Kaikki dictionary packs. See docs/KAIKKI_PARSING_DESIGN.md.

  python -m py.kaikki_ingest en --max-entries 3000 --out packs/kaikki-en-poc
  python -m py.kaikki_ingest zh-en --max-entries 3000 --out packs/kaikki-zh-en-poc
  python -m py.kaikki_ingest zh-zh --max-entries 3000 --out packs/kaikki-zh-zh-poc
"""

from __future__ import annotations

import argparse
import gzip
import io
import sys
import urllib.request
from pathlib import Path

from .kaikki import raw_to_head_entries, stream_raw_from_lines, stream_raw_from_path
from .pack_io import write_pack
from .schema import PackManifest

KAIKKI_EN_URL = "https://kaikki.org/dictionary/English/kaikki.org-dictionary-English.jsonl"
KAIKKI_ZH_EN_URL = "https://kaikki.org/dictionary/Chinese/kaikki.org-dictionary-Chinese.jsonl"
KAIKKI_ZH_ZH_URL = "https://kaikki.org/dictionary/downloads/zh/zh-extract.jsonl.gz"

CONFIG = {
    "en": {
        "lang": "en",
        "pack_id": "kaikki-en-poc",
        "pack_name": "English (Wiktionary) POC",
        "url": KAIKKI_EN_URL,
        "gzip": False,
    },
    "zh-en": {
        "lang": "zh",
        "pack_id": "kaikki-zh-en-poc",
        "pack_name": "Chinese → English POC",
        "url": KAIKKI_ZH_EN_URL,
        "gzip": False,
    },
    "zh-zh": {
        "lang": "zh",
        "pack_id": "kaikki-zh-zh-poc",
        "pack_name": "Chinese → Chinese (zhwiktionary) POC",
        "url": KAIKKI_ZH_ZH_URL,
        "gzip": True,
    },
}


def _stream_lines_from_url(url: str, gzipped: bool):
    """Yield lines from URL; decompress gzip on the fly."""
    with urllib.request.urlopen(url, timeout=120) as resp:
        if gzipped:
            with gzip.GzipFile(fileobj=resp, mode="rb") as gz:
                with io.TextIOWrapper(gz, encoding="utf-8", errors="replace") as text:
                    for line in text:
                        s = line.rstrip("\n\r")
                        if s.strip():
                            yield s
        else:
            buf = b""
            for chunk in iter(lambda: resp.read(1 << 16), b""):
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    s = line.decode("utf-8", errors="replace").strip()
                    if s:
                        yield s
            if buf.strip():
                yield buf.decode("utf-8", errors="replace").strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("variant", choices=list(CONFIG), help="en | zh-en | zh-zh")
    parser.add_argument("--source-file", type=Path, help="Local JSONL or .jsonl.gz (else stream from URL)")
    parser.add_argument("--out", type=Path, default=None, help="Output pack dir (default: packs/<pack_id>)")
    parser.add_argument("--max-entries", type=int, default=5000, help="Max raw entries to read (default 5000)")
    parser.add_argument("--allow-single-letter-en", action="store_true", help="Include single-letter EN headwords (e.g. A, B)")
    args = parser.parse_args()

    cfg = CONFIG[args.variant]
    lang = cfg["lang"]
    out_dir = args.out or Path("packs") / cfg["pack_id"]

    if args.source_file:
        if not args.source_file.exists():
            print(f"Error: not found: {args.source_file}", file=sys.stderr)
            return 1
        raw_list = list(
            stream_raw_from_path(
                args.source_file,
                lang,
                max_raw=args.max_entries,
                allow_single_letter_en=args.allow_single_letter_en,
            )
        )
    else:
        print(f"Streaming from {cfg['url']}...", file=sys.stderr)
        lines = _stream_lines_from_url(cfg["url"], cfg["gzip"])
        raw_list = list(
            stream_raw_from_lines(
                lines,
                lang,
                max_raw=args.max_entries,
                allow_single_letter_en=args.allow_single_letter_en,
            )
        )

    if not raw_list:
        print("No entries parsed.", file=sys.stderr)
        return 1

    heads = raw_to_head_entries(raw_list)
    manifest = PackManifest(
        id=cfg["pack_id"],
        name=cfg["pack_name"],
        language=lang,
        sort="alphabetical",
        entry_count=len(heads),
        data_file="entries.jsonl",
        license="CC BY-SA 3.0",
        source_url="https://kaikki.org/dictionary/",
    )
    n = write_pack(out_dir, manifest, heads)
    print(f"Wrote {n} head entries to {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
