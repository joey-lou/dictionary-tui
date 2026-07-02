"""Shared transformers for the ETL pipeline."""

from __future__ import annotations

from common.etl.base import Transformer
from common.etl.utils import (
    first_definition_before_all_caps,
    normalize_escaped_quotes,
    normalize_whitespace,
    strip_all_caps_headings,
    strip_legacy_markers,
    truncate_at_word_boundary,
)
from common.etl.utils import (
    normalize_pos_style as _normalize_pos,
)
from common.models import HeadEntry


class TruncateShortDefinition(Transformer):
    """Truncate short_definition at word boundary instead of mid-word."""

    def __init__(self, max_chars: int = 80) -> None:
        self.max_chars = max_chars

    def apply(self, entries: list[HeadEntry]) -> list[HeadEntry]:
        result = []
        for e in entries:
            if e.short_definition and len(e.short_definition) > self.max_chars:
                short = truncate_at_word_boundary(e.short_definition, self.max_chars)
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


class NormalizeWhitespaceDefinitions(Transformer):
    """Collapse runs of whitespace in short_definition and full_definition."""

    def apply(self, entries: list[HeadEntry]) -> list[HeadEntry]:
        result = []
        for e in entries:
            short = normalize_whitespace(e.short_definition) if e.short_definition else e.short_definition
            full = normalize_whitespace(e.full_definition) if e.full_definition else e.full_definition
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


class StripLegacyMarkers(Transformer):
    """Strip Defn:, [Obs.], [R.] from short_definition and full_definition."""

    def apply(self, entries: list[HeadEntry]) -> list[HeadEntry]:
        result = []
        for e in entries:
            short = strip_legacy_markers(e.short_definition) if e.short_definition else e.short_definition
            full = strip_legacy_markers(e.full_definition) if e.full_definition else e.full_definition
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


class StripAllCapsHeadings(Transformer):
    """Remove ALL CAPS headword-style runs from definition text."""

    def apply(self, entries: list[HeadEntry]) -> list[HeadEntry]:
        result = []
        for e in entries:
            short = strip_all_caps_headings(e.short_definition) if e.short_definition else e.short_definition
            full = strip_all_caps_headings(e.full_definition) if e.full_definition else e.full_definition
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


class NormalizeEscapedQuotes(Transformer):
    """Replace \\\" and remove * diacritic cruft in definitions."""

    def apply(self, entries: list[HeadEntry]) -> list[HeadEntry]:
        result = []
        for e in entries:
            short = normalize_escaped_quotes(e.short_definition) if e.short_definition else e.short_definition
            full = normalize_escaped_quotes(e.full_definition) if e.full_definition else e.full_definition
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


class TruncateAtFirstAllCapsHeadword(Transformer):
    """Keep only the first definition; drop content after ALL CAPS next-headword line (sub-entry leakage)."""

    def apply(self, entries: list[HeadEntry]) -> list[HeadEntry]:
        result = []
        for e in entries:
            short = first_definition_before_all_caps(e.short_definition) if e.short_definition else e.short_definition
            full = first_definition_before_all_caps(e.full_definition) if e.full_definition else e.full_definition
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


class NormalizePOS(Transformer):
    """Normalize part_of_speech to consistent style (no trailing period)."""

    def apply(self, entries: list[HeadEntry]) -> list[HeadEntry]:
        result = []
        for e in entries:
            pos = _normalize_pos(e.part_of_speech)
            if pos != e.part_of_speech:
                result.append(
                    HeadEntry(
                        headword=e.headword,
                        sort_key=e.sort_key,
                        leading_key=e.leading_key,
                        pronunciation=e.pronunciation,
                        part_of_speech=pos,
                        short_definition=e.short_definition,
                        full_definition=e.full_definition,
                        phrases=e.phrases,
                    )
                )
            else:
                result.append(e)
        return result
