#!/usr/bin/env python3
"""Fetch first N lines from a Kaikki dictionary JSONL and dump structure for inspection.

Usage:
  python3 scripts/inspect_kaikki_raw.py [N]           # English, N lines (default 100)
  python3 scripts/inspect_kaikki_raw.py 100 zh         # Chinese, 100 lines
"""

from __future__ import annotations

import json
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path

# Language label -> (URL, filename prefix). Postprocessed one-word-per-line format.
KAIKKI_URLS = {
    "en": (
        "https://kaikki.org/dictionary/English/kaikki.org-dictionary-English.jsonl",
        "kaikki_en",
    ),
    "zh": (
        "https://kaikki.org/dictionary/Chinese/kaikki.org-dictionary-Chinese.jsonl",
        "kaikki_zh",
    ),
}


def stream_lines(url: str, max_lines: int):
    with urllib.request.urlopen(url, timeout=60) as resp:
        buffer = b""
        count = 0
        for chunk in iter(lambda: resp.read(1 << 16), b""):
            buffer += chunk
            while b"\n" in buffer and count < max_lines:
                line, buffer = buffer.split(b"\n", 1)
                count += 1
                yield line.decode("utf-8", errors="replace").strip()
            if count >= max_lines:
                return


def main():
    args = sys.argv[1:]
    n = 100
    lang = "en"
    if args:
        try:
            n = int(args[0])
            if len(args) > 1:
                lang = args[1].lower()
        except ValueError:
            lang = args[0].lower() if args[0].isalpha() else "en"
    if lang not in KAIKKI_URLS:
        print(f"Unknown language: {lang}. Use one of: {list(KAIKKI_URLS.keys())}")
        sys.exit(1)
    url, prefix = KAIKKI_URLS[lang]
    out_dir = Path(__file__).parent.parent / "tmp"
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = out_dir / f"{prefix}_first_{n}_raw.jsonl"
    summary_path = out_dir / f"{prefix}_structure_summary.txt"

    lines = []
    print(f"Fetching first {n} lines from {url}...")
    for line in stream_lines(url, n):
        if line:
            lines.append(line)

    # Save raw
    with open(raw_path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line)
            f.write("\n")
    print(f"Saved {len(lines)} raw lines to {raw_path}")

    # Collect all keys and value types
    all_keys: defaultdict[str, set[str]] = defaultdict(set)
    sample_values: dict[str, list] = {}
    word_samples = []
    sense_keys: defaultdict[str, set[str]] = defaultdict(set)

    for i, line in enumerate(lines):
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        for k, v in obj.items():
            type_name = type(v).__name__
            if isinstance(v, list) and v:
                type_name = f"list[{type(v[0]).__name__}]"
            elif isinstance(v, dict) and v:
                type_name = "dict"
            all_keys[k].add(type_name)
            if k not in sample_values:
                sample_values[k] = []
            if len(sample_values[k]) < 3:
                if isinstance(v, str) and len(v) > 80:
                    sample_values[k].append(repr(v[:80]) + "...")
                elif isinstance(v, list) and len(v) > 2:
                    sample_values[k].append(f"list(len={len(v)})")
                else:
                    sample_values[k].append(repr(v)[:100])
        for sense in obj.get("senses") or []:
            if isinstance(sense, dict):
                for sk in sense.keys():
                    sense_keys[sk].add(type(sense.get(sk)).__name__)
        if len(word_samples) < 5:
            word_samples.append((obj.get("head") or obj.get("word"), json.dumps(obj, indent=2)[:2000]))

    # Write summary
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(f"=== {lang.upper()} — Top-level keys (first {len(lines)} lines) ===\n\n")
        for k in sorted(all_keys.keys()):
            f.write(f"  {k}: {all_keys[k]}\n")
            for ex in sample_values.get(k, [])[:2]:
                f.write(f"    e.g. {ex}\n")
            f.write("\n")
        if sense_keys:
            f.write("\n=== Sense-level keys seen ===\n\n")
            for k in sorted(sense_keys.keys()):
                f.write(f"  {k}: {sense_keys[k]}\n")
        f.write("\n=== Full JSON sample (first 5 entries) ===\n\n")
        for head, sample in word_samples:
            f.write(f"--- head/word: {head} ---\n")
            f.write(sample)
            f.write("\n\n")

    print(f"Structure summary written to {summary_path}")
    print("Top-level keys:", sorted(all_keys.keys()))


if __name__ == "__main__":
    main()
