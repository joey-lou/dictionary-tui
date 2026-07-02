"""Default pack loader: writes manifest.json and entries.jsonl."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from common.etl.base import Loader
from common.io import write_pack
from common.models import HeadEntry, PackManifest


class PackLoader(Loader):
    """Writes pack to disk using common.io.write_pack."""

    def load(
        self,
        output_dir: Path,
        manifest: PackManifest,
        entries: Iterable[HeadEntry],
    ) -> int:
        return write_pack(output_dir, manifest, entries)
