# Kaikki: data-cleaning rules and before → after examples

The parser applies four rules so the pack is suitable for a single-word (EN) or single-character (ZH) index with phrases grouped under the head.

---

## Data-cleaning rules

1. **Language-only headwords**  
   No non-English headwords in the English pack; no non-Chinese headwords in the Chinese pack. We drop entries that fail the language filter (e.g. symbols, romanizations in ZH, or non‑ASCII scripts in EN where required).

2. **Collapse similar/same glosses; omit tags**  
   Duplicate or identical gloss strings are merged into one. Tags (e.g. *figuratively*, *broadly*) are not shown in the output so definitions stay simple.

3. **Index = single word (EN) or single character (ZH)**  
   The dictionary index lists only **single words** (EN) or **single characters** (字, ZH). Phrases (EN) or 词语 (ZH) do not get their own index row; they are grouped under the head:
   - **EN**: `leading_key` = first word of the headword (e.g. *rain* for “rain cats and dogs”).
   - **ZH**: `leading_key` = first character (e.g. 此 for 此時此刻).
   - `is_phrase` is `true` for multi-word (EN) or multi-character (ZH) headwords so the UI can treat them as phrases under the head.

4. **Same headword, different POS or pronunciation → separate records**  
   One headword with multiple parts of speech (e.g. *rain* noun vs *rain* verb) or multiple pronunciations (e.g. 行 xíng vs 行 háng) produces **multiple pack entries**, one per (headword, POS) or per (headword, POS, pronunciation) when the source has multiple sounds.

---

## Example 1: **rain cats and dogs** (phrase; Rule 3)

Phrases do **not** get their own line in the pack. They are collapsed into the head entry’s `phrases` array.

### BEFORE (raw, trimmed)

```json
{
  "word": "rain cats and dogs",
  "pos": "verb",
  "lang_code": "en",
  "senses": [
    {
      "glosses": ["To rain very heavily."],
      "tags": ["idiomatic", "impersonal"]
    }
  ]
}
```

### AFTER (no separate line for the phrase)

The pack has **one entry per head** (single word/字). The phrase “rain cats and dogs” does **not** appear as its own line. The **rain** (verb) head entry gets:

| Field | Value |
|-------|--------|
| **headword** | `rain` |
| **leading_key** | `rain` |
| **is_phrase** | `false` |
| **part_of_speech** | `verb` |
| **phrases** | `[{ "form": "rain cats and dogs", "definition": "To rain very heavily." }]` |

So the index lists only **rain**; opening it shows the head definitions plus the phrase “rain cats and dogs” in `phrases`.

---

## Example 2: **free** (adjective; Rule 2 — collapsed glosses, no tags)

Raw data has many senses repeating “Unconstrained.” with different tags. We merge duplicate glosses and drop tags.

### BEFORE (raw, first 8 senses)

- **word**: `free`, **pos**: `adj`
- **senses**: e.g.  
  - gloss `"Unconstrained."`, tags `null`  
  - gloss `"Unconstrained."`, second line `"Not imprisoned or enslaved."`, tags `null`  
  - gloss `"Unconstrained."`, second line `"Generous; liberal."`, tags `null`  
  - gloss `"Unconstrained."`, tags `["obsolete"]`  
  - …many more with “Unconstrained.” and various tags

### AFTER (one pack entry)

| Field | Value |
|-------|--------|
| **headword** | `free` |
| **leading_key** | `free` |
| **is_phrase** | `false` |
| **part_of_speech** | `adj` |
| **short_definition** | `Unconstrained.` |
| **full_definition** | `1. Unconstrained. 2. Not imprisoned or enslaved. 3. Generous; liberal. 4. Clear of offence or crime; guiltless; innocent. 5. Without obligations. …` *(unique glosses only; no tags)* |

Duplicate “Unconstrained.” appears once; other distinct gloss lines are kept in order.

---

## Example 3: **rain** noun vs **rain** verb (Rule 4 — same headword, different POS)

Same headword, different part of speech → two separate records.

### AFTER (two pack entries)

| Field | Record 1 (noun) | Record 2 (verb) |
|-------|------------------|-----------------|
| **headword** | `rain` | `rain` |
| **leading_key** | `rain` | `rain` |
| **is_phrase** | `false` | `false` |
| **part_of_speech** | `noun` | `verb` |
| **short_definition** | Condensed water falling from a cloud. | To have rain fall from the sky. |

Each (word, POS) comes from a separate line in Kaikki; we never merge them.

---

## Example 4: Multiple pronunciations (Rule 4)

When one Kaikki line has multiple `sounds` (e.g. different IPA variants), we emit **one pack entry per pronunciation** for that (headword, POS).

Example: **dictionary** (noun) with three IPA variants in `sounds` → three pack entries, same headword and POS, different `pronunciation` values (`/ˈdɪk.ʃə.nə.ɹi/`, `/ˈdɪk.ʃən.ɹi/`, `/ˈdɪkʃ.nə.ɹi/`).

---

## Example 5: **此** (single character, ZH) vs **此時此刻** (phrase, ZH; Rule 3)

### 此 (single character — index row)

| Field | Value |
|-------|--------|
| **headword** | `此` |
| **leading_key** | `此` |
| **is_phrase** | `false` |
| **part_of_speech** | `character` |
| **pronunciation** | `cǐ` *(from zh_pron)* |
| **short_definition** | `this` |

### 此時此刻 (phrase — under index key 此)

| Field | Value |
|-------|--------|
| **headword** | `此時此刻` |
| **leading_key** | `此` |
| **is_phrase** | `true` |
| **part_of_speech** | `noun` |
| **pronunciation** | `cǐshícǐkè` |
| **short_definition** | `this moment; now` |

The index shows **此** once; the phrase 此時此刻 is grouped under it (词语 under 字).

---

## Chinese → Chinese (zhwiktionary / zh-extract)

Data from **zh-extract** (`kaikki.org/dictionary/downloads/zh/zh-extract.jsonl.gz`) is Chinese headwords with Chinese definitions. The same four rules apply: language filter (CJK only), collapsed glosses, no tags, `leading_key` = first character, `is_phrase` for multi-character headwords, and separate records for different POS or pronunciation.

---

## Summary

| Rule | Effect |
|------|--------|
| 1. Language-only | EN: letters/spaces/hyphen/apostrophe only; ZH: CJK ideographs only. |
| 2. Glosses + tags | Merge duplicate glosses; do not output tags. |
| 3. Index = word/字 | Only head entries (single word/字) are written; phrases are in each head’s `phrases` array, not separate lines. |
| 4. Split by POS/pronunciation | One record per (headword, POS) from source; one record per pronunciation when multiple sounds. |

| Raw (Kaikki) | Pack output |
|--------------|-------------|
| `word`, `pos`, `senses` | headword, sort_key, part_of_speech, leading_key, is_phrase |
| `sounds[].ipa` / `sounds[].zh_pron` (ZH) | pronunciation (one per record; multiple records if multiple sounds) |
| All sense glosses | full_definition = numbered unique glosses only; short_definition = first gloss (truncated) |
| tags, qualifier | Omitted |

Run `python3 scripts/show_kaikki_edge_examples.py` to regenerate live examples from the Kaikki streams.
