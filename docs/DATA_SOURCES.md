# Data sources

Reference for the six dictionary/lexical data sources used to build packs. Each section documents schema, extractable fields, and file format. The pack schema (list/detail entries) is defined in `src/schema.rs`; this doc describes the **upstream** sources and how they map.

---

## 1. wordset-dictionary

**Origin:** GitHub [StevensDeptECE/Dictionaries](https://github.com/StevensDeptECE/Dictionaries) — wordset-dictionary.

**File format:** Per-letter JSON files under the repo: `a.json` … `z.json`, plus `misc.json`. Each file is a **single JSON object** keyed by word (one key per headword).

**Schema (per file):**
- Top level: object `{ [word: string]: WordEntry }`.
- **WordEntry** (per word):
  - `word` (string) — headword.
  - `wordset_id` (string/number) — WordNet-style ID.
  - `meanings` (array) — list of sense objects:
    - `id` (string/number)
    - `def` (string) — definition text.
    - `speech_part` (string) — part of speech.
    - `example` (string, optional)
    - `synonyms` (array, optional)
  - `labels` (array, optional) — e.g. `{ "name": string, "is_dialect": boolean }`.
  - `editors`, `contributors` (optional) — metadata.

**Extractable fields:** `word`, `wordset_id`, `meanings[].def`, `meanings[].speech_part`, `meanings[].example`, `meanings[].synonyms`, `labels`.

**Notes:**
- **No pronunciation** (no IPA or pinyin).
- **Multiple definitions** per word via `meanings[]`.
- **Word-level only** (no phrase/idiom distinction in structure; all entries are single words).

---

## 2. chinese-xinhua

**Origin:** GitHub [pwxcoo/chinese-xinhua](https://github.com/pwxcoo/chinese-xinhua). Data under `data/`.

**File format:** JSON files:
- `word.json` — 汉字 (single characters).
- `idiom.json` — 成语 (idioms).
- `ci.json` — 词语 (words/phrases).
- `xiehouyu.json` — 歇后语 (riddle–answer sayings).

**Schema:**

| File | Entry shape | Key fields |
|------|-------------|------------|
| **word.json** | One object per 汉字 | `word`, `oldword`, `strokes`, `pinyin`, `radicals`, `explanation`, `more` |
| **idiom.json** | One object per 成语 | `word`, `pinyin`, `abbreviation`, `derivation`, `example`, `explanation` |
| **ci.json** | One object per 词语 | `ci`, `explanation` |
| **xiehouyu.json** | One object per 歇后语 | `riddle`, `answer` |

**word.json (汉字):**
- `word` (string) — character.
- `oldword` (string, optional) — traditional/variant.
- `strokes` (number) — stroke count.
- `pinyin` (string) — pronunciation.
- `radicals` (string) — radical info.
- `explanation` (string) — definition/explanation.
- `more` (optional) — extra (e.g. more readings).

**idiom.json (成语):**
- `word` (string) — idiom (four chars typically).
- `pinyin` (string).
- `abbreviation` (string, optional).
- `derivation` (string, optional) — origin/source.
- `example` (string, optional).
- `explanation` (string) — meaning.

**ci.json (词语):**
- `ci` (string) — headword (word or phrase).
- `explanation` (string).

**xiehouyu.json (歇后语):**
- `riddle` (string) — first part.
- `answer` (string) — punchline/answer.

**Extractable fields:** headword (`word`/`ci`/`riddle`+`answer`), `pinyin`, `strokes`, `radicals`, `explanation`, `derivation`, `example`, `abbreviation`, `oldword`, `more`; for xiehouyu: `riddle`, `answer`.

**Notes:**
- **Pronunciation:** pinyin in `word.json` and `idiom.json`; **ci.json** and **xiehouyu.json** typically **lack** pinyin.
- **Single vs multiple:** One main `explanation` per entry (may contain semicolons or list-like text).
- **Word vs phrase/idiom:** Explicit file types — 字 vs 成语 vs 词语 vs 歇后语.

---

## 3. kaikki-en (English Wiktextract)

**Origin:** [Kaikki.org](https://kaikki.org/) — Wiktextract-based dumps. English: e.g. `kaikki.org-dictionary-English.jsonl`.

**File format:** JSONL — **one line per (word, part-of-speech)**. Each line is one JSON object.

**Schema (top-level):**
- `word` (string) — headword.
- `pos` (string) — part of speech: `"noun"`, `"verb"`, `"adj"`, `"adv"`, `"symbol"`, etc.
- `lang_code` (string) — e.g. `"en"`.
- `senses` (array) — sense objects (see below).
- `sounds` (array) — e.g. `{ "ipa": string, "tags": [] }`; first `ipa` used for pronunciation.
- `forms` (array) — inflections: `{ "form": string, "tags": [] }`.
- `head_templates` (array) — e.g. expansion template.
- `etymology_text` (string, optional).
- `etymology_templates`, `etymology_number` (optional).
- `antonyms`, `synonyms`, `related` (arrays of `{ "word": string }`).
- `translations`, `categories`, `wikipedia`, etc. (optional).

**Sense object (each item in `senses`):**
- `glosses` (array of strings) — definitions; first or concatenation used for short/full.
- `raw_glosses` (optional).
- `tags` (array) — e.g. "figuratively", "broadly".
- `qualifier` (string, optional).
- `examples` (array) — `{ "text": string, "type": "example" }`.
- `links`, `categories`, etc. (optional).

**Extractable fields:** `word`, `pos`, `senses[].glosses`, `senses[].tags`, `senses[].examples`, `sounds[].ipa`, `forms`, `head_templates`, `etymology_text`, `synonyms`, `antonyms`, `related`.

**Notes:**
- **Pronunciation:** IPA from `sounds[].ipa` (no pinyin; English).
- **Multiple definitions** — one line per (word, pos), multiple senses per line.
- **Word-level** — headwords are single words; multi-word phrases can appear as separate headwords.

---

## 4. kaikki-zh-en (Chinese → English from en Wiktionary)

**Origin:** Kaikki “Chinese” dictionary (from **en** Wiktionary): e.g. `kaikki.org-dictionary-Chinese.jsonl`. Definitions are in **English**.

**File format:** Same as kaikki-en — JSONL, one line per (word, pos).

**Schema:** Same top-level and sense structure as kaikki-en. Difference:
- `lang_code` — `"zh"`.
- **Pronunciation:** Prefer `sounds[].zh_pron` (Pinyin, Jyutping, Bopomofo, etc., with tags like "Mandarin", "Cantonese"); may also have `sounds[].ipa` (e.g. Sinological-IPA).

**Extractable fields:** Same as kaikki-en, plus `sounds[].zh_pron` for Mandarin/other Chinese readings.

**Notes:**
- **Pronunciation:** `zh_pron` (and optionally `ipa`).
- **Multiple definitions** per (word, pos); senses in **English**.
- **Word/character** headwords; some entries may be multi-character or phrases depending on Wiktionary.

---

## 5. kaikki-zh-zh (Chinese → Chinese, zh-extract)

**Origin:** Kaikki zh-extract — from **zh** Wiktionary (Chinese-language Wiktionary). File: e.g. `kaikki.org/dictionary/downloads/zh/zh-extract.jsonl.gz`.

**File format:** JSONL, same structure as other Kaikki dumps.

**Schema:** Same top-level and sense structure. Differences from kaikki-zh-en:
- **Glosses** (definitions) are in **Chinese** (`senses[].glosses`).
- **Pronunciation:** `sounds[].zh_pron` (and sometimes `ipa`).
- May include `redirects` (e.g. traditional form as alternate headword).

**Extractable fields:** Same as kaikki-zh-en; glosses are Chinese.

**Notes:**
- **Pronunciation:** `zh_pron` (and optionally `ipa`).
- **Multiple definitions**; all text in Chinese.
- **Word/character** level; same structural distinction as other Kaikki.

---

## 6. cc-cedict

**Origin:** [CC-CEDICT](https://cc-cedict.org/) — Chinese–English dictionary. Export used: e.g. MDBG TSV/UTF-8 (line-based).

**File format:** Line-based (e.g. tab-separated or custom format). Our pack format is **JSONL** with one JSON object per line (post-processing).

**Pack schema (our normalized entries):**
- `headword` (string)
- `sort_key` (string) — e.g. pinyin with tone numbers for sorting.
- `pronunciation` (string) — display form (e.g. "A diàn").
- `short_definition` (string) — truncated for list view.
- `full_definition` (string) — full definition text.
- `part_of_speech` (string, optional) — e.g. "v.", "n.", "Tw."

**Upstream:** Raw lines contain headword, pinyin, part-of-speech, and definition(s); we merge into short/full and add `sort_key`.

**Extractable fields:** headword, sort_key, pronunciation, short_definition, full_definition, part_of_speech.

**Notes:**
- **Pronunciation:** Present (pinyin, often with regional tags).
- **Single or multiple:** One line per headword; definition can be multi-sense (slash-separated or similar in raw).
- **Word and phrase:** Headwords include single characters, words, and multi-character phrases (词语, 成语, etc.); no separate type field in our pack (can infer from length/structure if needed).

---

## Superset of extractable fields

One row per unified field; columns show whether each source provides it (Y/N or note).

| Field name (unified) | wordset-dictionary | chinese-xinhua (word/idiom/ci) | kaikki-en | kaikki-zh-en | kaikki-zh-zh | cc-cedict |
|----------------------|--------------------|--------------------------------|-----------|--------------|--------------|-----------|
| headword | Y | Y (word/idiom/ci) | Y | Y | Y | Y |
| pronunciation | N | Y (word, idiom); N for ci | Y (IPA) | Y (zh_pron/ipa) | Y (zh_pron/ipa) | Y |
| part_of_speech | Y (as speech_part) | N (word.json); idiom/ci no pos | Y | Y | Y | Y |
| short_definition | Y (first def only) | Y (explanation) | Y (first gloss only) | Y (first gloss only) | Y (first gloss only) | Y |
| full_definition | Y | Y | Y | Y | Y | Y |
| phrases/idioms | N (word-level only) | Y (idiom.json, ci.json) | via multi-word headwords | Y | Y | Y (multi-char headwords) |
| examples | Y | Y (idiom) | Y | Y | Y | N |
| synonyms | Y | N | Y | Y | Y | N |
| radicals | N | Y (word only) | N | N | N | N |
| strokes | N | Y (word only) | N | N | N | N |
| derivation | N | Y (idiom) | N | N | N | N |
| etymology | N | N | Y | Y | Y | N |
| labels/tags | Y | N | Y | Y | Y | N |
| forms/inflections | N | N | Y | Y | Y | N |
| sort_key | derived | derived | derived | derived | derived | Y / derived |
| xiehouyu | N | Y (xiehouyu.json only) | N | N | N | N |

---

## Overlapping set

Fields provided by **at least two** sources. Use this to see which sources can feed a unified word list and which are phrase-only or supplementary.

| Field | wordset-dictionary | chinese-xinhua (word/idiom/ci) | kaikki-en | kaikki-zh-en | kaikki-zh-zh | cc-cedict |
|-------|--------------------|--------------------------------|-----------|--------------|--------------|-----------|
| **headword** | Y | Y | Y | Y | Y | Y |
| **pronunciation** | N | Y (word, idiom; not ci) | Y | Y | Y | Y |
| **part_of_speech** | Y (as speech_part) | N (word.json has no pos; idiom/ci no pos) | Y | Y | Y | Y |
| **short_definition** | Y | Y | Y | Y | Y | Y |
| **full_definition** | Y | Y | Y | Y | Y | Y |
| **phrases/idioms** | N | Y (idiom.json, ci.json) | Y (via grouping / multi-word headwords) | Y | Y | Y |

**Implications:**
- **Unified word list:** wordset, kaikki-en, kaikki-zh-en, kaikki-zh-zh, and cc-cedict can all contribute headword + short/full definition; wordset lacks pronunciation; chinese-xinhua word/idiom have pronunciation but word.json has no part_of_speech.
- **Phrase-only or supplementary:** chinese-xinhua idiom and ci are phrase/idiom-focused (ci has no pinyin); xinhua word.json is character-focused with strokes/radicals. Use xinhua for idioms/词语 and cedict/kaikki for unified headword + pronunciation + pos + definition.
- **Pronunciation:** wordset N; xinhua Y for word/idiom; kaikki all Y; cedict Y.
- **Part of speech:** wordset Y (speech_part); xinhua N for word.json; kaikki all Y; cedict Y.
