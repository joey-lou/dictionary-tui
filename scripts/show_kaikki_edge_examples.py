#!/usr/bin/env python3
"""Print Kaikki raw->parsed edge-case examples (EN + ZH) per data-cleaning rules.

Rules demonstrated:
1. Language-only headwords (no non-EN in EN dict, no non-ZH in ZH dict).
2. Collapsed duplicate/similar glosses; no tags in output.
3. leading_key + is_phrase: index = single word (EN) or single character (ZH); phrases under head.
4. Same headword, different POS or pronunciation → separate records.

Uses the same parser as ingest (`scripts/ingest/sources/kaikki.py`).
"""

from __future__ import annotations

import json
import re
import urllib.request
import html as _html


def _read_url(url: str) -> str:
    with urllib.request.urlopen(url, timeout=60) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _stream_jsonl(url: str):
    with urllib.request.urlopen(url, timeout=60) as resp:
        buf = b""
        for chunk in iter(lambda: resp.read(1 << 16), b""):
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                s = line.decode("utf-8", errors="replace").strip()
                if s:
                    yield s


def _extract_json_code_block(html: str) -> dict:
    m = re.search(r"<pre[^>]*>(.*?)</pre>", html, flags=re.DOTALL)
    if not m:
        raise RuntimeError("Could not find <pre> JSON block in meaning page HTML.")
    payload = _html.unescape(m.group(1)).strip()
    return json.loads(payload)


def _trim_raw(obj: dict, keep_senses: int = 5) -> dict:
    out = {
        "word": obj.get("word"),
        "pos": obj.get("pos"),
        "lang_code": obj.get("lang_code"),
    }
    sounds = obj.get("sounds") or []
    if sounds:
        out["sounds"] = sounds[:4]  # show up to 4 for multi-pronunciation
    senses = obj.get("senses") or []
    trimmed_senses = []
    for s in senses[:keep_senses]:
        if not isinstance(s, dict):
            continue
        trimmed_senses.append(
            {
                "glosses": s.get("glosses"),
                "tags": s.get("tags"),
            }
        )
    out["senses"] = trimmed_senses
    return out


def _parsed_repr(entry, full_max: int = 320) -> dict:
    d = {
        "headword": entry.headword,
        "sort_key": entry.sort_key,
        "leading_key": getattr(entry, "leading_key", None),
        "is_phrase": getattr(entry, "is_phrase", None),
        "part_of_speech": entry.part_of_speech,
        "pronunciation": entry.pronunciation,
        "short_definition": entry.short_definition,
        "full_definition": entry.full_definition,
    }
    if isinstance(d.get("full_definition"), str) and len(d["full_definition"]) > full_max:
        d["full_definition"] = d["full_definition"][:full_max] + "…"
    return d


def main() -> int:
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root / "scripts"))
    from ingest.sources.kaikki import parse_kaikki_json_line

    print("=== Rule 3: Index = single word (EN) / single character (ZH); phrases under head ===\n")

    # EN phrase: "rain cats and dogs" → leading_key "rain", is_phrase True
    en_url = "https://kaikki.org/dictionary/English/kaikki.org-dictionary-English.jsonl"
    en_phrase_obj = None
    en_phrase_entries = []
    for s in _stream_jsonl(en_url):
        try:
            obj = json.loads(s)
        except json.JSONDecodeError:
            continue
        w = obj.get("word")
        if isinstance(w, str) and " " in w and "rain" in w.lower():
            entries = parse_kaikki_json_line(s, "en")
            if entries:
                en_phrase_obj = obj
                en_phrase_entries = entries
                break
    if en_phrase_obj and en_phrase_entries:
        print("EN phrase (rain cats and dogs) — appears under index key 'rain', not its own index row")
        print("RAW (trimmed):")
        print(json.dumps(_trim_raw(en_phrase_obj, keep_senses=2), ensure_ascii=False, indent=2))
        print("\nPARSED (leading_key = first word, is_phrase = True):")
        print(json.dumps(_parsed_repr(en_phrase_entries[0]), ensure_ascii=False, indent=2))

    # ZH single char vs phrase
    zh_single_url = "https://kaikki.org/dictionary/Chinese/meaning/%E6%AD%A4/%E6%AD%A4/%E6%AD%A4.html"
    zh_phrase_url = "https://kaikki.org/dictionary/Chinese/meaning/%E6%AD%A4/%E6%AD%A4%E6%99%82/%E6%AD%A4%E6%99%82%E6%AD%A4%E5%88%BB.html"
    zh_single_raw = _extract_json_code_block(_read_url(zh_single_url))
    zh_phrase_raw = _extract_json_code_block(_read_url(zh_phrase_url))
    zh_single_entries = parse_kaikki_json_line(json.dumps(zh_single_raw, ensure_ascii=False), "zh")
    zh_phrase_entries = parse_kaikki_json_line(json.dumps(zh_phrase_raw, ensure_ascii=False), "zh")
    if zh_single_entries:
        print("\nZH single character 此 — index row; leading_key = 此, is_phrase = False")
        print("PARSED:", json.dumps(_parsed_repr(zh_single_entries[0]), ensure_ascii=False, indent=2))
    if zh_phrase_entries:
        print("\nZH phrase 此時此刻 — under index key 此; leading_key = 此, is_phrase = True")
        print("RAW (trimmed):")
        print(json.dumps(_trim_raw(zh_phrase_raw, keep_senses=3), ensure_ascii=False, indent=2))
        print("\nPARSED:")
        print(json.dumps(_parsed_repr(zh_phrase_entries[0]), ensure_ascii=False, indent=2))

    print("\n=== Rule 2: Collapsed duplicate glosses; no tags ===\n")

    # Find "free" or similar with many duplicate glosses
    for s in _stream_jsonl(en_url):
        try:
            obj = json.loads(s)
        except json.JSONDecodeError:
            continue
        if obj.get("word") != "free" or obj.get("pos") != "adj":
            continue
        entries = parse_kaikki_json_line(s, "en")
        if not entries:
            continue
        print("EN 'free' (adj) — raw has many senses with repeated 'Unconstrained.' and tags")
        print("RAW (first 8 senses):")
        print(json.dumps(_trim_raw(obj, keep_senses=8), ensure_ascii=False, indent=2))
        print("\nPARSED: duplicate glosses merged, tags omitted")
        print(json.dumps(_parsed_repr(entries[0], full_max=400), ensure_ascii=False, indent=2))
        break
    else:
        print("(Could not find 'free' adj in first chunk; run with full file for this example)")

    print("\n=== Rule 4: Same headword, different POS or pronunciation → separate records ===\n")

    # Same headword, different POS: "rain" noun and "rain" verb (separate lines in Kaikki)
    rain_noun = rain_verb = None
    for s in _stream_jsonl(en_url):
        try:
            obj = json.loads(s)
        except json.JSONDecodeError:
            continue
        if obj.get("word") != "rain":
            continue
        entries = parse_kaikki_json_line(s, "en")
        if not entries:
            continue
        pos = (obj.get("pos") or "").lower()
        if pos == "noun":
            rain_noun = entries[0]
        elif pos == "verb":
            rain_verb = entries[0]
        if rain_noun and rain_verb:
            break
    if rain_noun and rain_verb:
        print("EN 'rain' — two records: noun vs verb")
        print("Record 1 (noun):", json.dumps(_parsed_repr(rain_noun, full_max=120), ensure_ascii=False))
        print("Record 2 (verb):", json.dumps(_parsed_repr(rain_verb, full_max=120), ensure_ascii=False))
    else:
        print("EN 'rain' noun/verb: found noun=", rain_noun is not None, ", verb=", rain_verb is not None)

    # Multiple pronunciations: one line with two sounds → two entries (if we have such a line)
    for s in _stream_jsonl(en_url):
        try:
            obj = json.loads(s)
        except json.JSONDecodeError:
            continue
        sounds = obj.get("sounds") or []
        ipas = [x.get("ipa") for x in sounds if isinstance(x, dict) and x.get("ipa")]
        if len(ipas) >= 2 and obj.get("lang_code") == "en":
            entries = parse_kaikki_json_line(s, "en")
            if len(entries) >= 2:
                print("\nSame headword+POS, multiple pronunciations → one record per pronunciation:")
                print("Headword:", entries[0].headword, "POS:", entries[0].part_of_speech)
                for i, e in enumerate(entries[:3]):
                    print(f"  [{i+1}] pronunciation={e.pronunciation!r}")
                break
    else:
        print("\n(Multiple-pronunciation example: typically one entry per (word,pos) line;")
        print(" when a line has multiple sounds we emit one record per sound.)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
