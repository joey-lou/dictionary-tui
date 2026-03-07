"""Parse Kaikki/Wiktextract JSONL (Wiktionary) for English entries with pronunciation and rich definitions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Iterator

from ..models import DetailEntry

# Max length for short_definition in list view.
_SHORT_DEF_MAX = 100


def _is_basic_english_headword(word: str) -> bool:
    """
    Keep only English-ish headwords: letters plus space, apostrophe, hyphen.
    This drops entries like "-ity", "A.", "C++", "foo/bar", etc.
    """
    if not word or not word.strip():
        return False
    w = word.strip()
    for ch in w:
        if ch.isalpha():
            continue
        if ch in {" ", "-", "'"}:
            continue
        return False
    # Must contain at least one letter.
    return any(c.isalpha() for c in w)


def _is_cjk_ideograph(ch: str) -> bool:
    cp = ord(ch)
    # Unified ideographs + extensions commonly encountered in Wiktionary.
    return (
        0x4E00 <= cp <= 0x9FFF  # CJK Unified Ideographs
        or 0x3400 <= cp <= 0x4DBF  # Extension A
        or 0x20000 <= cp <= 0x2A6DF  # Extension B
        or 0x2A700 <= cp <= 0x2B73F  # Extension C
        or 0x2B740 <= cp <= 0x2B81F  # Extension D
        or 0x2B820 <= cp <= 0x2CEAF  # Extension E
        or 0x2CEB0 <= cp <= 0x2EBEF  # Extension F
        or 0x30000 <= cp <= 0x3134F  # Extension G
        or cp == 0x3007  # 〇
    )


def _is_basic_chinese_headword(word: str) -> bool:
    """
    Keep only headwords made of CJK ideographs (plus 〇).
    This drops romanizations, Latin-script borrowings like 'GDP', and punctuation-heavy entries.
    """
    if not word or not word.strip():
        return False
    w = word.strip()
    return all(_is_cjk_ideograph(ch) for ch in w)


def _all_pronunciations(obj: dict, lang_code: str) -> list[str | None]:
    """All distinct pronunciations for this entry; one per sound variant. Returns [None] if none."""
    sounds = obj.get("sounds") or []
    seen: set[str] = set()
    out: list[str | None] = []
    for s in sounds:
        if not isinstance(s, dict):
            continue
        if lang_code == "zh":
            raw = s.get("zh_pron")
            if isinstance(raw, str) and raw.strip():
                # e.g. "shǒuyè (Mandarin)" → take first token
                p = raw.strip().split()[0].strip() or raw.strip()
                if p and p not in seen:
                    seen.add(p)
                    out.append(p)
                continue
        ipa = s.get("ipa")
        if isinstance(ipa, str) and ipa.strip() and ipa not in seen:
            seen.add(ipa)
            out.append(ipa)
    return out if out else [None]


def _index_key_and_phrase(word: str, lang_code: str) -> tuple[str, bool]:
    """Index key (leading_key) and whether this headword is a phrase. EN: key = first word; ZH: key = first character."""
    if not word or not word.strip():
        return "", True
    w = word.strip()
    if lang_code == "zh":
        return w[0], len(w) > 1
    # EN: first word (space-separated)
    first = w.split()[0] if w else ""
    return first.lower() if first else "", " " in w


def _glosses_from_sense(sense: dict) -> list[str]:
    """Extract English gloss strings from one sense."""
    out: list[str] = []
    for g in sense.get("glosses") or []:
        if isinstance(g, dict) and g.get("gloss"):
            out.append(g["gloss"].strip())
        elif isinstance(g, str) and g.strip():
            out.append(g.strip())
    return out


def _unique_glosses(gloss_list: list[str]) -> list[str]:
    """Deduplicate glosses (exact match after strip); preserve order."""
    seen: set[str] = set()
    out: list[str] = []
    for g in gloss_list:
        n = g.strip()
        if n and n not in seen:
            seen.add(n)
            out.append(n)
    return out


def _build_short_and_full(senses: list) -> tuple[str, str]:
    """
    From sense dicts, build short_definition (first gloss, truncated) and
    full_definition (numbered list of unique glosses; tags omitted).
    """
    all_glosses: list[str] = []
    for sense in senses:
        if not isinstance(sense, dict):
            continue
        all_glosses.extend(_glosses_from_sense(sense))
    unique = _unique_glosses(all_glosses)
    if not unique:
        return "", ""
    short_gloss = unique[0]
    short = (
        short_gloss
        if len(short_gloss) <= _SHORT_DEF_MAX
        else short_gloss[:_SHORT_DEF_MAX].rstrip() + "…"
    )
    numbered = [f"{i + 1}. {g}" for i, g in enumerate(unique)]
    full = " ".join(numbered)
    return short, full


def _pos_label(pos: str) -> str:
    """Normalize POS to our schema (noun, verb, adj, adv where possible)."""
    p = (pos or "").lower()
    if p in ("noun", "verb", "adj", "adjective", "adv", "adverb"):
        return "adj" if p in ("adjective", "adj") else "adv" if p in ("adverb", "adv") else p
    return pos or ""


def parse_kaikki_json_line(line: str, lang_code: str = "en") -> list[DetailEntry]:
    """
    Parse one JSONL line from Kaikki/Wiktextract. Returns entries for the given language.
    One entry per (word, pos); multiple senses merged into full_definition.
    """
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return []
    if obj.get("lang_code") != lang_code and obj.get("lang") != lang_code:
        return []
    word = obj.get("word") or obj.get("head", "")
    if not word or not isinstance(word, str):
        return []
    if lang_code == "en" and not _is_basic_english_headword(word):
        return []
    if lang_code == "zh" and not _is_basic_chinese_headword(word):
        return []
    leading_key, is_phrase = _index_key_and_phrase(word, lang_code)
    prons = _all_pronunciations(obj, lang_code)
    entries: list[DetailEntry] = []
    sort_key = word.lower() if lang_code == "en" else word

    sections: list[tuple[str, list]] = []
    if obj.get("pos_sections"):
        for sec in obj["pos_sections"]:
            if isinstance(sec, dict) and sec.get("senses"):
                sections.append((sec.get("pos") or "", sec["senses"]))
    if not sections and obj.get("senses"):
        sections.append((obj.get("pos") or "", obj["senses"]))

    for pos, senses in sections:
        short, full = _build_short_and_full(senses)
        if not short and not full:
            continue
        for pron in prons:
            entries.append(
                DetailEntry(
                    headword=word,
                    sort_key=sort_key,
                    pronunciation=pron,
                    short_definition=short or None,
                    full_definition=full or None,
                    part_of_speech=_pos_label(pos) or None,
                    leading_key=leading_key or None,
                    is_phrase=is_phrase,
                )
            )
    return entries


def parse_kaikki_sense_line(line: str, lang_code: str = "en") -> list[DetailEntry]:
    """
    Parse one JSONL line from Kaikki postprocessed format (one sense per line).
    Returns 0 or 1 DetailEntry. lang_code used for language filter and index_key/is_phrase.
    """
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return []
    word = obj.get("head") or obj.get("word") or ""
    if not word or not isinstance(word, str):
        return []
    if lang_code == "en" and not _is_basic_english_headword(word):
        return []
    if lang_code == "zh" and not _is_basic_chinese_headword(word):
        return []
    leading_key, is_phrase = _index_key_and_phrase(word, lang_code)
    gloss = obj.get("gloss")
    if not gloss and "glosses" in obj:
        gl = obj.get("glosses") or []
        gloss = gl[0] if gl else None
        if isinstance(gloss, dict):
            gloss = gloss.get("gloss")
    if not gloss or not isinstance(gloss, str):
        return []
    pos = _pos_label(obj.get("pos") or "")
    pron = None
    if lang_code == "zh" and obj.get("zh_pron"):
        pron = obj["zh_pron"] if isinstance(obj["zh_pron"], str) else None
    elif obj.get("ipa"):
        pron = obj["ipa"] if isinstance(obj["ipa"], str) else None
    elif obj.get("sounds"):
        for s in obj["sounds"] or []:
            if isinstance(s, dict) and s.get("ipa"):
                pron = s["ipa"]
                break
    short = gloss if len(gloss) <= _SHORT_DEF_MAX else gloss[:_SHORT_DEF_MAX].rstrip() + "…"
    sort_key = word.lower() if lang_code == "en" else word
    return [
        DetailEntry(
            headword=word,
            sort_key=sort_key,
            pronunciation=pron,
            short_definition=short,
            full_definition=gloss.strip(),
            part_of_speech=pos or None,
            leading_key=leading_key or None,
            is_phrase=is_phrase,
        )
    ]


def _stream_entries_from_lines(
    lines: Iterable[str],
    lang_code: str,
    max_entries: int | None,
) -> Iterator[DetailEntry]:
    """Yield DetailEntry from JSONL lines; stop after max_entries if set.
    Tries raw (word-per-line) format first, then postprocessed (sense-per-line) format.
    """
    count = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        entries = parse_kaikki_json_line(line, lang_code=lang_code)
        if not entries:
            entries = parse_kaikki_sense_line(line, lang_code=lang_code)
        for entry in entries:
            yield entry
            count += 1
            if max_entries is not None and count >= max_entries:
                return


def stream_kaikki_entries(
    path: Path,
    lang_code: str = "en",
    max_entries: int | None = None,
):
    """Stream DetailEntry from a Kaikki JSONL file (plain or .gz)."""
    import gzip

    if path.suffix == ".gz":
        f = gzip.open(path, "rt", encoding="utf-8")
    else:
        f = path.open("r", encoding="utf-8")
    with f as fp:
        yield from _stream_entries_from_lines(fp, lang_code, max_entries)
