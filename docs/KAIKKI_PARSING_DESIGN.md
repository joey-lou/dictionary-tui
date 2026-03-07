# Kaikki dictionary parsing — design

This doc defines how we turn Kaikki/Wiktextract JSONL into dictionary packs. The parser lives under `py/` and produces one pack per variant (en, zh-en, zh-zh).

---

## 1. Goals

- **Index = heads only**: The pack’s `entries.jsonl` has one line per **index head** (one word in EN, one character 字 in ZH). The UI index is exactly these lines.
- **Phrases under the head**: Multi-word (EN) or multi-character 词语 (ZH) do **not** get their own line. They are stored in the head entry’s `phrases` array.
- **One row per (head, POS)**: Same headword with different part of speech (e.g. *rain* noun vs verb) → separate lines. Same headword, same POS → **one line**; we pick **one** pronunciation (no row per accent/romanization).
- **Clean definitions**: Deduplicate glosses, no tags in output. Language-only headwords.

---

## 2. Input: Kaikki JSONL

- One JSON object per line (word+POS or sense-level depending on dump).
- Top-level: `word`, `lang_code`, `pos`, `senses` (list of `{glosses, tags, ...}`), `sounds` (list of `{ipa, zh_pron, tags}`).
- Optional: `pos_sections` (list of `{pos, senses}`) for multiple POS per word.

---

## 3. Rules (parsing and output)

### 3.1 Language-only headwords

- **EN**: Headword must match “basic English”: letters, spaces, hyphen, apostrophe only; at least one letter. Reject symbols, digits-only, slashes, etc. Option: reject single-letter headwords (A, B) so the index is “words” not “letters”; design choice — can be a filter.
- **ZH**: Headword must be only CJK ideographs (and 〇). Reject romanizations, Latin script, mixed script.

### 3.2 Definitions: collapse glosses, no tags

- From each sense, collect all gloss strings (from `glosses`: string or `{gloss}`).
- Clean: remove wiki markup (e.g. `__NOTITLECONVERT__`), collapse newlines to space.
- Merge into one list; deduplicate by normalized string (strip, exact match), preserve order.
- **Do not** emit tags (e.g. “figuratively”, “broadly”) in the definition text.
- `short_definition` = first gloss, truncated (e.g. 100 chars). `full_definition` = numbered list of unique glosses only.

### 3.3 Index = single word (EN) or single character (ZH)

- **Head** = one token: EN = one word (no space in headword); ZH = one character (len(headword) == 1).
- **Phrase** = EN: space in headword; ZH: len(headword) > 1.
- **Output**: Only **heads** get a line in `entries.jsonl`. Each head line may have a `phrases` array.
- **leading_key**: EN = first word of headword (so for head “rain”, leading_key = “rain”); ZH = first character. Used for grouping; for heads, headword equals leading_key (for single word/char).
- Phrases are attached to the head that matches `(leading_key, part_of_speech)`: same leading_key and same POS as the phrase. If no matching head exists, the phrase can be dropped or attached to a head with same leading_key only (design choice: same POS preferred).

### 3.4 One record per (headword, POS); one pronunciation per record

- **Split by POS**: Different part of speech → different lines (e.g. *rain* noun, *rain* verb).
- **Do not split by pronunciation variant**: Many dumps have 10+ `sounds` (IPA for US/UK, or Pinyin/Bopomofo/Jyutping/… for ZH). We output **one** pronunciation per (headword, POS):
  - **EN**: Pick one IPA (e.g. first, or first with a preferred tag like “US” if present).
  - **ZH**: Pick one romanization (e.g. first Mandarin Pinyin, or first `zh_pron` that looks like Pinyin).
- **Exception — 多音字**: When the same character has **distinct readings that imply different meanings** (e.g. 行 xíng vs 行 háng), the source may expose them as different POS or different sense groups. We then emit **two** head entries (same headword, different POS or different “reading” key). We do **not** emit 20 lines for 中 with 20 romanization systems.

So: **one line per (headword, POS)**; pronunciation = single chosen value; phrases nested under the head.

### 3.5 Same headword, different POS or 多音字 → separate records

- Same headword + different POS → separate lines (already above).
- Same headword + same POS but genuinely different reading (多音字) → separate lines only when the source structures them that way (e.g. separate pos_sections or entries). We do not invent splits; we only collapse pronunciation variants into one per (head, POS).

---

## 4. Output schema (one line per head)

Each line in `entries.jsonl`:

| Field | Description |
|-------|-------------|
| `headword` | The head form (one word EN, one char ZH). |
| `sort_key` | For sorting (e.g. lowercase EN, headword for ZH). |
| `leading_key` | Index key: first word (EN) or first character (ZH). |
| `pronunciation` | **One** value: IPA (EN) or chosen romanization (ZH). |
| `short_definition` | First gloss, truncated. |
| `full_definition` | Numbered unique glosses, no tags. |
| `part_of_speech` | Normalized POS (noun, verb, adj, adv, …). |
| `phrases` | Optional list of `{form, definition}` for phrases under this head (same leading_key + POS). |

We do **not** write `is_phrase` on the line (every line is a head). We do not write duplicate lines that differ only by pronunciation.

---

## 5. Pipeline (high level)

1. **Read** Kaikki JSONL (stream or file); decode JSON per line.
2. **Filter** by language (lang_code) and headword rules (language-only).
3. **Classify** each object: head (single word/char) vs phrase (multi-word/char). Extract (leading_key, POS, pronunciation, glosses).
4. **Pronunciation**: For each (word, POS), choose **one** pronunciation (first IPA or first Pinyin, no row per variant).
5. **Definitions**: Build short_definition and full_definition from senses; dedupe glosses, no tags.
6. **Phrases**: Group phrase entries by (leading_key, POS); attach list of `{form, definition}` to the corresponding head.
7. **Emit** one line per (headword, POS) with one pronunciation and optional `phrases`; write only head lines.

---

## 6. Edge cases

- **No pronunciation**: Emit `pronunciation: null`.
- **Phrase with no matching head**: Skip phrase or attach to any head with same leading_key (e.g. first head with that key). Prefer same POS.
- **Single-letter EN (A, B)**: Include or exclude by config; design says “index = single words” so excluding single letters is reasonable.
- **Multiple POS in one line**: `pos_sections` or repeated lines → one output line per POS, each with one pronunciation and shared phrase list for (leading_key, POS).

---

## 7. Implementation location

- Parser and pack-building logic: **`py/`** (dedicated module), not `scripts/`.
- Entry point: e.g. `python -m py.kaikki_ingest --variant en --max-entries 3000 --out packs/kaikki-en-poc`.
- Design doc: **`docs/KAIKKI_PARSING_DESIGN.md`** (this file). No dependency on scripts/ for the core logic.
