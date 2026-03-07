"""chinese-xinhua source (pwxcoo/chinese-xinhua): ZH-ZH dictionary.

Head entries come from ``word.json`` (single characters with pinyin).
Phrases come from ``idiom.json`` (成语) and ``ci.json`` (词语), grouped
under their leading character's head.
"""

from __future__ import annotations

import json
import re
import urllib.request
from collections import defaultdict
from pathlib import Path

from ..models import HeadEntry, PhraseItem

_BASE_URL = "https://raw.githubusercontent.com/pwxcoo/chinese-xinhua/master/data"
_SHORT_DEF_MAX = 60

# Grammar POS markers found in angle brackets 〈...〉
_GRAMMAR_POS: dict[str, str] = {
    "名": "n.",
    "动": "v.",
    "形": "adj.",
    "副": "adv.",
    "数": "num.",
    "量": "cl.",
    "代": "pron.",
    "叹": "interj.",
    "助": "part.",
    "连": "conj.",
    "介": "prep.",
    "拟声": "onom.",
    "语气": "modal",
    "前缀": "prefix",
}
# Combined POS markers (e.g. "形、副")
_COMBINED_SEP = re.compile(r"[、，,]")

_POS_RE = re.compile(r"〈([^〉]+)〉")
_ETYM_KEYWORDS = {"形声", "象形", "会意", "指事", "假借", "转注"}
_CITATION_RE = re.compile(r"--[《〈].*?[》〉](?:。)?")
_BENYI_RE = re.compile(r"本义[:：]?\s*([^)）。;；\n]+)")


def _download_json(name: str, cache_dir: Path) -> list[dict]:
    path = cache_dir / name
    if not path.exists():
        cache_dir.mkdir(parents=True, exist_ok=True)
        url = f"{_BASE_URL}/{name}"
        with urllib.request.urlopen(url, timeout=120) as resp:
            path.write_bytes(resp.read())
    return json.loads(path.read_text(encoding="utf-8"))


def _pinyin_sort_key(pinyin: str) -> str:
    return pinyin.lower().strip()


def _extract_pos(text: str) -> str | None:
    """Extract grammar POS from 〈...〉 markers near the start of the text."""
    m = _POS_RE.search(text[:50])
    if not m:
        return None
    raw = m.group(1).strip()
    if raw in _GRAMMAR_POS:
        return _GRAMMAR_POS[raw]
    parts = _COMBINED_SEP.split(raw)
    mapped = [_GRAMMAR_POS[p.strip()] for p in parts if p.strip() in _GRAMMAR_POS]
    return "/".join(mapped) if mapped else None


_LEADING_PINYIN_RE = re.compile(r"^[a-zA-ZüÜāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜɡ]+\d?\s+")


def _strip_leading_char(text: str, char: str) -> str:
    """Remove the headword character (and trailing inline pinyin) from the start."""
    s = text.lstrip()
    if s.startswith(char):
        s = s[len(char) :]
    s = s.lstrip()
    # Strip inline pinyin like "ā 1.日本和字" → "1.日本和字"
    s = _LEADING_PINYIN_RE.sub("", s)
    return s.lstrip()


def _find_balanced_paren(text: str, start: int) -> int | None:
    """Find the index past the closing ')' matching '(' at *start*."""
    if start >= len(text) or text[start] != "(":
        return None
    depth = 0
    for i in range(start, min(start + 300, len(text))):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return i + 1
    return None


def _extract_etymology(text: str) -> tuple[str | None, str, str | None]:
    """Find and remove the etymology parenthetical from *text*.

    Returns ``(benyi, remaining_text, etym_content)``.
    """
    idx = text.find("(")
    if idx < 0 or idx > 80:
        return None, text, None
    end = _find_balanced_paren(text, idx)
    if end is None:
        return None, text, None
    content = text[idx + 1 : end - 1]
    if not any(kw in content for kw in _ETYM_KEYWORDS):
        return None, text, None
    benyi_m = _BENYI_RE.search(content)
    benyi = benyi_m.group(1).strip() if benyi_m else None
    remaining = (text[:idx] + text[end:]).strip()
    return benyi, remaining, content


def _clean_definition(explanation: str, char: str) -> tuple[str, str]:
    """Extract a clean (short_definition, full_definition) from raw explanation.

    Returns (short, full) where short is a concise summary and full is the
    cleaned-up complete text.
    """
    text = _strip_leading_char(explanation, char)

    # Strip POS marker
    text = _POS_RE.sub("", text, count=1).lstrip()

    # Strip etymology parenthetical, capture "本义" if present
    benyi, text, _ = _extract_etymology(text)
    text = text.lstrip()

    # Split into paragraphs (double-newline or multiple-space runs)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n|\n\n", text) if p.strip()]
    full = " ".join(text.split()).strip()

    # Use first paragraph for short definition candidate
    first_para = paragraphs[0] if paragraphs else full
    first_para = " ".join(first_para.split()).strip()
    short_candidate = _CITATION_RE.sub("", first_para).strip()

    short = _first_meaningful_segment(short_candidate, benyi)

    if len(short) > _SHORT_DEF_MAX:
        short = short[: _SHORT_DEF_MAX - 1].rstrip() + "…"

    if not full:
        full = explanation.strip()
    if not short:
        short = full[:_SHORT_DEF_MAX] if full else ""

    return short, full


def _first_meaningful_segment(text: str, benyi: str | None) -> str:
    """Pick the first useful fragment from cleaned definition text."""
    if not text:
        return benyi or ""

    # If text starts with "同本义" or similar references, use benyi
    if text.startswith("同本义") and benyi:
        return benyi

    # Split on sentence boundaries and take first non-empty part
    parts = re.split(r"[。；\n]", text)
    for part in parts:
        cleaned = part.strip()
        # Skip fragments that are just references like "又如..." or "如..."
        if cleaned and not cleaned.startswith(("又如", "如")):
            # Remove leading "同本义。" prefix when followed by actual content
            cleaned = re.sub(r"^同本义[。.]?\s*", "", cleaned)
            if cleaned:
                return cleaned

    return benyi or (parts[0].strip() if parts else text[:_SHORT_DEF_MAX])


def parse_xinhua(
    cache_dir: Path,
    *,
    include_ci: bool = True,
) -> list[HeadEntry]:
    """Build ZH-ZH ``HeadEntry`` list from chinese-xinhua data."""
    word_data = _download_json("word.json", cache_dir)
    idiom_data = _download_json("idiom.json", cache_dir)
    ci_data = _download_json("ci.json", cache_dir) if include_ci else []

    heads: list[HeadEntry] = []
    seen_chars: set[str] = set()

    for obj in word_data:
        char = (obj.get("word") or "").strip()
        if not char or len(char) != 1:
            continue
        pinyin = (obj.get("pinyin") or "").strip()
        explanation = (obj.get("explanation") or "").strip()
        if not explanation:
            continue

        pos = _extract_pos(explanation)
        short, full = _clean_definition(explanation, char)

        heads.append(
            HeadEntry(
                headword=char,
                sort_key=_pinyin_sort_key(pinyin) if pinyin else char,
                leading_key=char,
                pronunciation=pinyin or None,
                part_of_speech=pos,
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
        explanation = " ".join((obj.get("explanation") or "").split()).strip()
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
        explanation = " ".join((obj.get("explanation") or "").split()).strip()
        if not explanation:
            continue
        leading = ci[0]
        phrase_bucket[leading].append(PhraseItem(form=ci, definition=explanation))

    # --- Attach phrases to heads ---
    final: list[HeadEntry] = []
    attached_keys: set[str] = set()
    for h in heads:
        phrases = tuple(phrase_bucket.get(h.leading_key, ()))
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
