# Data and Display Design: Unified Structure and UI

Design for a clean word index, list/detail separation, phrase handling, and pack format.

---

## 1. Goal and List Record Shape

**Goal:** A clean index of **single words only**. Each list record represents exactly one row in the list view.

**List record shape:** One row per `(headword, pronunciation, part_of_speech)`:

| Field | Description |
|-------|-------------|
| `headword` | The word form (single word only in the list). |
| `pronunciation` | Phonetic form (e.g. IPA, pinyin). |
| `part_of_speech` | POS tag (e.g. noun, verb, adj, adv). |
| `short_definition` | One-line summary for the list; one sense only. |

- **One record per (headword, pronunciation, POS).** Multiple senses for the same triple are **not** separate list rows; they appear only in the detail view.
- **Multiple definitions** for the same (headword, pronunciation, POS) are shown in the **detail view only**, as numbered senses.

---

## 2. Phrases and Idioms

- **Not in the word list.** The list shows only single words (headwords). Phrases and idioms are excluded from the main index.
- **Separate structure:** Store phrases in either:
  - A **phrases array** keyed by `leading_key` (and optionally headword), or
  - A dedicated **phrases file** (e.g. `phrases.jsonl`) keyed for lookup (see §6).
- **Display:** When the user opens a headword in the detail view, show a **phrases/idioms section** when phrases exist for that headword (or leading key). No phrase rows in the list.

---

## 3. Recommended Sources

| Use case | Preferred source | Notes |
|----------|------------------|--------|
| **EN (English)** | **wordset** | Cleaner data; prefer for EN list/detail. |
| **ZH–ZH (Chinese definitions)** | **chinese-xinhua** | Cleaner Chinese-in-Chinese data. |
| **ZH–EN (Chinese–English)** | **cc-cedict** | Standard for Chinese–English. |
| **Richer coverage** | **Kaikki** | Use only where broader coverage is needed; note quality and consistency concerns. |

Source selection should favor wordset (EN) and chinese-xinhua (ZH-ZH) for cleaner data; use cc-cedict for ZH–EN; use Kaikki only when richer coverage is required.

---

## 4. Schema

Keep **ListEntry** and **DetailEntry** as the core types, with the following rules:

### ListEntry

- One record per `(headword, pronunciation, part_of_speech)`.
- Fields: `headword`, `pronunciation`, `part_of_speech`, `short_definition`, plus `sort_key` and optional `leading_key` for indexing.
- **No** phrase rows: `is_phrase` can be omitted or ignored for list generation; list contains only single-word entries.

### DetailEntry

- Same uniqueness: one detail record per `(headword, pronunciation, part_of_speech)`.
- **Optional `definitions[]`:** Array of strings for multiple senses. When present, detail view shows numbered definitions instead of a single `full_definition`.
- **Optional `full_definition`:** Single string; use when there is only one sense or when merging senses into one block.
- **Optional `phrases`:** `PhraseItem[]` in the detail entry. When present, detail view shows a “Phrases / Idioms” section.

### PhraseItem

- `form`: phrase or idiom text.
- `definition`: definition text for that phrase.

**Summary:** Enforce one record per (headword, pronunciation, part_of_speech). Add optional `definitions[]` in DetailEntry for multiple senses. Keep phrases as optional `PhraseItem[]` in DetailEntry.

---

## 5. Display

### List view

- **Columns (or row content):** headword, pronunciation, part_of_speech, short_definition.
- One row per list entry (one per headword–pronunciation–POS).
- No phrases or idioms in the list.

### Detail view

- **Primary content:** Either `full_definition` or numbered `definitions[]` (when present).
- **Phrases/idioms:** When the detail entry has a non-empty `phrases` array, show a dedicated section (e.g. “Phrases / Idioms”) listing each `PhraseItem` (form + definition).

---

## 6. Pack Format

- **List data:** JSONL, **one line per list entry**. Each line is a single ListEntry (or equivalent) for one (headword, pronunciation, part_of_speech).
- **Detail data:** Either:
  - **Inline:** Same JSONL where each line can be a DetailEntry (with optional `definitions[]` and `phrases`), keyed by (headword, pronunciation, POS) for lookup; or
  - **Separate detail file:** e.g. one JSONL line per detail record, keyed the same way.
- **Phrases:** Either
  - **Inline:** Optional `phrases` array inside the DetailEntry in the detail line, or
  - **Sidecar:** Separate file (e.g. `phrases.jsonl`) with records keyed by `(leading_key, headword, pos)` (or equivalent) so the app can look up phrases when opening a headword’s detail.

Implementations may use inline phrases in the detail line or a sidecar `phrases.jsonl`; the app resolves phrases for a given headword/detail key and displays them in the detail view.

---

## 7. Design Recommendations and Source Priority

### 7.1 Source priority

| Use case | Primary source | Notes |
|----------|----------------|-------|
| **EN word list** | **wordset-dictionary** | Human-edited, ~177k words; no IPA. Prefer as first choice for EN. |
| **ZH–ZH (Chinese definitions)** | **chinese-xinhua** `word.json` | ~16k characters; includes pinyin, radicals, strokes. |
| **ZH–EN (Chinese–English)** | **cc-cedict** | Standard dictionary for Chinese–English. |

### 7.2 Phrase and idiom data

- **Chinese:** Use **chinese-xinhua** `idiom.json` and `ci.json` for idioms and 詞 (ci) phrases.
- **English / multilingual:** **Kaikki** phrases can be grouped under the headword and shown in the detail view when opening that head.

### 7.3 Implementation order

1. Ingest **wordset** → produce **EN pack**.
2. Ingest **xinhua** `word.json` → produce **ZH-ZH pack**.
3. Keep **cc-cedict** ingest for ZH–EN.
4. **Optional:** Ingest idioms/phrases (xinhua `idiom.json`, `ci.json`; Kaikki phrases) either as a **separate asset** or **attached to the head** (e.g. in detail or sidecar).

### 7.4 Build scope

- **No requirement** to support all six sources in one build.
- Prefer **quality** (wordset, xinhua, cedict) over Kaikki for the **initial demo**.
