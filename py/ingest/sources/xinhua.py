"""chinese-xinhua source (pwxcoo/chinese-xinhua): ZH-ZH dictionary.

Head entries come from ``word.json`` (single characters with pinyin).
Phrases come from ``idiom.json`` (成语) and ``ci.json`` (词语), grouped
under their leading character's head.
"""

from __future__ import annotations

import json
import urllib.request
from collections import defaultdict
from pathlib import Path

from ..models import HeadEntry, PhraseItem

_BASE_URL = "https://raw.githubusercontent.com/pwxcoo/chinese-xinhua/master/data"
_SHORT_DEF_MAX = 100


def _download_json(name: str, cache_dir: Path) -> list[dict]:
    path = cache_dir / name
    if not path.exists():
        cache_dir.mkdir(parents=True, exist_ok=True)
        url = f"{_BASE_URL}/{name}"
        with urllib.request.urlopen(url, timeout=120) as resp:
            path.write_bytes(resp.read())
    return json.loads(path.read_text(encoding="utf-8"))


def _clean_explanation(text: str) -> str:
    """Normalize whitespace in explanation text."""
    return " ".join(text.split()).strip()


def _short(text: str) -> str:
    if len(text) <= _SHORT_DEF_MAX:
        return text
    return text[:_SHORT_DEF_MAX].rstrip() + "…"


def _pinyin_sort_key(pinyin: str) -> str:
    """Lowercase pinyin for sorting."""
    return pinyin.lower().strip()


def parse_xinhua(
    cache_dir: Path,
    *,
    include_ci: bool = True,
) -> list[HeadEntry]:
    """Build ZH-ZH ``HeadEntry`` list from chinese-xinhua data.

    Downloads ``word.json``, ``idiom.json``, and optionally ``ci.json``
    into *cache_dir* if not already present.
    """
    word_data = _download_json("word.json", cache_dir)
    idiom_data = _download_json("idiom.json", cache_dir)
    ci_data = _download_json("ci.json", cache_dir) if include_ci else []

    # --- Build head entries from word.json (single characters) ---
    heads: list[HeadEntry] = []
    seen_chars: set[str] = set()

    for obj in word_data:
        char = (obj.get("word") or "").strip()
        if not char or len(char) != 1:
            continue
        pinyin = (obj.get("pinyin") or "").strip()
        explanation = _clean_explanation(obj.get("explanation") or "")
        if not explanation:
            continue

        lines = [part.strip() for part in explanation.replace("；", "\n").split("\n") if part.strip()]
        short = _short(lines[0]) if lines else explanation[:_SHORT_DEF_MAX]
        if len(lines) > 1:
            full = "\n".join(f"{i + 1}. {part}" for i, part in enumerate(lines))
        else:
            full = lines[0] if lines else explanation

        heads.append(
            HeadEntry(
                headword=char,
                sort_key=_pinyin_sort_key(pinyin) if pinyin else char,
                leading_key=char,
                pronunciation=pinyin or None,
                part_of_speech=None,
                short_definition=short,
                full_definition=full,
            )
        )
        seen_chars.add(char)

    # --- Collect phrases from idiom.json ---
    phrase_bucket: dict[str, list[PhraseItem]] = defaultdict(list)

    for obj in idiom_data:
        word = (obj.get("word") or "").strip()
        if not word or len(word) <= 1:
            continue
        pinyin = (obj.get("pinyin") or "").strip()
        explanation = _clean_explanation(obj.get("explanation") or "")
        if not explanation:
            continue
        defn = f"[{pinyin}] {explanation}" if pinyin else explanation
        leading = word[0]
        phrase_bucket[leading].append(PhraseItem(form=word, definition=defn))

    # --- Collect phrases from ci.json ---
    for obj in ci_data:
        ci = (obj.get("ci") or "").strip()
        if not ci or len(ci) <= 1:
            continue
        explanation = _clean_explanation(obj.get("explanation") or "")
        if not explanation:
            continue
        leading = ci[0]
        phrase_bucket[leading].append(PhraseItem(form=ci, definition=explanation))

    # --- Attach phrases to heads ---
    final: list[HeadEntry] = []
    attached_keys: set[str] = set()
    for h in heads:
        phrases = tuple(phrase_bucket.get(h.leading_key, ()))
        # Attach phrases only to the first head for each character
        if h.leading_key in attached_keys:
            phrases = ()
        elif phrases:
            attached_keys.add(h.leading_key)
        if phrases:
            h = HeadEntry(
                headword=h.headword,
                sort_key=h.sort_key,
                leading_key=h.leading_key,
                pronunciation=h.pronunciation,
                part_of_speech=h.part_of_speech,
                short_definition=h.short_definition,
                full_definition=h.full_definition,
                phrases=phrases,
            )
        final.append(h)

    # --- Synthetic heads for chars with phrases but no word.json entry ---
    for char, items in phrase_bucket.items():
        if char not in seen_chars and items:
            final.append(
                HeadEntry(
                    headword=char,
                    sort_key=char,
                    leading_key=char,
                    pronunciation=None,
                    part_of_speech=None,
                    short_definition=f"（见 {len(items)} 个词条）",
                    full_definition=None,
                    phrases=tuple(items),
                )
            )

    return final
