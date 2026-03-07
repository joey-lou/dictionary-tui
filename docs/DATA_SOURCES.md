# Data sources

Reference for the dictionary data sources used to build packs. The unified pack schema is defined in `py/ingest/models.py` (Python) and `src/schema.rs` (Rust).

---

## 1. Webster's Unabridged 1913 (English)

**Origin:** [Project Gutenberg #29765](https://www.gutenberg.org/ebooks/29765) — Webster's Unabridged Dictionary, 1913 edition.

**Format:** Plain text with structured entries. Each entry starts with a headword in ALL CAPS on its own line, followed by pronunciation in diacritical notation, POS, etymology, and numbered definitions.

**Entry shape:**

| Field | Location | Notes |
|-------|----------|-------|
| headword | ALL CAPS line | Entry boundary |
| pronunciation | First token on body line (e.g. `Ab"stract`) | Diacritical: `"` = stress, `*` = syllable break |
| POS | After comma on first line (e.g. `n.`, `a.`, `v. t.`) | Mapped to normalized labels |
| etymology | `Etym: [...]` block | Stripped from definitions |
| definitions | `Defn:` or numbered (`1.`, `2.`, …) | First definition used for short_definition |

**Pack mapping:** One `HeadEntry` per entry. Pronunciation converted: `"` → `ˈ` (stress), `*` → `·` (syllable). POS normalized (e.g. `n.` → `noun`, `a.` → `adj.`). Short definition ≤80 chars from first definition.

**Ingest:** `python3 py/ingest_webster1913.py`

---

## 2. Wordset Dictionary (English)

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

**Pack mapping:** One `HeadEntry` per (word, POS). No pronunciation (source lacks it).

**Ingest:** `python3 py/ingest_wordset.py`

---

## 3. chinese-xinhua (Chinese–Chinese)

**Origin:** [pwxcoo/chinese-xinhua](https://github.com/pwxcoo/chinese-xinhua). Data under `data/`.

**Files:**

| File | Content | Key fields |
|------|---------|------------|
| `word.json` | Single characters (汉字) | `word`, `pinyin`, `strokes`, `radicals`, `explanation` |
| `idiom.json` | Idioms (成语) | `word`, `pinyin`, `explanation`, `derivation`, `example` |
| `ci.json` | Words/phrases (词语) | `ci`, `explanation` |

**Pack mapping:** `word.json` → head entries (single characters). POS extracted from `〈名〉`/`〈动〉`-style markers and `本義` patterns in explanation text (Chinese labels: 名/动/形/副/数/etc.). Short definition cleaned: headword char, inline pinyin, and etymology stripped. `idiom.json` + `ci.json` → phrases grouped under leading character.

**Ingest:** `python3 py/ingest_xinhua.py`

---

## 4. CC-CEDICT (Chinese–English)

**Origin:** [CC-CEDICT](https://cc-cedict.org/) via [MDBG](https://www.mdbg.net/).

**Format:** Line-based: `traditional simplified [pinyin] /def1/def2/…/`

**Fields per line:** headword (simplified or traditional), numbered pinyin, slash-separated English definitions.

**Pack mapping:** Single-character entries → heads with pronunciation (pinyin with tone marks) and POS inferred from definition text. Multi-character entries → phrases under leading character.

**Ingest:** `python3 py/ingest_cedict.py`

---

## Field coverage

| Field | Webster's 1913 | Wordset | chinese-xinhua | CC-CEDICT |
|-------|----------------|---------|----------------|-----------|
| headword | ✓ | ✓ | ✓ | ✓ |
| pronunciation | ✓ (diacritical) | ✗ | ✓ (pinyin) | ✓ (pinyin) |
| part_of_speech | ✓ (96%) | ✓ | partial (9%) | partial (inferred) |
| short_definition | ✓ | ✓ | ✓ | ✓ |
| full_definition | ✓ | ✓ | ✓ | ✓ |
| phrases/idioms | ✗ | ✗ | ✓ | ✓ |
