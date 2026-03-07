# Data and Display Design

Unified data structure and UI design across all languages.

---

## 1. List Record Shape

One row per `(headword, pronunciation, part_of_speech)`:

| Field | Description |
|-------|-------------|
| `headword` | Atomic unit: single word (EN) or single character (ZH) |
| `pronunciation` | Phonetic form (IPA or pinyin); null when source lacks it |
| `part_of_speech` | Normalized POS (noun, verb, adj, adv, …) |
| `short_definition` | One-line summary for list view |

Multiple definitions for the same tuple appear only in the detail view, not as separate list rows.

---

## 2. Phrases and Idioms

- **Not in the word list.** The index shows only atomic headwords.
- **Stored as `PhraseItem[]`** inside the head entry's `phrases` array.
- **Displayed** in the detail view when present, as a dedicated "Phrases" section.

---

## 3. Sources

| Use case | Source | Notes |
|----------|--------|-------|
| **English** | Wordset | 77K words, clean POS, no pronunciation |
| **Chinese–Chinese** | chinese-xinhua | 17K characters + 295K phrases/idioms |
| **Chinese–English** | CC-CEDICT | 13K character heads + 102K compound phrases |

---

## 4. Schema

### HeadEntry (one JSONL line)

| Field | Type | Required |
|-------|------|----------|
| `headword` | string | ✓ |
| `sort_key` | string | ✓ |
| `leading_key` | string | ✓ |
| `pronunciation` | string? | |
| `part_of_speech` | string? | |
| `short_definition` | string | ✓ |
| `full_definition` | string | ✓ |
| `phrases` | PhraseItem[]? | |

### PhraseItem

| Field | Type |
|-------|------|
| `form` | string |
| `definition` | string |

---

## 5. Display

### List view

Columns: headword, POS, short_definition. Pronunciation shown when present. One row per head entry.

### Detail view

- Headword, POS, pronunciation
- Full definition (numbered senses or full text)
- Phrases section when `phrases` is non-empty
