"""CC-CEDICT source download and parsing (Chinese, pinyin index, English definitions)."""

from __future__ import annotations

import re
import urllib.request
from pathlib import Path

from ..models import DetailEntry

# MDBG; if this URL returns HTML, download from cc-cedict.org or use --source-file
DEFAULT_CEDICT_URL = "https://www.mdbg.net/chinese/export/cedict/cedict_1_0_ts_utf-8_mdbg.txt.gz"

# Line format: traditional simplified [pinyin] /def1/def2/
_CEDICT_LINE = re.compile(r"^(\S+)\s+(\S+)\s+\[([^\]]+)\]\s+/(.+)/\s*$")

# Tone mark (1–4) per vowel; tone 5 = neutral, no mark.
_PINYIN_TONES: dict[str, tuple[str, str, str, str]] = {
    "a": ("ā", "á", "ǎ", "à"),
    "e": ("ē", "é", "ě", "è"),
    "i": ("ī", "í", "ǐ", "ì"),
    "o": ("ō", "ó", "ǒ", "ò"),
    "u": ("ū", "ú", "ǔ", "ù"),
    "ü": ("ǖ", "ǘ", "ǚ", "ǜ"),
}

# Max length for short_definition in list view; full_definition is unabridged.
_SHORT_DEF_MAX_CHARS = 100


def _pinyin_syllable_to_accent(syllable: str) -> str:
    """Convert one syllable from numbered (e.g. 'hao3') to accented (e.g. 'hǎo'). Preserves cap."""
    if not syllable or syllable[-1] not in "12345":
        return syllable
    tone = int(syllable[-1])
    base = syllable[:-1].replace("u:", "ü").replace("v", "ü")
    if tone == 5:
        return base  # neutral tone: no accent
    if tone not in (1, 2, 3, 4):
        return syllable
    # Which vowel gets the tone: a > o > e > iu > i > u > ü
    lower = base.lower()
    idx = -1
    if "a" in lower:
        idx = lower.rindex("a")
    elif "o" in lower:
        idx = lower.rindex("o")
    elif "e" in lower:
        idx = lower.rindex("e")
    elif "iu" in lower:
        idx = lower.index("u")
    elif "i" in lower:
        idx = lower.rindex("i")
    elif "u" in lower:
        idx = lower.rindex("u")
    elif "ü" in lower:
        idx = lower.rindex("ü")
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


def _pinyin_numbered_to_accent(pinyin_raw: str) -> str:
    """Convert full pinyin string from numbered to accented (e.g. 'ni3 hao3 ma5' -> 'nǐ hǎo ma')."""
    parts = pinyin_raw.strip().split()
    out = []
    for part in parts:
        # Middle dot or punctuation: leave as-is
        if part in (".", "·", ",", " "):
            out.append(part)
            continue
        out.append(_pinyin_syllable_to_accent(part))
    return " ".join(out)


def _infer_part_of_speech(defn: str) -> str | None:
    """Infer a simple classification from CEDICT definition text (they don't use POS tags)."""
    s = defn.strip()
    if not s:
        return None
    s_lower = s.lower()
    if s_lower.startswith("to ") and " " in s[3:]:
        return "v."
    if "CL:" in s or "classifier for " in s_lower:
        return "cl."
    if s_lower.startswith("abbr.") or s_lower.startswith("abbreviation"):
        return "abbr."
    if "(slang)" in s_lower or "(colloquial)" in s_lower:
        return "slang"
    if "(dialect)" in s_lower:
        return "dial."
    if "(Tw)" in s or "(Taiwan)" in s_lower:
        return "Tw."
    if "(informal)" in s_lower:
        return "inf."
    if "interjection" in s_lower or "exclamation" in s_lower:
        return "interj."
    if "prefix" in s_lower or "suffix" in s_lower:
        return "affix"
    if "proper noun" in s_lower or "surname" in s_lower or "given name" in s_lower:
        return "prop."
    return None


def _short_definition(first_gloss: str, full_text: str) -> str:
    """First gloss only; truncate if still long so list view stays readable."""
    short = first_gloss.strip()
    if len(short) <= _SHORT_DEF_MAX_CHARS:
        return short
    return short[:_SHORT_DEF_MAX_CHARS].rstrip() + "…"


def download_source(url: str, target_file: Path) -> Path:
    """Download CEDICT file to ``target_file`` if missing."""
    target_file.parent.mkdir(parents=True, exist_ok=True)
    if target_file.exists():
        return target_file
    with urllib.request.urlopen(url, timeout=120) as response:
        body = response.read()
    target_file.write_bytes(body)
    return target_file


def _normalize_pinyin_for_sort(pinyin: str) -> str:
    """Normalize pinyin for stable sort: lowercase, collapse spaces, keep tone numbers."""
    return " ".join(pinyin.lower().split())


def _is_gzip(path: Path) -> bool:
    """True if file starts with gzip magic bytes."""
    with open(path, "rb") as f:
        return f.read(2) == b"\x1f\x8b"


def parse_file(
    path: Path,
    *,
    use_simplified: bool = True,
    max_entries: int | None = None,
) -> list[DetailEntry]:
    """Parse a CEDICT file (plain text or .gz). Detects gzip by magic bytes."""
    import gzip

    text: str
    if _is_gzip(path):
        text = gzip.open(path, "rt", encoding="utf-8").read()
    else:
        text = path.read_text(encoding="utf-8")

    return parse_lines(
        text.splitlines(),
        use_simplified=use_simplified,
        max_entries=max_entries,
    )


def parse_lines(
    lines: list[str],
    *,
    use_simplified: bool = True,
    max_entries: int | None = None,
) -> list[DetailEntry]:
    """Parse CEDICT-format lines into DetailEntry list."""
    entries: list[DetailEntry] = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = _CEDICT_LINE.match(line)
        if not m:
            continue
        trad, simp, pinyin_raw, defs_str = m.groups()
        headword = simp if use_simplified else trad
        sort_key = _normalize_pinyin_for_sort(pinyin_raw.strip())
        # Display pronunciation with tone marks (accented), not raw numbers.
        pinyin_display = _pinyin_numbered_to_accent(pinyin_raw)
        defs = [d.strip() for d in defs_str.split("/") if d.strip()]
        if not defs:
            continue
        first_gloss = defs[0].split(";")[0].strip()
        full = " / ".join(defs) if len(defs) > 1 else defs[0]
        short = _short_definition(first_gloss, full)
        pos = _infer_part_of_speech(defs[0]) or _infer_part_of_speech(full)
        entries.append(
            DetailEntry(
                headword=headword,
                sort_key=sort_key,
                pronunciation=pinyin_display,
                short_definition=short,
                full_definition=full,
                part_of_speech=pos,
            )
        )
        if max_entries is not None and len(entries) >= max_entries:
            break
    return entries
