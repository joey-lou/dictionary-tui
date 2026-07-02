# Dictionary ingest ETL design

Ingest is structured as an **Extract → Transform → Load** pipeline so that:

- **Extract** is source-specific (Gutenberg text, JSON dir, CEDICT file).
- **Transform** is a chain of reusable or source-specific steps that fix parsing and data quality.
- **Load** writes the unified pack (manifest + entries.jsonl).

When new data issues are found, add a **Transformer** and register it in the pipeline instead of touching the extractor.

---

## 1. Pipeline flow

```
  Source (Path)     Extract        Transform₁ … Transformₙ       Load
  (file or dir)  →  [HeadEntry*]  →  [HeadEntry*]  →  manifest.json + entries.jsonl
```

- **Extractor**: `extract(source: Path) -> list[HeadEntry]`. Reads the raw source and produces a list of head entries. Source format is dictionary-specific (e.g. one text file, a directory of JSON files).
- **Transformers**: `apply(entries: list[HeadEntry]) -> list[HeadEntry]`. Each step returns a new list; order can matter (e.g. truncate after stripping cruft).
- **Loader**: `load(output_dir, manifest, entries) -> int`. Writes the pack and returns the final entry count.

The CLI for each dictionary:

1. Resolves the **source** path (download to cache, or use `--source-file`).
2. Builds a **Pipeline(extractor, transformers, loader)**.
3. Calls **pipeline.run(source, output_dir, manifest)**.

---

## 2. Layout

```
py/
├── ETL_DESIGN.md           # This document
├── README.md               # Pack format and how to run / add a source
├── common/                 # Shared models, I/O, ETL framework
│   ├── models.py           # HeadEntry, PhraseItem, PackManifest
│   ├── io.py               # write_pack, merge_phrases_into_heads
│   └── etl/
│       ├── __init__.py     # Pipeline, Extractor, Transformer, Loader, PackLoader
│       ├── base.py         # Abstract base classes + Pipeline
│       ├── transforms.py   # Shared transformers (TruncateShortDefinition, etc.)
│       ├── loader.py       # PackLoader (wraps write_pack)
│       └── utils.py        # truncate_at_word_boundary, strip_legacy_markers, etc.
├── webster1913/            # Webster's 1913 EN pack
│   ├── extractor.py        # parse_webster, download_source, WebsterExtractor
│   ├── transformers.py     # get_transformers()
│   ├── loader.py           # re-exports PackLoader
│   └── __main__.py         # CLI: argparse, pipeline.run
├── xinhua/                 # Xinhua ZH-ZH pack
│   ├── extractor.py        # parse_xinhua, XinhuaExtractor
│   ├── transformers.py    # get_transformers()
│   ├── loader.py           # re-exports PackLoader
│   └── __main__.py         # CLI
├── cedict/                 # CC-CEDICT ZH-EN pack
│   ├── extractor.py        # parse_file, download_source, CEDICTExtractor
│   ├── transformers.py    # get_transformers()
│   ├── loader.py          # re-exports PackLoader
│   └── __main__.py         # CLI
├── ingest_webster1913.py   # Thin entrypoint: sys.path + webster1913.__main__.main
├── ingest_xinhua.py        # Thin entrypoint: xinhua.__main__.main
└── ingest_cedict.py        # Thin entrypoint: cedict.__main__.main
```

Run from repo root: `python3 py/ingest_webster1913.py` (and similarly for xinhua/cedict). Or from `py/`: `python -m webster1913`, `python -m xinhua`, `python -m cedict`.

---

## 3. Base classes

### Extractor (ABC)

- **Method**: `extract(self, source: Path) -> list[HeadEntry]`.
- **Responsibility**: Parse the source (file or directory) into a list of `HeadEntry`. No normalization beyond what the source format requires to produce valid entries.
- **Example**: `WebsterExtractor.extract(path)` reads the Gutenberg text and returns one `HeadEntry` per dictionary entry.

### Transformer (ABC)

- **Method**: `apply(self, entries: list[HeadEntry]) -> list[HeadEntry]`.
- **Responsibility**: Return a new list of entries with some cleanup or normalization applied. Immutable style: do not mutate input entries.
- **Examples**:
  - `TruncateShortDefinition(max_chars=80)` — truncate `short_definition` at word boundary.
  - Future: `StripWebsterDefnMarker`, `FixXinhuaMissingChars`, etc.

### Loader (ABC)

- **Method**: `load(self, output_dir: Path, manifest: PackManifest, entries: Iterable[HeadEntry]) -> int`.
- **Responsibility**: Write `manifest.json` and `entries.jsonl` to `output_dir`; return the number of entries written.
- **Default**: `PackLoader` delegates to `common.io.write_pack`.

### Pipeline

- **Constructor**: `Pipeline(extractor, transformers, loader)`.
- **Method**: `run(source, output_dir, manifest) -> int`. Runs extract → transform chain → load; returns entry count.
- **Note**: `manifest.entry_count` is ignored; the loader sets it from the actual count.

---

## 4. Adding a new dictionary

1. **Add a package** `py/<name>/` with `extractor.py`, `transformers.py`, `loader.py`, `__main__.py` (see `webster1913/` or `cedict/` as a template).
   - In `extractor.py`: implement parsing and an `Extractor` subclass that calls it in `extract(source)`.
   - In `__main__.py`: resolve source path (download or `--source-file`), build `Pipeline(...)`, build `PackManifest`, call `pipeline.run(...)`.
2. **Add a thin entrypoint** `py/ingest_<name>.py` that inserts `py` into `sys.path` and runs `<name>.__main__.main()`.
3. **Optional**: Add source-specific transformers in `common/etl/transforms.py` or in the package’s `transformers.py`, and register them in the package’s `get_transformers()`.

---

## 5. Adding a new fix (transform)

When a data quality issue is found (see `docs/DATA_ISSUES.md`):

1. **Implement a Transformer** in `common/etl/transforms.py` (or the dictionary package’s `transformers.py` if it’s source-specific).
   - Use helpers from `common/etl/utils.py` (e.g. `truncate_at_word_boundary`, `strip_legacy_markers`) where possible.
2. **Register it** in the appropriate pipeline:
   - Add to that package’s `get_transformers()` (e.g. `webster1913/transformers.py`).
3. **Document** the issue and the fix in `docs/DATA_ISSUES.md` (mark as addressed).

No need to change the extractor unless the bug is in the initial parsing logic (e.g. wrong regex for entry boundaries).

---

## 6. Shared utilities (`etl/utils.py`)

- **truncate_at_word_boundary(text, max_chars, ellipsis)** — Truncate at last space so the result doesn’t end mid-word; append ellipsis.
- **strip_legacy_markers(text)** — Remove leading `Defn:` and similar structural cruft from definition text.
- **normalize_whitespace(text)** — Collapse runs of whitespace to a single space, strip edges.
- **split_senses_on_numbering(text)** — Split definition text into a list of senses by `1. 2.` or `(a) (b)` style numbering.

Use these inside transformers to keep behavior consistent and easy to tune.
