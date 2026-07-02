"""Transform chain for Xinhua pipeline."""

from __future__ import annotations

import re

from common.etl.base import Transformer
from common.etl.transforms import NormalizeEscapedQuotes, NormalizePOS
from common.etl.utils import (
    truncate_at_word_boundary,
    xinhua_add_newlines_in_full_def,
    xinhua_fix_placeholder_and_corrupt,
    xinhua_normalize_numbering,
    xinhua_normalize_short_def_leading,
    xinhua_short_def_from_first_sense,
)
from common.models import HeadEntry, PhraseItem

_SHORT_MAX = 60


class XinhuaFixPlaceholderAndCorrupt(Transformer):
    """Replace known corrupt runs (e.g. 腰瓿->pathaka) and placeholder ? in definitions."""

    def apply(self, entries: list[HeadEntry]) -> list[HeadEntry]:
        result = []
        for e in entries:
            short = xinhua_fix_placeholder_and_corrupt(e.short_definition) if e.short_definition else e.short_definition
            full = xinhua_fix_placeholder_and_corrupt(e.full_definition) if e.full_definition else e.full_definition
            new_phrases = (
                tuple(
                    PhraseItem(form=p.form, definition=xinhua_fix_placeholder_and_corrupt(p.definition))
                    for p in e.phrases
                )
                if e.phrases
                else e.phrases
            )
            if short != e.short_definition or full != e.full_definition or new_phrases != e.phrases:
                result.append(
                    HeadEntry(
                        headword=e.headword,
                        sort_key=e.sort_key,
                        leading_key=e.leading_key,
                        pronunciation=e.pronunciation,
                        part_of_speech=e.part_of_speech,
                        short_definition=short or e.short_definition,
                        full_definition=full or e.full_definition,
                        phrases=new_phrases,
                    )
                )
            else:
                result.append(e)
        return result


class XinhuaShortDefFromFirstSense(Transformer):
    """Derive short_definition from first sense; skip empty or circular (headword-only) defs."""

    def apply(self, entries: list[HeadEntry]) -> list[HeadEntry]:
        result = []
        for e in entries:
            short = xinhua_short_def_from_first_sense(e.full_definition, e.short_definition, e.headword)
            if short and len(short) > _SHORT_MAX:
                short = truncate_at_word_boundary(short, _SHORT_MAX)
            if short != e.short_definition:
                result.append(
                    HeadEntry(
                        headword=e.headword,
                        sort_key=e.sort_key,
                        leading_key=e.leading_key,
                        pronunciation=e.pronunciation,
                        part_of_speech=e.part_of_speech,
                        short_definition=short,
                        full_definition=e.full_definition,
                        phrases=e.phrases,
                    )
                )
            else:
                result.append(e)
        return result


class XinhuaAddNewlinesInFullDef(Transformer):
    """Insert newlines between 又見, senses, for readability."""

    def apply(self, entries: list[HeadEntry]) -> list[HeadEntry]:
        result = []
        for e in entries:
            if not e.full_definition:
                result.append(e)
                continue
            full = xinhua_add_newlines_in_full_def(e.full_definition)
            if full != e.full_definition:
                result.append(
                    HeadEntry(
                        headword=e.headword,
                        sort_key=e.sort_key,
                        leading_key=e.leading_key,
                        pronunciation=e.pronunciation,
                        part_of_speech=e.part_of_speech,
                        short_definition=e.short_definition,
                        full_definition=full,
                        phrases=e.phrases,
                    )
                )
            else:
                result.append(e)
        return result


class XinhuaNormalizeNumbering(Transformer):
    """Normalize ①② and ⑴⑵ to 1. 2. style."""

    def apply(self, entries: list[HeadEntry]) -> list[HeadEntry]:
        result = []
        for e in entries:
            short = xinhua_normalize_numbering(e.short_definition) if e.short_definition else e.short_definition
            short = xinhua_normalize_short_def_leading(short or e.short_definition or "", e.headword)
            full = xinhua_normalize_numbering(e.full_definition) if e.full_definition else e.full_definition
            if short != e.short_definition or full != e.full_definition:
                result.append(
                    HeadEntry(
                        headword=e.headword,
                        sort_key=e.sort_key,
                        leading_key=e.leading_key,
                        pronunciation=e.pronunciation,
                        part_of_speech=e.part_of_speech,
                        short_definition=short or e.short_definition,
                        full_definition=full or e.full_definition,
                        phrases=e.phrases,
                    )
                )
            else:
                result.append(e)
        return result


# full_definition may start with headword+pinyin+digit. (extractor can strip headword, leaving pinyin+digit.)
_PINYIN_CHARS = r"a-zA-ZüÜāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜɡ"
_LEADING_PINYIN_NUM = re.compile(r"^([" + _PINYIN_CHARS + r"]+)\d*\.")
# Only override when def is short (variant "X讀1.同\"Y\"" type); avoid changing main entries
_MAX_DEF_LEN_FOR_PINYIN_OVERRIDE = 50


def _pinyin_sort_key(pinyin: str) -> str:
    return pinyin.lower().strip()


class XinhuaFixPronunciationFromDefinition(Transformer):
    """When full_definition is short and starts with pinyin+digit. (e.g. dú1.), use that pinyin if it differs."""

    def apply(self, entries: list[HeadEntry]) -> list[HeadEntry]:
        result = []
        for e in entries:
            full = (e.full_definition or "").strip()
            if not full or len(full) > _MAX_DEF_LEN_FOR_PINYIN_OVERRIDE:
                result.append(e)
                continue
            m = _LEADING_PINYIN_NUM.match(full)
            if not m:
                result.append(e)
                continue
            def_pinyin = m.group(1).strip()
            current = (e.pronunciation or "").strip()
            if not def_pinyin or def_pinyin.lower() == current.lower():
                result.append(e)
                continue
            result.append(
                HeadEntry(
                    headword=e.headword,
                    sort_key=_pinyin_sort_key(def_pinyin),
                    leading_key=e.leading_key,
                    pronunciation=def_pinyin,
                    part_of_speech=e.part_of_speech,
                    short_definition=e.short_definition,
                    full_definition=e.full_definition,
                    phrases=e.phrases,
                )
            )
        return result


def get_transformers():
    """Return the list of transformers for the Xinhua pipeline."""
    return [
        XinhuaFixPlaceholderAndCorrupt(),
        NormalizeEscapedQuotes(),
        NormalizePOS(),  # English POS; map Chinese single-char (名/动/形) to English
        XinhuaShortDefFromFirstSense(),
        XinhuaAddNewlinesInFullDef(),
        XinhuaFixPronunciationFromDefinition(),  # before NormalizeNumbering so full_def still has "頭pinyin1."
        XinhuaNormalizeNumbering(),
    ]
