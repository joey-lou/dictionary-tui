"""Shared text helpers for ETL transforms."""

from __future__ import annotations

import re


def truncate_at_word_boundary(text: str, max_chars: int, ellipsis: str = "\u2026") -> str:
    """Truncate at word boundary; append ellipsis."""
    if len(text) <= max_chars:
        return text
    budget = max_chars - len(ellipsis)
    if budget <= 0:
        return ellipsis[: max_chars - 1] + ellipsis[-1] if max_chars >= 1 else ""
    cut = text[: budget + 1]
    last_space = cut.rfind(" ")
    cut = cut[:last_space].rstrip() if last_space > budget // 2 else cut[:budget].rstrip()
    return cut + ellipsis


def strip_legacy_markers(text: str) -> str:
    """Remove leading Defn:, [Obs.], [R.], etc. from definition text."""
    if not text or not text.strip():
        return text
    s = re.sub(r"^(?:Defn:\s*)+", "", text.strip()).strip()
    s = re.sub(r"\s*\[Obs\.?\]\s*", " ", s)
    s = re.sub(r"\s*\[R\.?\]\s*", " ", s)
    return " ".join(s.split())


def normalize_whitespace(text: str) -> str:
    """Collapse runs of whitespace to single space, strip edges."""
    if not text:
        return text
    return " ".join(text.split())


def split_senses_on_numbering(text: str) -> list[str]:
    """Split definition text into senses by 1. 2. or (a) (b) numbering."""
    if not text or not text.strip():
        return []
    parts = re.split(r"\s+(?=\d+\.\s|\d+\.\s*\S|\s*\([a-z]\)\s)", text.strip())
    return [p.strip() for p in parts if p.strip()]


def strip_all_caps_headings(text: str) -> str:
    """Remove or trim ALL CAPS token runs (e.g. 'ABATIS; ABATTIS') from definition body."""
    if not text or not text.strip():
        return text
    # Match ALL CAPS words/semicolon runs that look like headword lists
    s = re.sub(r"\s+[A-Z][A-Z\-'\s;]{2,60}(?=\s|\.|$)", " ", text)
    return " ".join(s.split())


def normalize_escaped_quotes(text: str) -> str:
    """Replace legacy \\\" and similar with plain quote; remove * diacritic markers."""
    if not text:
        return text
    s = text.replace('\\"', '"').replace("\\'", "'")
    return re.sub(r"\*([a-zA-Z])", r"\1", s)


def first_definition_before_all_caps(text: str) -> str:
    """Keep only the first definition; strip content after ALL CAPS headword line (sub-entry leakage)."""
    if not text or not text.strip():
        return text
    # Find first line that is entirely ALL CAPS (next headword), possibly with ; and spaces
    for m in re.finditer(r"\n\s*([A-Z][A-Z\-'\s;]{3,50})\s*(?=\n|$)", text):
        line = m.group(1).strip()
        if re.match(r"^[A-Z][A-Z\-'\s;]+$", line) and (" " in line or ";" in line or len(line) > 4):
            return text[: m.start()].strip()
    return text


# Chinese single-char POS to English (for packs that may have raw 名/动/形 etc.)
_POS_ZH_TO_EN: dict[str, str] = {
    "名": "noun",
    "动": "verb",
    "形": "adj",
    "副": "adv",
    "数": "num",
    "量": "measure",
    "代": "pron",
    "叹": "interj",
    "助": "particle",
    "连": "conj",
    "介": "prep",
}


def normalize_pos_style(pos: str | None) -> str | None:
    """Normalize POS: strip trailing period; map Chinese single-char to English."""
    if not pos or not pos.strip():
        return pos
    s = pos.strip().rstrip(".")
    if not s:
        return pos
    if len(s) == 1 and s in _POS_ZH_TO_EN:
        return _POS_ZH_TO_EN[s]
    return s


# --- Xinhua-specific helpers ---

# Known corrupt or unencodable character replacements (longer first for correct order)
XINHUA_CHAR_FIXES: list[tuple[str, str]] = [
    ("腰瓿thaka", "pathaka"),  # 呗: 梵语 腰瓿thaka (corrupt) -> pathaka (Sanskrit)
    ("腰瓿", "pathaka"),
    ("卡籽", "卡住"),  # 别: 用东西卡籽门～住 (typo; 籽 = seed)
]


# Placeholder ? often appears for missing character; replace with full-width or leave
def xinhua_fix_placeholder_and_corrupt(text: str) -> str:
    """Replace known corrupt runs and optional placeholder ? in Xinhua definitions."""
    if not text:
        return text
    for bad, good in XINHUA_CHAR_FIXES:
        text = text.replace(bad, good)
    return text


def xinhua_short_def_from_first_sense(full: str | None, short: str | None, headword: str) -> str | None:
    """Derive short_definition from first meaningful sense; skip empty or circular (just headword)."""
    if not full or not full.strip():
        return short
    first = full.split("。")[0].strip() if "。" in full else full.strip()
    first = first.split("；")[0].strip() if "；" in first else first
    if not first or first == headword or len(first) < 2:
        return short if short and short.strip() and short != headword else None
    return first[:60].rstrip() + ("…" if len(first) > 60 else "")


def xinhua_add_newlines_in_full_def(text: str) -> str:
    """Insert newlines between 又見, classical quote, and modern senses for readability."""
    if not text or not text.strip():
        return text
    s = re.sub(r"(又見[^。]+。)", r"\1\n", text)
    s = re.sub(r"([。；])\s*(\d+[\.．])", r"\1\n\2", s)
    return s.strip()


_CIRCLE_NUM = "①②③④⑤⑥⑦⑧⑨⑩"
_PAREN_NUM = "⑴⑵⑶⑷⑸"
# Leading "pinyin+digit." e.g. bié1. in variant entries (別: "bié1.同\"别\"")
_LEADING_PINYIN_NUM_RE = re.compile(r"^[a-zA-ZüÜāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜɡ]+\d+\.\s*")
# After ShortDefFromFirstSense, short_def may start with headword+pinyin+digit. (e.g. 別bié1.)
_HEADWORD_PINYIN_NUM_RE = re.compile(r"^.[a-zA-ZüÜāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜɡ]+\d+\.\s*")


def xinhua_normalize_short_def_leading(text: str, headword: str) -> str:
    """Replace leading 'headword+pinyin+digit.' (e.g. 別bié1.) with '1. ' in short defs."""
    if not text or not text.strip() or not headword:
        return text
    s = text.strip()
    if not s.startswith(headword):
        return text
    s = _HEADWORD_PINYIN_NUM_RE.sub("1. ", s, count=1)
    return s.strip()


def xinhua_normalize_numbering(text: str) -> str:
    """Normalize numbering to 1. 2. 3. style; strip leading pinyin+number (e.g. bié1. → 1.)."""
    if not text or not text.strip():
        return text
    s = _LEADING_PINYIN_NUM_RE.sub("1. ", text.strip(), count=1)
    for i, c in enumerate(_CIRCLE_NUM, 1):
        s = s.replace(c, f"{i}. ")
    for i, c in enumerate(_PAREN_NUM, 1):
        s = s.replace(c, f"{i}. ")
    s = re.sub(r"(\d)[．]", r"\1. ", s)
    return " ".join(s.split())
