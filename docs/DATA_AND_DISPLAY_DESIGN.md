# Data and Display Design

Unified data structure and UI design across all languages.

---

## 1. Entry Schema

One JSONL line per `(headword, pronunciation, part_of_speech)` tuple:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `headword` | string | ✓ | Atomic unit: single word (EN) or single character (ZH) |
| `sort_key` | string | ✓ | **Ordering + search only** (not shown in list). Lowercase (EN), pinyin (ZH). Used by Rust for sort order and search matching. |
| `leading_key` | string | ✓ | Grouping key (equals headword for heads) |
| `pronunciation` | string? | | **Display only:** shown in the list/detail "Pron." column. Diacritical (Webster), pinyin (ZH). Not used for sort or search. |
| `part_of_speech` | string? | | POS label (noun, adj., 名, 动, etc.); shown in list/detail. |
| `short_definition` | string | ✓ | One-line summary for list view |
| `full_definition` | string | ✓ | Full text for detail view |
| `phrases` | PhraseItem[]? | | Compound words/idioms grouped under this head |

Entries with the same headword but different POS or pronunciation are separate lines, grouped together by the TUI.

---

## 2. Phrases and Idioms

- **Not shown in the word list.** The index shows only atomic headwords.
- **Stored as `PhraseItem[]`** inside the head entry's `phrases` array.
- **Rendered** in the detail view under a "Phrases:" section (`form — definition` per line).

---

## 3. Sources

| Use case | Source | Entries | POS | Pron. |
|----------|--------|---------|-----|-------|
| **English** | Webster's 1913 | 109K | 96% | 96% (diacritical) |
| **Chinese–Chinese** | chinese-xinhua | 17K | 9% (Chinese labels) | ✓ (pinyin) |
| **Chinese–English** | CC-CEDICT | 13K | partial (inferred) | ✓ (pinyin) |

---

## 4. List View Display

All dictionaries share the same column layout with a header row:

```
┌─ Entries · Collapsed ───────────────────────────┐
│ Word           POS    Pron.        Definition    │
│ Abstract       adj.   Abˈstract    Withdraw; …   │
│ Apple          noun   Apˈple       The fleshy …   │
│ …                                                │
└──────────────────────────────────────────────────┘
```

**Column order:** indicator → Word → POS → Pron. → Definition

**Collapse/expand:**
- Entries with the same headword (different POS or pronunciation) are grouped.
- Collapsed view: one row per unique headword; `-` indicator if variants are hidden.
- Expanded view: all entries visible; `+` on the group header.
- Toggle with Space key.

---

## 5. Detail View

Shows the selected entry's full information:
- Headword, POS, pronunciation
- Full definition text
- Phrases/idioms (when present)

---

## 6. Sorting

- **Alphabetical** (English): sorted by `sort_key` (lowercase headword).
- **Pinyin** (Chinese): sorted by pinyin `sort_key`. Entries with the same headword are kept adjacent (sorted by the lowest pinyin reading of the headword group).
