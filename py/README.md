# Dictionary pack ingest

Build `manifest.json` + `entries.jsonl` under `packs/` from external sources.  
See the main [README](../README.md) for installing and running the TUI.

## Layout

```
py/
├── common/           # models, I/O, ETL framework
├── webster1913/      # Webster's 1913 (EN)
├── xinhua/           # Xinhua (ZH-ZH)
├── cedict/           # CC-CEDICT (ZH-EN)
└── ingest_*.py       # CLI entrypoints
```

## Run

From repo root:

```bash
python3 py/ingest_webster1913.py
python3 py/ingest_xinhua.py
python3 py/ingest_cedict.py
```

Sources download into `.cache/` on first run. Use `--help` for `--source-file` and `--out`.

## Pack format

| File | Contents |
|------|----------|
| `manifest.json` | `id`, `name`, `language`, `sort`, `entry_count`, `license`, `source_url` |
| `entries.jsonl` | One JSON line per entry: `headword`, `sort_key`, `pronunciation`, definitions, optional `phrases` |

## Data sources

| Pack | Source |
|------|--------|
| `webster1913-en` | [Project Gutenberg #29765](https://www.gutenberg.org/ebooks/29765) |
| `xinhua-zh-zh` | [pwxcoo/chinese-xinhua](https://github.com/pwxcoo/chinese-xinhua) |
| `cc-cedict` | [CC-CEDICT](https://cc-cedict.org/) via [MDBG export](https://www.mdbg.net/chinese/export/cedict/cedict_1_0_ts_utf-8_mdbg.txt.gz) |

## New dictionary

1. Copy `py/webster1913/` or `py/cedict/` → `py/<name>/` (extractor, transformers, loader, `__main__.py`).
2. Add `py/ingest_<name>.py`.
3. Ship via a `packs-v*` release (update `packs/catalog.json`).
