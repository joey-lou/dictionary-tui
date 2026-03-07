# Ingest: adding a new dictionary source

This directory contains the shared library for building dictionary packs.
Each pack is a folder with `manifest.json` + `entries.jsonl`.

## Pack structure

```
packs/<pack-id>/
├── manifest.json      # Pack metadata
└── entries.jsonl       # One HeadEntry per line (JSON)
```

### manifest.json

```json
{
  "id": "my-pack",
  "name": "My Dictionary",
  "language": "en",
  "sort": "alphabetical",
  "entry_count": 50000,
  "data_file": "entries.jsonl",
  "license": "MIT",
  "source_url": "https://example.com"
}
```

`sort` is `"alphabetical"` for English or `"pinyin"` for Chinese.

### entries.jsonl

Each line is a JSON object matching `HeadEntry`:

```json
{
  "headword": "rain",
  "sort_key": "rain",
  "leading_key": "rain",
  "pronunciation": null,
  "part_of_speech": "noun",
  "short_definition": "water falling from clouds",
  "full_definition": "1. water falling in drops...\n2. anything falling rapidly...",
  "phrases": [
    {"form": "rain cats and dogs", "definition": "to rain very heavily"}
  ]
}
```

**Rules:**
- Every line is a **head** entry (single word for EN, single character for ZH)
- `leading_key` = `headword` for heads
- Multi-word/multi-char entries go in `phrases[]`, never as separate lines
- One record per `(headword, pronunciation, part_of_speech)`
- `phrases` is omitted (not `[]`) when empty

## Adding a new source

1. **Create a source parser** in `sources/<name>.py`:

```python
from ..models import HeadEntry, PhraseItem

def parse_my_source(path: Path) -> list[HeadEntry]:
    """Parse source data into HeadEntry objects."""
    ...
```

The parser should:
- Yield one `HeadEntry` per (headword, POS) tuple
- Set `leading_key = headword`
- Attach multi-word/multi-char entries as `PhraseItem` in `phrases`
- Truncate `short_definition` to ~100 characters

2. **Create a CLI script** at `py/ingest_<name>.py`:

```python
from ingest.io_utils import write_pack
from ingest.models import PackManifest
from ingest.sources.<name> import parse_my_source

entries = parse_my_source(source_path)
manifest = PackManifest(
    id="my-pack",
    name="My Dictionary",
    language="en",
    sort="alphabetical",
    entry_count=len(entries),
)
write_pack(Path("packs/my-pack"), manifest, entries)
```

3. **Run it:** `python3 py/ingest_<name>.py`

`write_pack` handles sorting by `(leading_key, sort_key)` and writing
both `manifest.json` and `entries.jsonl`.

## Existing sources

| Source module | CLI script | Pack ID |
|---------------|-----------|---------|
| `sources/wordset.py` | `py/ingest_wordset.py` | `wordset-en` |
| `sources/xinhua.py` | `py/ingest_xinhua.py` | `xinhua-zh-zh` |
| `sources/cedict.py` | `py/ingest_cedict.py` | `cc-cedict` |

## Models

- `models.py` — `HeadEntry`, `PhraseItem`, `PackManifest` dataclasses
- `io_utils.py` — `write_pack()` serialization, `merge_phrases_into_heads()` helper
