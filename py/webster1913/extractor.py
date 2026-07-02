"""Extract HeadEntry list from Gutenberg Webster 1913 plain text."""

from __future__ import annotations

import re
import urllib.request
from pathlib import Path

from common.etl.base import Extractor
from common.etl.utils import truncate_at_word_boundary
from common.models import HeadEntry

_GUTENBERG_URL = "https://www.gutenberg.org/cache/epub/29765/pg29765.txt"

_POS_MAP: dict[str, str] = {
    "n.": "noun",
    "a.": "adj.",
    "v. t.": "v.t.",
    "v. i.": "v.i.",
    "v. t. & i.": "v.",
    "v.": "v.",
    "adv.": "adv.",
    "prep.": "prep.",
    "conj.": "conj.",
    "interj.": "interj.",
    "pron.": "pron.",
    "p. p.": "p.p.",
    "p. a.": "p.a.",
    "imp.": "imp.",
    "pl.": "pl.",
    "superl.": "superl.",
}
_POS_RE = re.compile(
    r",\s+((?:" + "|".join(re.escape(k) for k in sorted(_POS_MAP, key=len, reverse=True)) + r"))",
)
_HEADWORD_RE = re.compile(r"^([A-Z][A-Z\-' ]{0,60})$", re.MULTILINE)
_PRON_RE = re.compile(r"^([A-Za-z*\"\-`']+(?:\s*\([^)]*\))?)\s*,")
_DEF_LINE_RE = re.compile(r"(?:^|\n)\s*(?:Defn:\s*|(\d+)\.\s*)")
_PAREN_CRUFT_RE = re.compile(r"\s*\([^)]*\)\s*$")
_DEFN_CRUFT_RE = re.compile(r"^(?:Defn:\s*)+")


def _strip_etymology(text: str) -> str:
    result = text
    while True:
        idx = result.find("Etym: [")
        if idx < 0:
            break
        depth = 0
        end = None
        for i in range(idx + 6, min(idx + 1000, len(result))):
            if result[i] == "[":
                depth += 1
            elif result[i] == "]":
                if depth == 1:
                    end = i + 1
                    if end < len(result) and result[end] == ".":
                        end += 1
                    break
                depth -= 1
            elif result[i : i + 2] == "\n\n":
                break
        if end is None:
            line_end = result.find("\n", idx)
            if line_end < 0:
                line_end = len(result)
            result = result[:idx] + result[line_end:]
        else:
            result = result[:idx] + result[end:]
    return result


def download_source(cache_dir: Path) -> Path:
    """Download the Gutenberg text if not already cached."""
    path = cache_dir / "pg29765.txt"
    if not path.exists():
        cache_dir.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(_GUTENBERG_URL, path)
    return path


def _clean_pronunciation(raw: str) -> str:
    s = raw.strip().rstrip(",").strip()
    s = _PAREN_CRUFT_RE.sub("", s)
    s = s.replace("*", "\u00b7")
    s = s.replace('"', "\u02c8")
    return s.replace("`", "")


def _extract_first_definition(body: str) -> str:
    cleaned = _strip_etymology(body)
    m = _DEF_LINE_RE.search(cleaned)
    if m:
        rest = cleaned[m.end() :].strip()
    else:
        lines = cleaned.split("\n")
        rest = " ".join(lines[1:]).strip() if len(lines) > 1 else cleaned
    rest = " ".join(rest.split())
    rest = re.split(r"\s+(?:\d+\.\s|Note:|Syn\.\s|--)", rest)[0]
    return _DEFN_CRUFT_RE.sub("", rest).strip().rstrip(".")


def _short(text: str, max_chars: int = 80) -> str:
    return truncate_at_word_boundary(text, max_chars)


def parse_webster(source_path: Path) -> list[HeadEntry]:
    """Parse the Gutenberg Webster 1913 text into HeadEntry list."""
    text = source_path.read_text(encoding="utf-8")
    body_start = text.find("\nA\n")
    body_end = text.rfind("End of the Project Gutenberg")
    if body_end < 0:
        body_end = text.rfind("*** END OF THE PROJECT GUTENBERG")
    if body_end < 0:
        body_end = len(text)
    content = text[body_start:body_end]

    matches = list(_HEADWORD_RE.finditer(content))
    entries: list[HeadEntry] = []

    for i, m in enumerate(matches):
        headword_raw = m.group(1).strip()
        if headword_raw.endswith("-") or len(headword_raw) == 0:
            continue
        body_start_idx = m.end()
        body_end_idx = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        body = content[body_start_idx:body_end_idx].strip()
        if not body:
            continue
        first_line = body.split("\n")[0].strip()
        if not first_line:
            continue

        pron_match = _PRON_RE.match(first_line)
        pron = _clean_pronunciation(pron_match.group(1)) if pron_match else None
        pos_match = _POS_RE.search(first_line)
        pos_raw = pos_match.group(1) if pos_match else None
        pos = _POS_MAP.get(pos_raw, pos_raw) if pos_raw else None
        full_def = _extract_first_definition(body)
        short_def = _short(full_def) if full_def else None
        headword = headword_raw.title().replace("'S", "'s")

        entries.append(
            HeadEntry(
                headword=headword,
                sort_key=headword.lower(),
                leading_key=headword,
                pronunciation=pron,
                part_of_speech=pos,
                short_definition=short_def,
                full_definition=full_def,
            )
        )
    return entries


class WebsterExtractor(Extractor):
    """Extract HeadEntry list from Gutenberg Webster 1913 text file."""

    def extract(self, source: Path) -> list[HeadEntry]:
        return parse_webster(source)
