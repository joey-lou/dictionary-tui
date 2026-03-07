# Kaikki / Wiktextract JSONL structure

Based on the first 100 lines of `kaikki.org-dictionary-English.jsonl` (postprocessed English, one line per word+POS).

**Before/after examples:** See [KAIKKI_BEFORE_AFTER.md](KAIKKI_BEFORE_AFTER.md) for raw JSON → parsed pack entries (English and Chinese).

## Line = one (word, part-of-speech) block

Each JSONL line is one **word** and one **part of speech**, with multiple **senses**. Not one sense per line; the “postprocessed” English file is still one word+POS per line with a `senses` array.

## Top-level keys

| Key | Type | Use |
|-----|------|-----|
| `word` | string | Headword (we use for headword + sort_key). |
| `pos` | string | Part of speech: "noun", "verb", "adj", "adv", "symbol", etc. |
| `lang`, `lang_code` | string | e.g. "English", "en" — filter by lang_code for language. |
| `senses` | list[dict] | **Main content.** Each sense has glosses, optional tags, examples. |
| `sounds` | list[dict] | IPA etc.; we take first `sounds[].ipa`. |
| `forms` | list[dict] | Inflections: `{"form": "dictionaries", "tags": ["plural"]}`. |
| `head_templates` | list[dict] | e.g. `expansion`: "dictionary (plural dictionaries)". |
| `etymology_text` | string | Long etymology paragraph. |
| `etymology_templates` | list | Structured etymology. |
| `etymology_number` | int | Disambiguates multiple etymologies. |
| `antonyms`, `synonyms`, `related` | list[dict] | `{"word": "..."}`. |
| `translations` | list[dict] | Per-language translations. |
| `categories`, `wikipedia`, `hypernyms`, `hyponyms`, etc. | various | Extra metadata. |

## Sense object (each item in `senses`)

| Key | Type | Use |
|-----|------|-----|
| `glosses` | list[string] | **Primary.** One or more definition strings (we use the first or join). |
| `raw_glosses` | list[string] | Unprocessed glosses when different from `glosses`. |
| `tags` | list[string] | Qualifiers: "figuratively", "broadly", "derogatory", etc. |
| `qualifier` | string | Single qualifier when not a list. |
| `examples` | list[dict] | `{"text": "If you want to know...", "type": "example"}` or quotation with `ref`. |
| `links` | list[list] | Pairs of linked terms. |
| `categories`, `hypernyms`, `coordinate_terms`, etc. | various | Extra. |

## How we map to our schema

- **short_definition**: First sense’s first gloss, truncated to ~100 chars (list view).
- **full_definition**: All senses combined — we use numbered list and optional tags so it’s structured but still one string:
  - `1. First gloss. 2. (figuratively) Second gloss.`
- **pronunciation**: First IPA from top-level `sounds`.
- **part_of_speech**: Normalized `pos` (noun, verb, adj, adv where possible).

We do **not** currently put etymology, forms, examples, or synonyms into the pack (single string, keep simple). They could be added later as optional sections or fields.

## Other languages (e.g. Chinese / ZH)

**Two different “Chinese” sources:**

| Source | Headwords | Definitions | Use case |
|--------|-----------|--------------|----------|
| **Kaikki “Chinese”** (e.g. `kaikki.org/dictionary/Chinese/...jsonl`) | Chinese (and borrowings) | **English** | Chinese → English (from **enwiktionary**) |
| **Kaikki zh-extract** (`kaikki.org/dictionary/downloads/zh/zh-extract.jsonl.gz`) | Chinese | **Chinese** | Chinese → Chinese (from **zhwiktionary**, the Chinese-language Wiktionary) |

So **Chinese → Chinese** exists: use the **zh-extract** raw dump (from zhwiktionary). It’s a separate file from the “Chinese” dictionary on the main Kaikki site; an ingest would need to download and parse `zh-extract.jsonl.gz` and map its glosses (in Chinese) into our schema.

**Same structure as English.** The first 100 lines of `kaikki.org-dictionary-Chinese.jsonl` use the same top-level and sense-level schema:

- **Top-level:** `word`, `pos`, `lang_code` ("zh"), `senses`, `sounds`, `forms`, `head_templates`, `etymology_text`, `antonyms`, `synonyms`, `related`, etc. **ZH-only:** `redirects` (list of alternative headwords, e.g. traditional form).
- **Sense-level:** `glosses`, `raw_glosses`, `tags`, `qualifier`, `examples`, `links`, `topics`, etc. Same as EN; ZH may also have `form_of`, `alt_of` in senses.
- **Pronunciation:** EN uses `sounds[].ipa`. ZH uses `sounds[].zh_pron` (Pinyin, Jyutping, Bopomofo, etc., with `tags` like "Mandarin", "Cantonese") and sometimes `sounds[].ipa` (e.g. Sinological-IPA). For a ZH pack, pick `zh_pron` (e.g. Mandarin Pinyin) when present, else `ipa`.

So we can reuse the same parser with `lang_code="zh"`; the only adaptation is how we read pronunciation (prefer `zh_pron` for ZH). Run `python3 scripts/inspect_kaikki_raw.py 100 zh` to fetch and inspect the ZH dump; output is in `tmp/kaikki_zh_first_100_raw.jsonl` and `tmp/kaikki_zh_structure_summary.txt`.
