"""Transform chain for Webster 1913 pipeline."""

from common.etl.transforms import (
    NormalizeEscapedQuotes,
    NormalizePOS,
    StripAllCapsHeadings,
    StripLegacyMarkers,
    TruncateAtFirstAllCapsHeadword,
    TruncateShortDefinition,
)


def get_transformers():
    """Return the list of transformers for the Webster 1913 pipeline."""
    return [
        TruncateAtFirstAllCapsHeadword(),
        StripLegacyMarkers(),
        StripAllCapsHeadings(),
        NormalizeEscapedQuotes(),
        NormalizePOS(),
        TruncateShortDefinition(max_chars=80),
    ]
