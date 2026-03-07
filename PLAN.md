# Dictionary TUI — Project Plan

**Goal:** A terminal UI for browsing dictionaries with responsive page flips (up/down/left/right), optional short definitions on each page, and expand-to-detail for selected words. English first; Chinese (pinyin-indexed, with 成语) and community extensions later.

---

## 1. Overview

| Aspect | Choice |
|--------|--------|
| **Language** | Rust |
| **TUI framework** | ratatui + crossterm |
| **Data** | Local dictionary packs; users opt-in to download per dictionary |
| **Extensibility** | Well-defined dictionary provider API + pack format so devs can add new dictionaries without changing core app |

### Core UX

- **List view:** Paginated word list in sort order (alphabetical for English, pinyin for Chinese). Each row: headword + optional pronunciation + optional short definition.
- **Navigation:** Up/down or left/right (or prev/next page) to move through pages; responsive, no network delay.
- **Detail view:** Select a word → expand to full definition (and later: phrases, 成语).
- **Future:** Chinese words with Chinese definitions, common phrases, 成语; same UX, different data and sort key.

### Features & user interactions

1. **Random page**
   - A dedicated key (or button) jumps to a random page in the current dictionary. One press = one random page (no need to hold or cycle).

2. **Page-turn increment (speed)**
   - Each navigation action (e.g. next/prev) advances by **N pages** (or by N entries; see note below). N is configurable.
   - **Default presets:** 1, 2, 5, 10, 50. User can **cycle through** these (e.g. a key binding like `+` / `-` or a menu) to change the current increment.
   - **Custom value:** The increment should be **adjustable by hand** (e.g. config file or in-app input) so users can set values other than the presets.
   - *Note:* Decide whether “increment” is “pages” (e.g. next = +1 page = +page_size entries) or “entries” (e.g. next = +10 entries). If “pages,” then 1/2/5/10/50 = 1 page, 2 pages, …; if “entries,” then 1/2/5/10/50 = 1 entry, 2 entries, …. Same presets can apply either way; document the chosen semantics in the UI (e.g. “Jump 5 pages” vs “Jump 5 entries”).

3. **Layout**
   - **List view:** **Single pane** only — one “page” of the dictionary at a time, like a single spread of a paper dictionary. No side panel; the list fills the main area.
   - **Detail view (current implementation):** Opens as a **dedicated full-screen detail screen** (list hidden, detail shown alone) and returns to list on back/escape.
   - **Future refinement options:** Expand-in-place or side panel can still be evaluated later, but full-screen detail is the baseline for Phase 1 due to readability in small terminals.

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────┐
│  TUI (ratatui + crossterm)                              │
│  - List view (page of entries)                           │
│  - Detail view (expanded definition)                     │
│  - Key bindings (nav, select, back, random page, etc.)   │
└───────────────────────┬─────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────┐
│  App / Session                                          │
│  - Current dictionary, page index, selection             │
│  - Calls provider for list_entries() and get_detail()   │
└───────────────────────┬─────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────┐
│  Dictionary Provider API (trait)             │
│  - metadata(), entry_count(), list_entries(), get_detail() │
└───────────────────────┬─────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────┐
│  Implementations                                        │
│  - LocalProvider: reads pack from disk (JSONL or SQLite) │
│  - (Future: HybridProvider for fetch-on-expand if needed)│
└─────────────────────────────────────────────────────────┘
```

- **Single entry point:** App discovers packs under a config/data dir and opens one via the provider interface. All dictionaries (English now, Chinese later) use the same schema and provider.
- **Data on disk:** Each pack is a folder with a manifest and a data file. No runtime dependency on third-party APIs for core browsing.

---

## 3. Dictionary Pack Format

### 3.1 Location

- **Pack root:** `~/.config/dictionary-tui/packs/<pack-id>/` (or `$XDG_CONFIG_HOME` / equivalent).
- **Discovery:** App scans for directories containing `manifest.json`.

### 3.2 Manifest (`manifest.json`)

```json
{
  "id": "webster-1913",
  "name": "Webster's Unabridged 1913",
  "language": "en",
  "sort": "alphabetical",
  "entry_count": 70000,
  "data_file": "entries.jsonl",
  "license": "Public Domain",
  "source_url": "https://www.gutenberg.org/ebooks/673"
}
```

| Field | Purpose |
|-------|--------|
| `id` | Unique pack identifier (e.g. for install path and config). |
| `name` | Display name in TUI. |
| `language` | `en` | `zh` (and later others). Drives default sort and UI hints. |
| `sort` | `alphabetical` | `pinyin`. Provider must expose entries in this order. |
| `entry_count` | Total entries (for progress bar / random page). |
| `data_file` | Filename of the main data file (relative to pack root). |
| `license`, `source_url` | Attribution and optional “About” screen. |

### 3.3 Entry Schema (same for English and Chinese)

Used in both list view (subset) and detail view (full).

| Field | List | Detail | Notes |
|-------|------|--------|-------|
| `headword` | ✓ | ✓ | Primary display form (e.g. "hello", "你好"). |
| `sort_key` | ✓ | ✓ | For ordering: lowercase ASCII for English; normalized pinyin for Chinese (e.g. `ni3 hao3` or sortable form). |
| `pronunciation` | optional | ✓ | IPA, pinyin, or other (e.g. `[pɪˈɹɪəɹɪti]`, `nǐ hǎo`). |
| `short_definition` | optional | ✓ | One line or a few words for list view. |
| `full_definition` | — | ✓ | Full text or structured senses for detail view. |
| `phrases` | — | optional | For Chinese: phrases, 成语, examples. Array of `{ "form": "...", "definition": "..." }` or similar. |

- **List view:** Provider returns `headword`, `sort_key`, optionally `pronunciation`, `short_definition`.
- **Detail view:** Provider returns full entry including `full_definition` and optionally `phrases`/成语.

### 3.4 Data File Format

- **Preferred:** **JSONL** — one JSON object per line, one line per entry. Sorted by `sort_key`. Enables streaming and fixed-size page reads (e.g. read N lines from offset).
- **Alternative:** **SQLite** — one `.db` per pack, table with columns matching the schema, index on `sort_key`. `list_entries(offset, limit)` = `SELECT ... ORDER BY sort_key LIMIT limit OFFSET offset`.

Ingest scripts (see below) produce this format from raw sources so the app only reads, never writes, the data file.

---

## 4. Dictionary Provider API

Trait implemented by the app’s data layer (e.g. `LocalProvider`).

### 4.1 Types

- **ListEntry:** `{ headword, sort_key, pronunciation?, short_definition? }`
- **DetailEntry:** ListEntry + `full_definition?`, `phrases?` (and any other optional fields in the schema)

### 4.2 Interface

| Method | Returns | Purpose |
|--------|---------|--------|
| `metadata()` | Same as manifest (id, name, language, sort, entry_count, …) | UI title, “About”, “Random page” range. |
| `entry_count()` | `int` | Total number of entries. |
| `list_entries(offset, limit)` | `list[ListEntry]` | One “page” of entries for list view. |
| `get_detail(headword_or_id)` | `Option<DetailEntry>` | Full entry for detail view (by headword or stable id if you add one). |

- **Random page:** App computes `random_offset` in `[0, entry_count - page_size]` and calls `list_entries(random_offset, page_size)`.
- **Optional later:** Async provider trait for fetch-on-expand; for now, only local data.

### 4.3 Adding a New Dictionary (for devs)

1. Obtain or build a data file that conforms to the entry schema and is sorted by `sort_key`.
2. Add a `manifest.json` in a new pack directory under the packs root.
3. (Optional) Contribute or use an ingest script that converts a known source (e.g. Webster, CC-CEDICT, Wiktextract) into the pack format.

No changes to core TUI or provider interface required.

---

## 5. Data Sources and Ingest

### 5.1 English (Phase 1)

| Source | Content | Ingest output |
|--------|---------|----------------|
| **Webster’s Unabridged 1913** | Word + definition (public domain) | `entries.jsonl` with headword, sort_key (lowercase headword), short_definition = first line of definition, full_definition = full text. |
| **WordNet** (optional) | Synsets + glosses; good for short definitions | Same schema; headword = lemma, sort_key = normalized form. |

- **Deliverable:** At least one ingest binary (e.g. `cargo run --bin ingest_webster`) or script that produces a pack under `packs/webster-1913/` (or similar) with valid `manifest.json` and `entries.jsonl`.

### 5.2 Chinese

| Source | Content | Ingest output |
|--------|---------|----------------|
| **CC-CEDICT** | Traditional/simplified, pinyin, English definitions | Pack with `language: "zh"`, `sort: "pinyin"`, sort_key = normalized pinyin; headword = simplified (or `--traditional`); list/detail and search by pinyin. Run: `python3 scripts/ingest_cedict.py` (optional `--source-file` if URL fails). |
| **Wiktionary zh-extract** (e.g. Kaikki) | Chinese entries, **Chinese definitions**, 成语, phrases | For Chinese-in-Chinese definitions: filter Mandarin; map to same schema; add `phrases` for 成语. Ingest script TBD. |

- **Deliverable:** `scripts/ingest_cedict.py` produces `packs/cc-cedict/` (pinyin-indexed, pinyin-searchable). For definitions in Chinese, use a Wiktionary zh–based ingest when available.

### 5.3 Pack Discovery and Install

- **Bundled:** Ship one English pack (e.g. Webster 1913) in the repo or as a separate download so the app works out of the box with at least one dictionary.
- **User install:** Document “Add a dictionary” = download or run ingest, then place the pack folder in `~/.config/dictionary-tui/packs/<pack-id>/` (or equivalent). App discovers it on next launch.
- **Ingest boundary:** Prefer direct downloadable datasets (official dumps/files) over web crawling; ingest pipeline handles transform + validation into pack format.

---

## 6. Tech Stack and Repo Layout

### 6.1 Stack

- **Rust** (edition 2021; target 1.70+ or similar)
- **ratatui** — TUI (widgets, layout, key handling)
- **crossterm** — terminal backend (raw mode, key events)
- **serde** + **serde_json** — manifest and entry (de)serialization
- **Optional:** **rusqlite** if supporting SQLite-backed packs; **dirs** or **directories** for config path

### 6.2 Suggested Repo Layout

```
dictionary-tui/
├── README.md
├── PLAN.md                    # This document
├── Cargo.toml                  # workspace or single crate with [[bin]] for ingest
├── src/
│   ├── main.rs                 # Binary entry; runs TUI app
│   ├── lib.rs                  # Library root (provider, pack, schema, app)
│   ├── app.rs                  # TUI loop, screens, key bindings
│   ├── provider.rs             # Provider trait + LocalProvider (JSONL / SQLite)
│   ├── pack.rs                 # Manifest parsing, pack discovery
│   └── schema.rs               # ListEntry, DetailEntry, PackManifest (serde structs)
├── bins/                       # Optional: separate ingest binaries
│   └── ingest_webster.rs       # Gutenberg Webster 1913 → pack (or under src/bin/)
├── packs/                      # Optional: one bundled pack for dev/demo
│   └── webster-1913/
│       ├── manifest.json
│       └── entries.jsonl
└── tests/
    ├── provider_test.rs
    └── pack_test.rs
```

- **Ingest:** Either `src/bin/ingest_webster.rs` (e.g. `cargo run --bin ingest_webster`) or a separate crate in the repo. Same pack format; ingest can be Rust (single repo) or Python (external scripts) if preferred for rapid iteration.

---

## 7. Phases and Milestones

### Phase 1 — English dictionary, core TUI

1. **Pack format & provider**
   - Define manifest and entry schema (structs + serde in `schema.rs`).
   - Implement `Provider` trait and `LocalProvider` for JSONL (and optionally SQLite): `metadata()`, `entry_count()`, `list_entries(offset, limit)`, `get_detail(headword)`.
   - Pack discovery: list packs under config dir, load manifest, open provider per pack.
2. **Ingest**
   - One English source (Webster 1913 or WordNet) → Rust binary or script → valid pack (manifest + entries.jsonl).
3. **TUI**
   - Single dictionary mode: choose a pack (or default to first/bundled).
   - List view: **single pane**, one page of entries (headword, optional short_definition); up/down or left/right for prev/next.
   - **Random page:** Dedicated key to jump to a random page.
   - **Page-turn increment:** Cycle through presets (1/2/5/10/50) and support custom value; nav keys advance by current increment (pages or entries — decide and document).
   - Detail view: on select, show full definition (and optional pronunciation); key to go back to list. **Current baseline:** dedicated full-screen detail screen.
4. **Polish**
   - Configurable page size; basic error handling (missing pack, corrupt data); clear key bindings (e.g. help screen); show current increment in UI.

### Phase 2 — Chinese-ready and optional second pack

1. **Schema and provider**
   - Ensure `language` and `sort` (alphabetical vs pinyin) are respected; no UI assumptions that sort_key is ASCII.
   - Display: support pinyin and optional traditional/simplified in list and detail (fields already in schema).
2. **CC-CEDICT ingest**
   - Binary or script: download or accept CEDICT file, parse lines, output pack with pinyin as sort_key, English definitions as short/full_definition.
   - Add one CC-CEDICT pack to `packs/` or document as “first Chinese pack.”
3. **TUI**
   - Dictionary selection (if multiple packs installed): choose English vs Chinese pack; list view uses correct sort order and displays pinyin when present.

### Phase 3 — Chinese definitions and 成语

1. **Data**
   - Ingest from Wiktionary zh-extract (or similar): map to same schema, add `phrases` for 成语 and common phrases.
2. **TUI**
   - Detail view: show `phrases` section when present (e.g. “成语 / 常见词组” with list of form + definition).

### Phase 4 — Community extensions and docs

1. **Docs**
   - “Adding a new dictionary”: manifest fields, entry schema, data file format (JSONL/SQLite), example ingest pipeline.
   - Document provider API (for any future alternative backends).
2. **Convenience**
   - Optional: CLI or in-TUI “Install dictionary” that runs a known ingest or downloads a prebuilt pack from a fixed URL.
   - Publish contributor packs in common channels (GitHub Releases, object storage + manifest index, community registry file).

---

## 8. Out of Scope (for now)

- **Online APIs:** No runtime lookup from third-party APIs; all data from local packs. (Design allows a future “fetch on expand” provider without changing the UX contract.)
- **Editing:** Read-only; no in-app editing of definitions.
- **Search:** Optional later; not required for “page flip” UX. If added, can be implemented as filter over list_entries or a separate index.

---

## 9. Success Criteria

- **Phase 1:** User can install the app, run with one English pack, flip through pages with responsive key navigation, and expand any word to see full definition.
- **Phase 2:** User can add a CC-CEDICT pack and browse Chinese words in pinyin order with English definitions.
- **Phase 3:** User can use a Chinese pack that includes Chinese definitions and 成语 in the detail view.
- **Phase 4:** A new developer can add a new dictionary by following the plan and docs without modifying core TUI code.

---

*Document version: 1.1. Rust + ratatui; English-first; Chinese and extensibility designed in from the start.*
