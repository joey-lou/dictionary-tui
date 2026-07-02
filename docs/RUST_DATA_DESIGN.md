# What Rust Stores and Relies On

Design review: what the TUI actually stores in memory, reads from disk, and uses to operate and render the dictionary.

---

## 1. On-disk layout (input to Rust)

- **Per pack:** a directory with:
  - `manifest.json` — pack metadata (see below).
  - `entries.jsonl` — one JSON object per line; each line is a **full entry** (list + detail fields together).

Rust does **not** maintain a separate “list” vs “detail” file; one JSONL line = one logical entry with all fields.

---

## 2. Manifest (`PackManifest`)

| Field          | Type   | Used by Rust for |
|----------------|--------|-------------------|
| `id`           | string | Pack discovery (dedup), not shown in UI. |
| `name`         | string | Pack picker and footer (e.g. "Webster 1913"). |
| `language`     | string | **Search behavior:** `"zh"` ⇒ search by `sort_key` (e.g. pinyin); else search by `headword`. |
| `sort`         | string | **Sorting:** `"pinyin"` ⇒ pinyin sort + tone-normalized compare; else alphabetical by `sort_key`. **Search:** `"zh"` + `"pinyin"` ⇒ match using plain letters (ignore 声调). |
| `entry_count`  | u64    | Footer / info only. |
| `data_file`    | string | Filename for JSONL (e.g. `entries.jsonl`). |
| `license`      | optional | Not used for render/operation. |
| `source_url`   | optional | Not used for render/operation. |

So for **operation and render**, Rust really relies on: **`language`**, **`sort`**, **`name`**, **`data_file`**, and **`entry_count`** (for display). The rest are for discovery and metadata.

---

## 3. One JSONL line = one entry (list + detail)

The same JSON object is used for:

- **List view** — Rust only needs a subset of fields (see `ListEntry`).
- **Detail view** — Rust reads the full object as `DetailEntry` when you open detail (seek + read that line).

So conceptually we store “one big struct per line”; the split between `ListEntry` and `DetailEntry` is a **view** over the same data, not two stored blobs.

---

## 4. List view: what Rust keeps in memory

`LocalProvider` holds:

- **`entries: Vec<ListEntry>`** — every line parsed into a **list-shaped** view (so we don’t keep `full_definition` or `phrases` in RAM for the list).
- **`line_offsets: Vec<u64>`** — byte offset of each line in the JSONL file (for seek-to-line on detail).
- **`sorted_line_map: Vec<usize>`** — mapping from **sorted index** → **line index** (so we know which line to seek to for detail).
- **`root_indices: Vec<usize>`** — for each “root” (unique headword group), the first sorted index of that group (for collapsed view and group size).

So for **rendering the list**, Rust relies on the **list subset** of each entry.

---

## 4a. List view data format (exact contract)

The list view **displays** exactly five columns. For each row it uses only these fields from `ListEntry`:

| Column label  | Source field         | Format in data        |
|---------------|----------------------|------------------------|
| Word          | `headword`           | string (required)     |
| POS           | `part_of_speech`     | optional string       |
| Pron.         | `pronunciation`     | optional string       |
| Definition    | `short_definition`  | optional string       |
| (indicator)   | derived from grouping, not a field | — |

So the **data format the list view relies on for display** is: one `ListEntry` per row with at least `headword` and `sort_key`; the columns shown are `headword`, `part_of_speech`, `pronunciation`, `short_definition`. No other fields are drawn in the list.

**Not displayed but required for behavior:** `sort_key` (for ordering and search), `leading_key` (for grouping). So the list view **does not show** `sort_key`; it is used only internally for sort order and search.

---

## 4b. sort_key vs pronunciation (clearing the confusion)

These two fields have different roles. They are **not** interchangeable.

| Field           | Purpose                    | Shown in list? | Used for |
|-----------------|----------------------------|----------------|----------|
| **sort_key**    | Ordering + search key      | **No**         | Sort order; search (prefix/contains). For zh+pinyin packs, search matches after stripping tones. |
| **pronunciation** | What to show as “Pron.”   | **Yes**        | Display only. The “Pron.” column shows `pronunciation`. |

- **sort_key** is machine-facing: Rust uses it to sort the list and to match the search box. It is never rendered. For English packs it is typically lowercase headword; for pinyin packs it is the pinyin string for that row (e.g. `ài`).
- **pronunciation** is user-facing: it is the string shown in the “Pron.” column. For English it might be diacritical (e.g. `Apˈple`); for Chinese it is typically the same pinyin as `sort_key` (e.g. `ài`), but that is a choice of the ingest, not a requirement.

So: **same string in both** (e.g. xinhua: both `ài`) is common for Chinese, but the **semantics** differ: `sort_key` = “how to order and search this row”; `pronunciation` = “what to print in the Pron. column”. If ingest wanted to show tone-free pinyin in the list, it would put that in `pronunciation` and keep a tone-marked or normalized form in `sort_key` for ordering; Rust would not care.

---

### ListEntry fields (reference)

| Field              | Required | Used for |
|--------------------|----------|----------|
| `headword`         | ✓        | Display “Word” column; grouping; non-zh search. |
| `sort_key`         | ✓        | Sort order; zh search (and pinyin tone stripping when applicable). **Not displayed.** |
| `leading_key`      | optional | Grouping; defaulted if missing. |
| `pronunciation`    | optional | **Display “Pron.” column only.** |
| `short_definition` | optional | Display “Definition” column. |
| `part_of_speech`   | optional | Display “POS” column. |
| `is_phrase`        | optional | Not used in current list render. |

So for **list operation and render**, Rust depends on: **headword**, **sort_key**, **leading_key** (or headword for grouping), **pronunciation**, **short_definition**, **part_of_speech**. It does **not** need **full_definition** or **phrases** in memory for the list.

---

## 5. Detail view: what Rust reads on demand

When the user opens the detail screen, Rust:

1. Takes the **sorted index** of the selected list row.
2. Maps it to a **line index** via `sorted_line_map`.
3. **Seeks** to `line_offsets[line_index]` in the JSONL file.
4. Reads **one line** and deserializes it as **`DetailEntry`**.

So for **detail**, Rust relies on the **full** entry fields of that one line.

### DetailEntry fields (what detail rendering uses)

| Field               | Used for |
|---------------------|----------|
| `headword`          | “Headword: …” |
| `part_of_speech`    | “Part of speech: …” (if present). |
| `pronunciation`     | “Pronunciation: …” (if present). |
| `full_definition`   | Main body text. |
| `phrases`           | “Phrases:” section (each `form` + `definition`). |

Also present but not shown in detail UI: `sort_key`, `leading_key`, `short_definition` (already shown in list). So for **detail operation and render**, Rust depends on: **headword**, **part_of_speech**, **pronunciation**, **full_definition**, **phrases**.

---

## 6. Search behavior (what Rust relies on)

- **Packs with `language == "zh"` and `sort == "pinyin"`:**
  - Query and each entry’s **`sort_key`** are normalized to **plain letters** (tones stripped).
  - **Prefix** and **contains** matching use this normalized form so typing e.g. `ai` matches `ài`.

- **Other `language == "zh"` packs:**
  - Match on **`sort_key`** as-is (case-insensitive), no tone stripping.

- **Non-zh (e.g. English):**
  - Match on **`headword`** (case-insensitive).

So for search, Rust relies on: **manifest.language**, **manifest.sort**, and per-entry **sort_key** (and **headword** for non-zh).

---

## 7. Sorting and grouping (what Rust relies on)

- **Sort order** is computed once at pack load:
  - If **`manifest.sort == "pinyin"`**: sort by pinyin-normalized key (base letter + tone digit), with **primary key per headword** = “lowest” pinyin among entries with that headword, so groups stay together.
  - Else: sort by **`sort_key`** then **headword**.
- **Grouping** is by **headword**: consecutive entries with the same **headword** form one “root” group for collapsed/expanded view.

So for sort and grouping, Rust relies on: **manifest.sort**, and per-entry **headword** and **sort_key**.

---

## 8. Summary table: stored vs used

| Data | Where | Used for |
|------|--------|----------|
| **Manifest** | In memory with provider | `language` + `sort` → search and sort behavior; `name`, `entry_count` → UI; `data_file` → path to JSONL. |
| **ListEntry (subset per line)** | In memory (`entries`) | List render (headword, POS, pron, short def); search (sort_key or headword); sort/group (headword, sort_key). |
| **Line offsets + sorted map** | In memory | Pagination and “seek to line” for detail. |
| **Root indices** | In memory | Collapsed vs expanded view; group size; jump. |
| **Full line (DetailEntry)** | On demand from disk | Detail screen: headword, POS, pron, full_definition, phrases. |

---

## 9. Implications for “what we’re actually storing/relying on”

- **For list operation and render:** Rust stores and relies on **manifest** (language, sort, name, data_file, entry_count), **list subset of each entry** (headword, sort_key, leading_key, pronunciation, short_definition, part_of_speech), and the index structures (offsets, sorted map, root indices). It does **not** need **full_definition** or **phrases** in RAM for the list.
- **For detail:** Rust relies on the **full entry** (same JSONL line) and uses **headword**, **part_of_speech**, **pronunciation**, **full_definition**, **phrases** for the detail screen.
- **For search:** Rust relies on **manifest.language** and **manifest.sort** to decide whether to use **sort_key** (and whether to strip tones) or **headword**.
- **POS and pronunciation:** Rust only **displays** whatever is in **part_of_speech** and **pronunciation**; it does not interpret or normalize them. So populating and normalizing POS (e.g. to English) is entirely an **ingest/schema** concern, not a Rust runtime concern.

This is the design we’re operating and rendering the dictionary with on the Rust side.
