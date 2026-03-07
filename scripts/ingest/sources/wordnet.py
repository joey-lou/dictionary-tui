"""WordNet source download and parsing helpers."""

from __future__ import annotations

import tarfile
import urllib.request
from pathlib import Path

from ..models import DetailEntry

DEFAULT_WORDNET_URL = "https://wordnetcode.princeton.edu/3.0/WordNet-3.0.tar.gz"
_POS_ORDER = ("noun", "verb", "adj", "adv")


def download_source(url: str, target_file: Path) -> Path:
    """Download WordNet tarball to ``target_file`` if missing."""
    target_file.parent.mkdir(parents=True, exist_ok=True)
    if target_file.exists():
        return target_file
    with urllib.request.urlopen(url, timeout=60) as response:
        body = response.read()
    target_file.write_bytes(body)
    return target_file


def parse_tarball(
    path: Path,
    max_entries: int | None = None,
    pronunciation_lookup: dict[str, str] | None = None,
) -> list[DetailEntry]:
    """Parse WordNet tarball into dictionary entries. Optionally add pronunciation from CMU dict."""
    cmu = pronunciation_lookup or {}
    with tarfile.open(path, mode="r:gz") as tar:
        data_by_pos = {
            pos: _parse_data_file(_read_member_text(tar, f"dict/data.{pos}")) for pos in _POS_ORDER
        }
        entries: list[DetailEntry] = []
        seen = set()
        for pos in _POS_ORDER:
            index_text = _read_member_text(tar, f"dict/index.{pos}")
            for lemma, offset in _iter_index_lemma_offsets(index_text):
                headword = lemma.replace("_", " ")
                if not _is_reasonable_headword(headword):
                    continue
                if headword in seen:
                    continue
                gloss = data_by_pos[pos].get(offset)
                if not gloss:
                    continue
                short = _first_clause(gloss)
                pron = cmu.get(headword.upper())
                entries.append(
                    DetailEntry(
                        headword=headword,
                        sort_key=headword.lower(),
                        pronunciation=pron,
                        short_definition=short,
                        full_definition=gloss,
                        part_of_speech=pos,
                    )
                )
                seen.add(headword)
                if max_entries is not None and len(entries) >= max_entries:
                    return entries
    return entries


def _read_member_text(tar: tarfile.TarFile, suffix_path: str) -> str:
    member = next((m for m in tar.getmembers() if m.name.endswith(suffix_path)), None)
    if member is None:
        raise RuntimeError(f"missing WordNet member: {suffix_path}")
    extracted = tar.extractfile(member)
    if extracted is None:
        raise RuntimeError(f"failed to read WordNet member: {suffix_path}")
    return extracted.read().decode("utf-8", errors="ignore")


def _parse_data_file(text: str) -> dict[int, str]:
    gloss_by_offset: dict[int, str] = {}
    for line in text.splitlines():
        if not line or line.startswith("  "):
            continue
        if "|" not in line:
            continue
        data_part, gloss_part = line.split("|", maxsplit=1)
        fields = data_part.split()
        if not fields:
            continue
        try:
            offset = int(fields[0])
        except ValueError:
            continue
        gloss = gloss_part.strip()
        if gloss:
            gloss_by_offset[offset] = gloss
    return gloss_by_offset


def _iter_index_lemma_offsets(text: str):
    for line in text.splitlines():
        if not line or line.startswith("  "):
            continue
        parts = line.split()
        if len(parts) < 6:
            continue
        lemma = parts[0]
        try:
            synset_cnt = int(parts[2])
            ptr_count = int(parts[3])
        except ValueError:
            continue
        offsets_start = 6 + ptr_count
        offsets_end = offsets_start + synset_cnt
        if len(parts) < offsets_end:
            continue
        try:
            first_offset = int(parts[offsets_start])
        except ValueError:
            continue
        yield lemma, first_offset


def _first_clause(gloss: str, max_len: int = 100) -> str:
    """First clause or phrase of the gloss for list view; full gloss is kept for detail."""
    for marker in ("; ", " -- ", ", "):
        idx = gloss.find(marker)
        if 0 < idx <= max_len:
            return gloss[:idx].strip()
    s = gloss[:max_len].strip()
    return s + "…" if len(gloss) > max_len else s


def _is_reasonable_headword(headword: str) -> bool:
    if not headword:
        return False
    if not headword[0].isalpha():
        return False
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ -'")
    return all(ch in allowed for ch in headword)
