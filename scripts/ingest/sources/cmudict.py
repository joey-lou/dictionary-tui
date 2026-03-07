"""CMU Pronouncing Dictionary (ARPAbet) for English pronunciation."""

from __future__ import annotations

import re
import urllib.request
from pathlib import Path

# Default: mirror that hosts the 0.7b text file (two spaces between word and phonemes).
DEFAULT_CMUDICT_URL = "https://raw.githubusercontent.com/Alexir/CMUdict/master/cmudict-0.7b"
# Alternative: https://github.com/cmusphinx/cmudict (file may be named differently)


def load_cmudict(path: Path) -> dict[str, str]:
    """
    Load CMU dict from a local file. Returns mapping word_uppercase -> pronunciation (ARPAbet).
    Word variants (1), (2) are normalized to the same key; first pronunciation is kept.
    """
    result: dict[str, str] = {}
    text = path.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(";;;"):
            continue
        # Format: "WORD  PHON1 PHON2 ..." (two spaces) or "WORD(1)  PHON1 ..."
        match = re.match(r"^(.+?)\s{2,}(.+)$", line)
        if not match:
            continue
        word_part, pron = match.group(1).strip(), match.group(2).strip()
        # Normalize key: "NATURAL(2)" -> "NATURAL"; keep first pronunciation per word.
        key = re.sub(r"\s*\(\d+\)\s*$", "", word_part).strip()
        if key and key not in result:
            result[key] = pron
    return result


def download_cmudict(target_file: Path, url: str = DEFAULT_CMUDICT_URL) -> Path:
    """Download CMU dict to target_file if missing. Returns path."""
    target_file.parent.mkdir(parents=True, exist_ok=True)
    if target_file.exists():
        return target_file
    with urllib.request.urlopen(url, timeout=60) as response:
        body = response.read()
    target_file.write_bytes(body)
    return target_file


def pronunciation_lookup_from_path(cmu_path: Path | None) -> dict[str, str]:
    """Load CMU dict from path; return empty dict if path is None or file missing."""
    if cmu_path is None or not cmu_path.exists():
        return {}
    return load_cmudict(cmu_path)
