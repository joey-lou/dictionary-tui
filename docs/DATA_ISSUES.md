# Data quality issues and planned fixes

This document tracks known data quality issues in each dictionary pack and the fixes we plan to apply via the ingest ETL pipeline. See `py/ETL_DESIGN.md` for the pipeline design and how to add new transforms.

---

## Webster 1913 (`webster1913-en`)

| Issue | Description | Status | Fix (transform / ingest change) |
|-------|-------------|--------|----------------------------------|
| Short def truncation mid-word | `short_definition` is cut at 80 chars with `…`, often mid-word (e.g. "the woo…") | **Addressed** | Webster extractor uses `truncate_at_word_boundary()`; pipeline has `TruncateShortDefinition(80)`. |
| Legacy markers in definitions | `Defn:`, `[Obs.]`, `[R.]`, source abbreviations (Shak., Chaucer) left in text | **Addressed** | `StripLegacyMarkers` in pipeline strips leading Defn: and inline [Obs.] / [R.]. |
| Sub-entry leakage | Some entries merge the next headword (e.g. Aard-Wolf ends with "AARONIC; AARONICAL...") | **Addressed** | `TruncateAtFirstAllCapsHeadword` keeps only content before ALL CAPS headword line. |
| Diacritics / escaped quotes | Raw `\"` and patterns like `A*ba\"sic` in definitions | **Addressed** | `NormalizeEscapedQuotes` replaces `\"`/`\'` with plain quotes, removes `*` diacritic. |
| POS inconsistency | Mix of "prep.", "adv.", "noun" with/without period; some entries missing POS | **Addressed** | `NormalizePOS` strips trailing period for consistent style. |
| ALL CAPS sub-headings | Section headers like "ABATIS; ABATTIS" appear inline in definition paragraph | **Addressed** | `StripAllCapsHeadings` removes ALL CAPS token runs from definition body. |

---

## Xinhua (`xinhua-zh-zh`)

| Issue | Description | Status | Fix (transform / ingest change) |
|-------|-------------|--------|----------------------------------|
| Missing / unencodable character | Literal `?` in definitions (e.g. 徶: "见\"徶?\"", 甼: "即?") | **Addressed** | `XinhuaFixPlaceholderAndCorrupt`; add more entries to `XINHUA_CHAR_FIXES` as needed. |
| Corrupt transliteration | 呗: "梵语 腰瓿thaka" — 腰瓿 is corrupt (should be 呗匿 or pathaka) | **Addressed** | `XINHUA_CHAR_FIXES`: 腰瓿 → pathaka in `xinhua_fix_placeholder_and_corrupt`. |
| Escaped quotes in display | JSON-escaped `\"` in definitions (e.g. 见\"峯岠\") — ensure TUI renders parsed string | **Addressed** | `NormalizeEscapedQuotes` in Xinhua pipeline; JSON output is correct; TUI renders. |
| Truncated short definitions | 编: short_definition ",扁声" (missing leading part); 苄: "基"; 蹩: full_definition just headword | **Addressed** | `XinhuaShortDefFromFirstSense` derives short from first sense; skips empty/circular. |
| Dense full_definition blocks | Single run-on paragraph (classical + 又見 + modern); no newlines between sections | **Addressed** | `XinhuaAddNewlinesInFullDef` inserts newlines after 又見 and sense numbering. |
| Numbering inconsistency | Mix of "1. 2.", "① ②", and unnumbered blocks | **Addressed** | `XinhuaNormalizeNumbering` maps ①②⑵ etc. to "1. 2." style. |
| Self-reference phrase defs | Many phrase definitions only "1.见\"某某\"" with no explanatory text | Optional | Documented as limitation; expand when possible in future. |
| Short def "pinyin+number" not normalized | Variant 別 (bié): short_definition is "bié1.同\"别\"" — leading "bié1." should become "1. " so it reads as sense numbering | **Addressed** | `xinhua_normalize_numbering` strips leading pinyin+digit.; `xinhua_normalize_short_def_leading(text, headword)` handles "頭pinyin1." in short defs. |
| Pronunciation/definition mismatch (source) | Variant 別 (dòu): pinyin is "dòu" but explanation says "dú1.同\"渎\"" — reading for 別=渎 is dú | **Addressed** | `XinhuaFixPronunciationFromDefinition`: when full_definition is short and starts with pinyin+digit., use that pinyin for pronunciation/sort_key. |
| Typo in word explanation (source) | 别: full_definition has "用东西卡籽门～住" — 卡籽 should be 卡住 | **Addressed** | `XINHUA_CHAR_FIXES`: 卡籽 → 卡住 in `xinhua_fix_placeholder_and_corrupt`. |
| Duplicate phrase forms | Same phrase form from idiom.json and ci.json (e.g. 别抱琵琶, 别出心裁) attached twice with different definitions | Open | Deduplicate by form when merging phrases (e.g. keep idiom entry when both exist). |
| Idiom pinyin typo (source) | 别鹤离鸾: pinyin "bié hè lí láun" — should be luán | Open | Add phrase-level fix or document; optional ETL fix in definition string. |
| Idiom explanation typo (source) | 别树一旗: "加成一家" — should be 自成一家 | Open | Add to `XINHUA_CHAR_FIXES`: 加成一家 → 自成一家. |

### Example: 别 (bié) in xinhua-zh-zh

- **Main entry 别**: short "分解", full def has typo 卡**籽**门 (should be 卡**住**). Phrases include duplicates (e.g. 别抱琵琶 twice: idiom with `[pinyin]` and ci without).
- **Variant 別 (bié)**: short_definition "**bié1.**同\"别\"" — leading pinyin+number not normalized.
- **Variant 別 (dòu)**: pronunciation "dòu" but text says "**dú**1.同\"渎\"" (mismatch).
- **Phrases**: 别鹤离鸾 has pinyin typo "láun" (should be luán); 别树一旗 has "加成一家" (should be 自成一家).

---

## CC-CEDICT (`cc-cedict`)

| Issue | Description | Status | Fix (transform / ingest change) |
|-------|-------------|--------|----------------------------------|
| (None critical) | Sample data is clean; slash-separated defs and (Tw) etc. are consistent | — | Optional: normalize parenthesis style (e.g. (Tw) vs (Taiwan)) in a transform if desired. |

---

## Cross-cutting (TUI / schema)

| Issue | Description | Status | Fix |
|-------|-------------|--------|-----|
| Phrases not in detail view | `phrases` array is in schema but the TUI detail panel does not render it | **Addressed** | Rust: `render_detail` now shows a "Phrases:" section with form — definition per phrase. |
| Single paragraph for full_definition | Multi-sense entries show as one block; hard to scan | Optional | Xinhua pipeline adds newlines; TUI wraps on `\n`. |

---

## Adding a new fix

1. Add or extend a **Transformer** in `py/common/etl/transforms.py` (or the dictionary package’s `transformers.py`).
2. Register it in that package’s `get_transformers()` (e.g. `py/webster1913/transformers.py`).
3. Update this table: set **Status** to **Addressed** and document the **Fix** in the last column.
4. Re-run the ingest script and commit updated pack data if the repo ships pre-built packs.
