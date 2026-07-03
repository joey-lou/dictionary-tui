# Dictionary pack ingest

Build dictionary packs (`manifest.json` + `entries.jsonl`) from external sources.

## Layout

```
py/
├── common/           # models, I/O, ETL framework (Pipeline, Transformer, …)
├── webster1913/      # Webster's 1913 EN
├── xinhua/           # Xinhua ZH-ZH
├── cedict/           # CC-CEDICT ZH-EN
└── ingest_*.py       # CLI entrypoints
```

## Run ingest

From repo root:

```bash
python3 py/ingest_webster1913.py
python3 py/ingest_xinhua.py
python3 py/ingest_cedict.py
```

Scripts download source data into `.cache/` on first run. Use `--help` for options (`--source-file`, `--out`).

## Pack format

Each pack directory contains:

- **`manifest.json`** — `id`, `name`, `language`, `sort`, `entry_count`, `license`, `source_url`
- **`entries.jsonl`** — one JSON object per line (`headword`, `sort_key`, `pronunciation`, `short_definition`, `full_definition`, optional `phrases`)

## Data sources

| Pack | Source |
|------|--------|
| `webster1913-en` | [Project Gutenberg #29765](https://www.gutenberg.org/ebooks/29765) |
| `xinhua-zh-zh` | [pwxcoo/chinese-xinhua](https://github.com/pwxcoo/chinese-xinhua) |
| `cc-cedict` | [CC-CEDICT](https://cc-cedict.org/) via [MDBG export](https://www.mdbg.net/chinese/export/cedict/cedict_1_0_ts_utf-8_mdbg.txt.gz) |

## Adding a new dictionary

1. Copy `py/webster1913/` or `py/cedict/` to `py/<name>/` (extractor, transformers, loader, `__main__.py`).
2. Add `py/ingest_<name>.py` entrypoint.
3. Add an entry to `packs/catalog.json` when ready to ship.
