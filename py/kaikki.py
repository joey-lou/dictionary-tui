"""
Parse Kaikki/Wiktextract JSONL into head entries + phrases.

Rules (see docs/KAIKKI_PARSING_DESIGN.md):
- Language-only headwords; collapse glosses, no tags.
- Index = single word (EN) or single character (ZH). Phrases nested under head.
- One record per (headword, POS); one pronunciation per record (no row per variant).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, List

from .schema import HeadEntry, PhraseItem

SHORT_DEF_MAX = 100


# ---------------------------------------------------------------------------
# Headword filters
# ---------------------------------------------------------------------------


def _is_cjk(c: str) -> bool:
    cp = ord(c)
    return (
        0x4E00 <= cp <= 0x9FFF
        or 0x3400 <= cp <= 0x4DBF
        or 0x20000 <= cp <= 0x2A6DF
        or 0x2A700 <= cp <= 0x2B73F
        or 0x2B740 <= cp <= 0x2B81F
        or 0x2B820 <= cp <= 0x2CEAF
        or 0x2CEB0 <= cp <= 0x2EBEF
        or 0x30000 <= cp <= 0x3134F
        or cp == 0x3007
    )


def is_ok_english_headword(word: str, allow_single_letter: bool = False) -> bool:
    if not word or not word.strip():
        return False
    w = word.strip()
    if not allow_single_letter and len(w) == 1 and w.isalpha():
        return False
    for ch in w:
        if ch.isalpha() or ch in " '-":
            continue
        return False
    return any(c.isalpha() for c in w)


def is_ok_chinese_headword(word: str) -> bool:
    if not word or not word.strip():
        return False
    return all(_is_cjk(c) for c in word.strip())


def leading_key_and_phrase(word: str, lang: str) -> tuple[str, bool]:
    """(leading_key, is_phrase). EN: first word; ZH: first character."""
    w = (word or "").strip()
    if not w:
        return "", True
    if lang == "zh":
        return w[0], len(w) > 1
    first = w.split()[0] or w
    return first.lower(), " " in w


# ---------------------------------------------------------------------------
# Pronunciation: one per (head, POS)
# ---------------------------------------------------------------------------


def _first_ipa(sounds: list) -> str | None:
    for s in sounds:
        if isinstance(s, dict) and s.get("ipa"):
            return s["ipa"]
    return None


def _first_pinyin(sounds: list) -> str | None:
    """First zh_pron that looks like Pinyin (Latin + tone numbers or nothing). Prefer Mandarin."""
    for s in sounds:
        if not isinstance(s, dict):
            continue
        raw = s.get("zh_pron")
        if not raw or not isinstance(raw, str):
            continue
        # "rén (Mandarin)" or "rén" -> take first token
        p = raw.strip().split()[0].strip()
        if not p:
            continue
        # Prefer tokens that look like Pinyin (no ㄓ, no numerals only)
        if any(c.isalpha() for c in p):
            return p
    for s in sounds:
        if isinstance(s, dict) and s.get("zh_pron"):
            raw = s["zh_pron"]
            if isinstance(raw, str):
                return raw.strip().split()[0].strip() or raw.strip()
    return None


def pick_one_pronunciation(obj: dict, lang: str) -> str | None:
    sounds = obj.get("sounds") or []
    if lang == "zh":
        return _first_pinyin(sounds) or _first_ipa(sounds)
    return _first_ipa(sounds)


# ---------------------------------------------------------------------------
# Glosses: collect, dedupe, no tags
# ---------------------------------------------------------------------------


def _clean_gloss(s: str) -> str:
    """Remove wiki cruft and normalize whitespace."""
    s = s.replace("__NOTITLECONVERT__", "").strip()
    return " ".join(s.split())


def _glosses_from_sense(sense: dict) -> List[str]:
    out: List[str] = []
    for g in sense.get("glosses") or []:
        if isinstance(g, dict) and g.get("gloss"):
            out.append(_clean_gloss(g["gloss"]))
        elif isinstance(g, str) and g.strip():
            out.append(_clean_gloss(g))
    return out


def _unique_glosses(gloss_list: List[str]) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for g in gloss_list:
        n = g.strip()
        if n and n not in seen:
            seen.add(n)
            out.append(n)
    return out


def build_definitions(senses: list) -> tuple[str, str]:
    """(short_definition, full_definition). Deduped glosses, no tags."""
    all_glosses: List[str] = []
    for sense in senses:
        if isinstance(sense, dict):
            all_glosses.extend(_glosses_from_sense(sense))
    unique = _unique_glosses(all_glosses)
    if not unique:
        return "", ""
    short = unique[0]
    if len(short) > SHORT_DEF_MAX:
        short = short[:SHORT_DEF_MAX].rstrip() + "…"
    full = " ".join(f"{i + 1}. {g}" for i, g in enumerate(unique))
    return short, full


# ---------------------------------------------------------------------------
# POS label
# ---------------------------------------------------------------------------


def _pos_label(pos: str) -> str:
    p = (pos or "").lower()
    if p in ("noun", "verb", "adj", "adjective", "adv", "adverb"):
        return "adj" if p in ("adjective", "adj") else "adv" if p in ("adverb", "adv") else p
    return pos or ""


# ---------------------------------------------------------------------------
# Raw entry (internal): one per (word, pos) with one pron
# ---------------------------------------------------------------------------


@dataclass
class _Raw:
    headword: str
    sort_key: str
    leading_key: str
    is_phrase: bool
    part_of_speech: str
    pronunciation: str | None
    short_definition: str
    full_definition: str


def _parse_line(line: str, lang: str, allow_single_letter_en: bool) -> List[_Raw]:
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return []
    if obj.get("lang_code") != lang and obj.get("lang") != lang:
        return []
    word = obj.get("word") or obj.get("head", "")
    if not word or not isinstance(word, str):
        return []
    if lang == "en" and not is_ok_english_headword(word, allow_single_letter=allow_single_letter_en):
        return []
    if lang == "zh" and not is_ok_chinese_headword(word):
        return []

    lead, is_phrase = leading_key_and_phrase(word, lang)
    pron = pick_one_pronunciation(obj, lang)
    sort_key = word.lower() if lang == "en" else word

    sections: List[tuple[str, list]] = []
    if obj.get("pos_sections"):
        for sec in obj["pos_sections"]:
            if isinstance(sec, dict) and sec.get("senses"):
                sections.append((sec.get("pos") or "", sec["senses"]))
    if not sections and obj.get("senses"):
        sections.append((obj.get("pos") or "", obj["senses"]))

    out: List[_Raw] = []
    for pos, senses in sections:
        short, full = build_definitions(senses)
        if not short and not full:
            continue
        pos_norm = _pos_label(pos) or ""
        out.append(
            _Raw(
                headword=word,
                sort_key=sort_key,
                leading_key=lead,
                is_phrase=is_phrase,
                part_of_speech=pos_norm,
                pronunciation=pron,
                short_definition=short,
                full_definition=full,
            )
        )
    return out


def parse_line(line: str, lang: str, allow_single_letter_en: bool = False) -> List[_Raw]:
    """Parse one JSONL line into zero or more raw entries (one per POS, one pron)."""
    return _parse_line(line, lang, allow_single_letter_en)


def raw_to_head_entries(raw_list: List[_Raw]) -> List[HeadEntry]:
    """Collapse phrases under heads; return only head entries with phrases attached."""
    heads: List[_Raw] = []
    phrases: List[_Raw] = []
    for r in raw_list:
        if r.is_phrase:
            phrases.append(r)
        else:
            heads.append(r)

    key = lambda r: (r.leading_key, r.part_of_speech)
    phrase_by_key: dict[tuple[str, str], List[_Raw]] = {}
    for p in phrases:
        k = key(p)
        phrase_by_key.setdefault(k, []).append(p)

    out: List[HeadEntry] = []
    for h in heads:
        k = key(h)
        phrase_items: List[PhraseItem] = [
            PhraseItem(
                form=p.headword,
                definition=(p.short_definition or p.full_definition or "").strip(),
            )
            for p in phrase_by_key.get(k, [])
        ]
        out.append(
            HeadEntry(
                headword=h.headword,
                sort_key=h.sort_key,
                leading_key=h.leading_key,
                pronunciation=h.pronunciation,
                short_definition=h.short_definition or None,
                full_definition=h.full_definition or None,
                part_of_speech=h.part_of_speech or None,
                phrases=tuple(phrase_items),
            )
        )
    return out


def stream_raw_from_lines(
    lines: Iterator[str],
    lang: str,
    max_raw: int | None,
    allow_single_letter_en: bool = False,
) -> Iterator[_Raw]:
    """Yield raw entries from JSONL lines; stop after max_raw."""
    n = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        for r in _parse_line(line, lang, allow_single_letter_en):
            yield r
            n += 1
            if max_raw is not None and n >= max_raw:
                return


def stream_raw_from_path(
    path: Path,
    lang: str,
    max_raw: int | None,
    allow_single_letter_en: bool = False,
) -> Iterator[_Raw]:
    import gzip

    if path.suffix == ".gz":
        f = gzip.open(path, "rt", encoding="utf-8")
    else:
        f = path.open("r", encoding="utf-8")
    with f as fp:
        yield from stream_raw_from_lines(fp, lang, max_raw, allow_single_letter_en=allow_single_letter_en)
