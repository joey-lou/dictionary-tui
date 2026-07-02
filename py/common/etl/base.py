"""Base classes for the ingest ETL pipeline."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from pathlib import Path

from common.models import HeadEntry, PackManifest


class Extractor(ABC):
    """Produces HeadEntry records from a source (file or dir)."""

    @abstractmethod
    def extract(self, source: Path) -> list[HeadEntry]:
        """Read source and return a list of head entries."""
        ...


class Transformer(ABC):
    """Modifies a list of HeadEntry; chain multiple in the pipeline."""

    @abstractmethod
    def apply(self, entries: list[HeadEntry]) -> list[HeadEntry]:
        """Return a new list of entries with this transform applied."""
        ...


class Loader(ABC):
    """Writes the final pack to disk."""

    @abstractmethod
    def load(
        self,
        output_dir: Path,
        manifest: PackManifest,
        entries: Iterable[HeadEntry],
    ) -> int:
        """Write manifest and entries to output_dir; return entry count."""
        ...


class Pipeline:
    """Runs Extract → Transform chain → Load."""

    def __init__(
        self,
        extractor: Extractor,
        transformers: Iterable[Transformer],
        loader: Loader,
    ) -> None:
        self.extractor = extractor
        self.transformers = list(transformers)
        self.loader = loader

    def run(
        self,
        source: Path,
        output_dir: Path,
        manifest: PackManifest,
    ) -> int:
        """Extract from source, apply transforms, load to output_dir."""
        entries = self.extractor.extract(source)
        for t in self.transformers:
            entries = t.apply(entries)
        return self.loader.load(output_dir, manifest, entries)
