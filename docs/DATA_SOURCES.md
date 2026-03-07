# Data sources

Reference for the three dictionary data sources used to build packs. The unified pack schema is defined in `scripts/ingest/models.py` (Python) and `src/schema.rs` (Rust).

---

## 1. Wordset Dictionary (English)

**Origin:** [StevensDeptECE/Dictionaries](https://github.com/StevensDeptECE/Dictionaries) — wordset-dictionary.

**Format:** Per-letter JSON files (`a.json`…`z.json`) plus `misc.json`. Each file is a single JSON object keyed by word.

**Entry shape:**

| Field | Type | Notes |
|-------|------|-------|
| `word` | string | Headword |
| `meanings[].def` | string | Definition text |
| `meanings[].speech_part` | string | Part of speech |
| `meanings[].example` | string? | Usage example |
| `meanings[].synonyms` | string[]? | Synonyms |

**Pack mapping:** One `HeadEntry` per (word, POS). `short_definition` = first def (≤100 chars). `full_definition` = numbered list. No pronunciation (source lacks IPA).

**Ingest:** `python3 scripts/ingest_wordset.py`

---

## 2. chinese-xinhua (Chinese–Chinese)

**Origin:** [pwxcoo/chinese-xinhua](https://github.com/pwxcoo/chinese-xinhua). Data under `data/`.

**Files:**

| File | Content | Key fields |
|------|---------|------------|
| `word.json` | Single characters (汉字) | `word`, `pinyin`, `strokes`, `radicals`, `explanation` |
| `idiom.json` | Idioms (成语) | `word`, `pinyin`, `explanation`, `derivation`, `example` |
| `ci.json` | Words/phrases (词语) | `ci`, `explanation` |

**Pack mapping:** `word.json` → head entries (single characters). `idiom.json` + `ci.json` → phrases grouped under leading character. Pinyin from `word.json` and `idiom.json`; `ci.json` lacks pinyin.

**Ingest:** `python3 scripts/ingest_xinhua.py`

---

## 3. CC-CEDICT (Chinese–English)

**Origin:** [CC-CEDICT](https://cc-cedict.org/) via [MDBG](https://www.mdbg.net/).

**Format:** Line-based: `traditional simplified [pinyin] /def1/def2/…/`

**Fields per line:** headword (simplified or traditional), numbered pinyin, slash-separated English definitions.

**Pack mapping:** Single-character entries → heads. Multi-character entries → phrases under leading character with `[pinyin] definition` format. POS inferred from definition text (e.g. "to …" → verb).

**Ingest:** `python3 scripts/ingest_cedict.py`

---

## Field coverage

| Field | Wordset | chinese-xinhua | CC-CEDICT |
|-------|---------|----------------|-----------|
| headword | ✓ | ✓ | ✓ |
| pronunciation | ✗ | ✓ (pinyin) | ✓ (pinyin) |
| part_of_speech | ✓ | ✗ | partial (inferred) |
| short_definition | ✓ | ✓ | ✓ |
| full_definition | ✓ | ✓ | ✓ |
| phrases/idioms | ✗ | ✓ (idiom.json, ci.json) | ✓ (multi-char entries) |
