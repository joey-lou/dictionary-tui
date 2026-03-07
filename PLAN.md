# Dictionary TUI — Project Plan

**Goal:** A terminal UI for browsing dictionaries with responsive page flips, optional short definitions on each page, and expand-to-detail for selected words. English, Chinese–English, and Chinese–Chinese supported.

---

## 1. Overview

| Aspect | Choice |
|--------|--------|
| **Language** | Rust |
| **TUI framework** | ratatui + crossterm |
| **Data** | Local dictionary packs; unified schema across languages |
| **Extensibility** | Well-defined pack format + provider API; add new dictionaries without changing core app |

### Core UX

- **List view:** Paginated word list in sort order (alphabetical for English, pinyin for Chinese). Each row: headword + optional pronunciation + optional POS + optional short definition.
- **Navigation:** Up/down to move selection; left/right (or prev/next page) to page through; configurable page-turn increment.
- **Detail view:** Select a word → expand to full definition, pronunciation, and associated phrases/idioms.
- **Pack picker:** Choose between installed dictionaries on startup.
- **Search:** Inline prefix search (`/`) to jump to matching entries.

---

## 2. Architecture

```
┌──────────────────────────────────────────────────┐
│  TUI (ratatui + crossterm)                        │
│  - Pack picker, List view, Detail view            │
│  - Key bindings (nav, select, search, random page)│
└──────────────────┬───────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────┐
│  App / Session                                    │
│  - Current pack, page index, selection, view mode │
│  - Calls provider for list_entries() / get_detail()│
└──────────────────┬───────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────┐
│  Provider API (trait)                             │
│  - metadata(), entry_count(), list_entries(),     │
│    get_detail(), search_first_prefix()            │
└──────────────────┬───────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────┐
│  LocalProvider                                    │
│  - Reads JSONL packs from disk                    │
│  - Collapsed/expanded view via root_indices       │
└──────────────────────────────────────────────────┘
```

---

## 3. Dictionary Pack Format

### Location

- **Pack root:** `packs/<pack-id>/` (repo-local) or `~/.config/dictionary-tui/packs/<pack-id>/`.
- **Discovery:** App scans for directories containing `manifest.json`.

### Manifest (`manifest.json`)

```json
{
  "id": "wordset-en",
  "name": "Wordset Dictionary",
  "language": "en",
  "sort": "alphabetical",
  "entry_count": 77000,
  "data_file": "entries.jsonl",
  "license": "CC BY 4.0",
  "source_url": "https://github.com/StevensDeptECE/Dictionaries"
}
```

### Unified Entry Schema

Every `entries.jsonl` line is a **head entry** — one per (headword, pronunciation, POS):

| Field | Type | Description |
|-------|------|-------------|
| `headword` | string | Atomic unit: single word (EN), single character (ZH) |
| `sort_key` | string | Ordering: lowercase (EN), pinyin (ZH) |
| `leading_key` | string | Grouping key (equals headword for heads) |
| `pronunciation` | string? | IPA (EN) or pinyin (ZH) |
| `part_of_speech` | string? | Normalized POS (noun, verb, adj, adv, …) |
| `short_definition` | string | One-line summary for list view |
| `full_definition` | string | Full text or numbered senses for detail view |
| `phrases` | PhraseItem[]? | Compound words/idioms grouped under this head |

**PhraseItem:** `{"form": "rain cats and dogs", "definition": "to rain very heavily"}`

**Key rules:**
- Index contains only atomic headwords (single word EN, single character ZH)
- Multi-word/multi-character entries → `phrases[]` array, never separate index rows
- One record per (headword, pronunciation, POS)

---

## 4. Current Packs

| Pack ID | Source | Language | Heads | POS | Pron. |
|---------|--------|----------|-------|-----|-------|
| `webster1913-en` | [Webster's 1913](https://www.gutenberg.org/ebooks/29765) | EN | 109K | 96% | 96% |
| `wordset-en` | [Wordset](https://github.com/StevensDeptECE/Dictionaries) | EN | 77K | ✓ | ✗ |
| `xinhua-zh-zh` | [chinese-xinhua](https://github.com/pwxcoo/chinese-xinhua) | ZH (中中) | 17K | 9% | ✓ |
| `cc-cedict` | [CC-CEDICT](https://cc-cedict.org/) | ZH-EN (中英) | 13K | partial | ✓ |

---

## 5. Tech Stack

- **Rust** (edition 2021) — TUI binary
- **ratatui** + **crossterm** — Terminal UI and input
- **serde** + **serde_json** — Pack (de)serialization
- **directories** — Config path resolution
- **Python 3** — Ingest scripts (stdlib only, no pip dependencies)

---

## 6. Repo Layout

```
dictionary-tui/
├── src/
│   ├── main.rs             # Entry point
│   ├── lib.rs              # Library root
│   ├── app.rs              # TUI loop, screens, key bindings
│   ├── provider.rs         # Provider trait + LocalProvider (JSONL)
│   ├── pack.rs             # Manifest parsing, pack discovery
│   ├── schema.rs           # ListEntry, DetailEntry, PhraseItem, PackManifest
│   └── config.rs           # User configuration
├── packs/                  # Bundled dictionary packs
│   ├── webster1913-en/
│   ├── wordset-en/
│   ├── xinhua-zh-zh/
│   └── cc-cedict/
├── py/
│   ├── ingest/             # Shared ingest library
│   │   ├── models.py       # HeadEntry, PhraseItem, PackManifest
│   │   ├── io_utils.py     # write_pack, merge helpers
│   │   └── sources/        # Per-source parsers
│   ├── ingest_webster1913.py # Webster's 1913 EN ingest CLI
│   ├── ingest_wordset.py   # Wordset EN ingest CLI
│   ├── ingest_xinhua.py    # Xinhua ZH-ZH ingest CLI
│   └── ingest_cedict.py    # CC-CEDICT ZH-EN ingest CLI
├── docs/                   # Design documentation
├── Cargo.toml
├── PLAN.md                 # This document
└── DEVELOPMENT.md          # Dev setup instructions
```
