# Dictionary pack ingest

Build dictionary packs (manifest + entries) from external sources via an **Extract → Transform → Load** pipeline. See `ETL_DESIGN.md` for the pipeline design and base classes.

## Layout

- **`common/`** — Shared models (`HeadEntry`, `PhraseItem`, `PackManifest`), I/O (`write_pack`), and ETL framework (`Pipeline`, `Extractor`, `Transformer`, `Loader`, `PackLoader`).
- **`webster1913/`**, **`xinhua/`**, **`cedict/`** — Per-dictionary packages, each with `extractor`, `transformers`, `loader`, and `__main__.py` CLI.
- **`ingest_webster1913.py`**, **`ingest_xinhua.py`**, **`ingest_cedict.py`** — Thin entrypoints that add `py` to `sys.path` and run the corresponding package’s `__main__.main()`.

## Running ingest

From the **repo root** (recommended):

```bash
python3 py/ingest_webster1913.py   # Webster's 1913 EN
python3 py/ingest_xinhua.py        # Xinhua ZH-ZH
python3 py/ingest_cedict.py        # CC-CEDICT ZH-EN
```

From **`py/`**:

```bash
cd py && python -m webster1913
cd py && python -m xinhua
cd py && python -m cedict
```

Scripts auto-download source data into `.cache/` on first run. Use `--source-file PATH` to use a local file instead (e.g. CEDICT if the default URL returns HTML).

## Pack format

Each pack is a directory containing:

- **`manifest.json`** — `id`, `name`, `language`, `sort`, `entry_count`, `license`, `source_url`.
- **`entries.jsonl`** — One JSON object per line: `HeadEntry` (headword, sort_key, leading_key, pronunciation, part_of_speech, short_definition, full_definition, phrases).

The Rust app reads these under `packs/<pack-id>/` and does not require a separate ingest step to run (packs are committed).

## Adding a new dictionary

1. Create `py/<name>/` with `extractor.py`, `transformers.py`, `loader.py`, `__main__.py` (copy from `webster1913/` or `cedict/`).
2. Add `py/ingest_<name>.py` that runs `<name>.__main__.main()` after adding `py` to `sys.path`.
3. Document in `ETL_DESIGN.md` and `docs/DATA_SOURCES.md` if needed.
