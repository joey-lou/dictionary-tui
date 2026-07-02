"""Extract HeadEntry list from chinese-xinhua data (word.json, idiom.json, ci.json)."""

from __future__ import annotations

import json
import re
import urllib.request
from collections import defaultdict
from pathlib import Path

from common.etl.base import Extractor
from common.models import HeadEntry, PhraseItem

_BASE_URL = "https://raw.githubusercontent.com/pwxcoo/chinese-xinhua/master/data"
_SHORT_DEF_MAX = 60

# Output English POS for UI consistency (UI is in English).
_GRAMMAR_POS: dict[str, str] = {
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
    "拟声": "onomat.",
    "语气": "particle",
    "前缀": "prefix",
}
_COMBINED_SEP = re.compile(r"[、，,]")
_POS_RE = re.compile(r"〈([^〉]+)〉")
_ETYM_KEYWORDS = {"形声", "象形", "会意", "指事", "假借", "转注"}
_CITATION_RE = re.compile(r"--[《〈].*?[》〉](?:。)?")
_BENYI_RE = re.compile(r"本义[:：]?\s*([^)）。;；\n]+)")
_BENYI_POS_RE = re.compile(r"本义[:：]?\s*(\S*?(?:叹|数|名|代|副|量|助|连|介)词)")
_INLINE_POS_RE = re.compile(
    r"\S[a-zA-Zāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜɡ]+\d?\s*"
    r"(叹词|名词|动词|形容词|副词|数词|量词|代词|连词|介词|助词)"
)
_CI_TO_POS: dict[str, str] = {
    "叹词": "interj",
    "名词": "noun",
    "动词": "verb",
    "形容词": "adj",
    "副词": "adv",
    "数词": "num",
    "量词": "measure",
    "代词": "pron",
    "连词": "conj",
    "介词": "prep",
    "助词": "particle",
}
# Fallback: find first occurrence of 名词/动词/... in definition text (no angle brackets).
_FREETEXT_POS_RE = re.compile(r"(名词|动词|形容词|副词|数词|量词|代词|连词|介词|助词|叹词)")
_LEADING_PINYIN_RE = re.compile(r"^[a-zA-ZüÜāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜɡ]+\d?\s+")


def _download_json(name: str, cache_dir: Path) -> list[dict]:
    path = cache_dir / name
    if not path.exists():
        cache_dir.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(f"{_BASE_URL}/{name}", timeout=120) as resp:
            path.write_bytes(resp.read())
    return json.loads(path.read_text(encoding="utf-8"))


def _pinyin_sort_key(pinyin: str) -> str:
    return pinyin.lower().strip()


def _extract_pos(text: str) -> str | None:
    m = _POS_RE.search(text[:50])
    if m:
        raw = m.group(1).strip()
        if raw in _GRAMMAR_POS:
            return _GRAMMAR_POS[raw]
        parts = _COMBINED_SEP.split(raw)
        mapped = [_GRAMMAR_POS[p.strip()] for p in parts if p.strip() in _GRAMMAR_POS]
        if mapped:
            return "/".join(mapped)
    m = _BENYI_POS_RE.search(text[:300])
    if m:
        ci = m.group(1)
        for suffix, pos in _CI_TO_POS.items():
            if ci.endswith(suffix):
                return pos
    m = _INLINE_POS_RE.search(text[:300])
    if m:
        ci = m.group(1)
        if ci in _CI_TO_POS:
            return _CI_TO_POS[ci]
    m = _FREETEXT_POS_RE.search(text[:300])
    if m:
        ci = m.group(1)
        if ci in _CI_TO_POS:
            return _CI_TO_POS[ci]
    return None


def _strip_leading_char(text: str, char: str) -> str:
    s = text.lstrip()
    if s.startswith(char):
        s = s[len(char) :].lstrip()
    s = _LEADING_PINYIN_RE.sub("", s)
    return s.lstrip()


def _find_balanced_paren(text: str, start: int) -> int | None:
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
    return benyi, (text[:idx] + text[end:]).strip(), content


def _first_meaningful_segment(text: str, benyi: str | None) -> str:
    if not text:
        return benyi or ""
    if text.startswith("同本义") and benyi:
        return benyi
    parts = re.split(r"[。；\n]", text)
    for part in parts:
        cleaned = part.strip()
        if cleaned and not cleaned.startswith(("又如", "如")):
            cleaned = re.sub(r"^同本义[。.]?\s*", "", cleaned)
            if cleaned:
                return cleaned
    return benyi or (parts[0].strip() if parts else text[:_SHORT_DEF_MAX])


def _clean_definition(explanation: str, char: str) -> tuple[str, str]:
    text = _strip_leading_char(explanation, char)
    text = _POS_RE.sub("", text, count=1).lstrip()
    benyi, text, _ = _extract_etymology(text)
    text = text.lstrip()
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n|\n\n", text) if p.strip()]
    full = " ".join(text.split()).strip()
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


def parse_xinhua(cache_dir: Path, *, include_ci: bool = True) -> list[HeadEntry]:
    """Build HeadEntry list from chinese-xinhua data."""
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
        phrase_bucket[word[0]].append(PhraseItem(form=word, definition=defn))
    for obj in ci_data:
        ci = (obj.get("ci") or "").strip()
        if not ci or len(ci) <= 1:
            continue
        explanation = " ".join((obj.get("explanation") or "").split()).strip()
        if not explanation:
            continue
        phrase_bucket[ci[0]].append(PhraseItem(form=ci, definition=explanation))

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


class XinhuaExtractor(Extractor):
    """Extract HeadEntry list from chinese-xinhua data dir."""

    def __init__(self, *, include_ci: bool = True) -> None:
        self.include_ci = include_ci

    def extract(self, source: Path) -> list[HeadEntry]:
        return parse_xinhua(source, include_ci=self.include_ci)
