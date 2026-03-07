"""CC-CEDICT source download and parsing (Chinese-English).

Unified structure: single-character entries become **heads**; multi-character
entries become **phrases** grouped under the leading character's head.
"""

from __future__ import annotations

import re
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from ..models import HeadEntry, PhraseItem

DEFAULT_CEDICT_URL = "https://www.mdbg.net/chinese/export/cedict/cedict_1_0_ts_utf-8_mdbg.txt.gz"

_CEDICT_LINE = re.compile(r"^(\S+)\s+(\S+)\s+\[([^\]]+)\]\s+/(.+)/\s*$")

_PINYIN_TONES: dict[str, tuple[str, str, str, str]] = {
    "a": ("ā", "á", "ǎ", "à"),
    "e": ("ē", "é", "ě", "è"),
    "i": ("ī", "í", "ǐ", "ì"),
    "o": ("ō", "ó", "ǒ", "ò"),
    "u": ("ū", "ú", "ǔ", "ù"),
    "ü": ("ǖ", "ǘ", "ǚ", "ǜ"),
}

_SHORT_DEF_MAX_CHARS = 100


def _pinyin_syllable_to_accent(syllable: str) -> str:
    if not syllable or syllable[-1] not in "12345":
        return syllable
    tone = int(syllable[-1])
    base = syllable[:-1].replace("u:", "ü").replace("v", "ü")
    if tone == 5:
        return base
    if tone not in (1, 2, 3, 4):
        return syllable
    lower = base.lower()
    idx = -1
    for target in ("a", "o", "e"):
        if target in lower:
            idx = lower.rindex(target)
            break
    if idx < 0 and "iu" in lower:
        idx = lower.index("u")
    if idx < 0:
        for target in ("i", "u", "ü"):
            if target in lower:
                idx = lower.rindex(target)
                break
    if idx < 0:
        return syllable
    v = base[idx]
    v_lower = v.lower() if v != "ü" else "ü"
    tones = _PINYIN_TONES.get(v_lower)
    if not tones:
        return syllable
    accented = tones[tone - 1]
    if v.isupper():
        accented = accented.upper()
    result = base[:idx] + accented + base[idx + 1 :]
    if base and base[0].isupper():
        result = result[0].upper() + result[1:]
    return result


def pinyin_numbered_to_accent(pinyin_raw: str) -> str:
    """``'ni3 hao3 ma5'`` → ``'nǐ hǎo ma'``."""
    parts = pinyin_raw.strip().split()
    return " ".join(p if p in (".", "·", ",", " ") else _pinyin_syllable_to_accent(p) for p in parts)


def _infer_pos(defn: str) -> str | None:
    s = defn.strip()
    if not s:
        return None
    lo = s.lower()
    if lo.startswith("to ") and " " in s[3:]:
        return "verb"
    if "CL:" in s or "classifier for " in lo:
        return "cl."
    if lo.startswith(("abbr.", "abbreviation")):
        return "abbr."
    if "proper noun" in lo or "surname" in lo or "given name" in lo:
        return "prop."
    if "interjection" in lo or "exclamation" in lo:
        return "interj."
    if "prefix" in lo or "suffix" in lo:
        return "affix"
    return None


def _short_def(first_gloss: str) -> str:
    short = first_gloss.strip()
    if len(short) <= _SHORT_DEF_MAX_CHARS:
        return short
    return short[:_SHORT_DEF_MAX_CHARS].rstrip() + "…"


def _normalize_pinyin_for_sort(pinyin: str) -> str:
    return " ".join(pinyin.lower().split())


def download_source(url: str, target_file: Path) -> Path:
    target_file.parent.mkdir(parents=True, exist_ok=True)
    if target_file.exists():
        return target_file
    with urllib.request.urlopen(url, timeout=120) as response:
        target_file.write_bytes(response.read())
    return target_file


def _is_gzip(path: Path) -> bool:
    with open(path, "rb") as f:
        return f.read(2) == b"\x1f\x8b"


@dataclass(frozen=True, slots=True)
class _RawEntry:
    headword: str
    pinyin_raw: str
    pinyin_display: str
    sort_key: str
    defs: list[str]
    pos: str | None


def _parse_raw(
    path: Path,
    *,
    use_simplified: bool = True,
) -> list[_RawEntry]:
    """Parse a CEDICT file into raw entries (before head/phrase split)."""
    import gzip

    if _is_gzip(path):
        with gzip.open(path, "rt", encoding="utf-8") as gz:
            text = gz.read()
    else:
        text = path.read_text(encoding="utf-8")

    entries: list[_RawEntry] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = _CEDICT_LINE.match(line)
        if not m:
            continue
        trad, simp, pinyin_raw, defs_str = m.groups()
        headword = simp if use_simplified else trad
        defs = [d.strip() for d in defs_str.split("/") if d.strip()]
        if not defs:
            continue
        entries.append(
            _RawEntry(
                headword=headword,
                pinyin_raw=pinyin_raw.strip(),
                pinyin_display=pinyin_numbered_to_accent(pinyin_raw),
                sort_key=_normalize_pinyin_for_sort(pinyin_raw.strip()),
                defs=defs,
                pos=_infer_pos(defs[0]) or _infer_pos(" / ".join(defs)),
            )
        )
    return entries


def parse_file(
    path: Path,
    *,
    use_simplified: bool = True,
) -> list[HeadEntry]:
    """Parse a CEDICT file into unified ``HeadEntry`` list.

    Single-character entries become heads; multi-character entries
    become ``PhraseItem`` objects attached to the matching head.
    """
    raw = _parse_raw(path, use_simplified=use_simplified)

    heads_raw: list[_RawEntry] = []
    phrases_raw: list[_RawEntry] = []
    for r in raw:
        if len(r.headword) == 1:
            heads_raw.append(r)
        else:
            phrases_raw.append(r)

    # Build phrase items grouped by leading character
    phrase_bucket: dict[str, list[PhraseItem]] = defaultdict(list)
    for p in phrases_raw:
        leading = p.headword[0]
        full = " / ".join(p.defs) if len(p.defs) > 1 else p.defs[0]
        defn = f"[{p.pinyin_display}] {full}"
        phrase_bucket[leading].append(PhraseItem(form=p.headword, definition=defn))

    # Build head entries, attaching phrases
    heads: list[HeadEntry] = []
    seen_leading: set[str] = set()
    for r in heads_raw:
        first_gloss = r.defs[0].split(";")[0].strip()
        full = " / ".join(r.defs) if len(r.defs) > 1 else r.defs[0]
        phrases = tuple(phrase_bucket.get(r.headword, ()))
        # Only attach phrases to the first head for this character to avoid duplication
        if r.headword in seen_leading:
            phrases = ()
        else:
            seen_leading.add(r.headword)
        heads.append(
            HeadEntry(
                headword=r.headword,
                sort_key=r.sort_key,
                leading_key=r.headword,
                pronunciation=r.pinyin_display,
                part_of_speech=r.pos,
                short_definition=_short_def(first_gloss),
                full_definition=full,
                phrases=phrases,
            )
        )

    return heads
