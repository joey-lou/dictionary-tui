# Development setup

Basic quality tooling for the Rust project (similar to pre-commit + ruff in Python).

## Prerequisites

- **Rust** — Install via [rustup](https://rustup.rs/). Includes `cargo`, `rustfmt`, and `clippy` (install with `rustup component add clippy rustfmt` if missing).
- **pre-commit** (optional) — `pip install pre-commit` or `brew install pre-commit`.

## Quick check

```bash
cargo fmt
cargo clippy -- -D warnings
cargo test
```

## Pre-commit (recommended)

Install hooks so format, clippy, and tests run on every commit:

```bash
pre-commit install
```

Then each `git commit` will run:

1. **cargo fmt** — Reformats code.
2. **cargo clippy -- -D warnings** — Fails if Clippy reports any warning.
3. **cargo test** — Runs tests.

Run manually on all files:

```bash
pre-commit run --all-files
```

## CI

On push/PR to `main`, GitHub Actions runs:

- `cargo fmt -- --check` (format check)
- `cargo clippy -- -D warnings`
- `cargo test`

Fix format and clippy locally before pushing.

## Config files

| File | Purpose |
|------|--------|
| `rustfmt.toml` | Line width (100), edition. |
| `Cargo.toml` → `[lints.rust]` | Forbid `unsafe_code`. |
| `Cargo.toml` → `[lints.clippy]` | Pedantic/nursery lints (warn by default). |
| `.pre-commit-config.yaml` | Local hooks. |
| `.github/workflows/ci.yml` | CI pipeline. |

## Optional: cargo-audit

For dependency security audits:

```bash
cargo install cargo-audit
cargo audit
```

You can add a CI job or pre-commit hook for this later.

## Python ingest scripts

Ingest (download + transform dictionary source data into local packs) lives under
`scripts/` and is intentionally separate from the Rust runtime.

Build a bundled English pack (Webster 1913 parser):

```bash
python3 scripts/ingest_webster1913.py --max-entries 3000
```

Build the full WordNet English pack (optionally with CMU Pronouncing Dictionary for pronunciation):

```bash
python3 scripts/ingest_wordnet.py
```

By default the script downloads the CMU Pronouncing Dictionary and attaches ARPAbet pronunciation to matching headwords. Use `--no-pronunciation` to skip. If the CMU URL fails, use `--cmudict-file /path/to/cmudict-0.7b` after downloading from [CMUdict](https://github.com/cmusphinx/cmudict) or a mirror. WordNet short definitions are first clause (up to 100 chars); full definition is the full gloss including examples.

Optional: limit entries for a quick test, e.g. `--max-entries 500`.

**Richer English source (Wiktionary):** For IPA pronunciation and more detailed definitions, build from the Kaikki/Wiktextract English extract:

1. Optional: run `python3 scripts/inspect_kaikki_raw.py 100` to fetch the first 100 lines and write `tmp/kaikki_en_first_100_raw.jsonl` plus a structure summary. See `docs/KAIKKI_STRUCTURE.md` for the JSONL schema (senses, glosses, tags, etc.).
2. Without a local file, the script streams from Kaikki: `python3 scripts/ingest_kaikki_en.py` (default 3000 entries). Or pass a local dump: `python3 scripts/ingest_kaikki_en.py --source-file /path/to/en-extract.jsonl.gz`.

Output: `packs/kaikki-en/` with IPA in `pronunciation`, numbered senses and optional qualifier tags (e.g. “(figuratively)”) in `full_definition`, and first gloss truncated to 100 chars in `short_definition`.

**Kaikki POC (en, Chinese→English, Chinese→Chinese):** One script builds small POC packs for all three:

```bash
python3 scripts/ingest_kaikki_poc.py en --max-entries 2500      # packs/kaikki-en-poc
python3 scripts/ingest_kaikki_poc.py zh-en --max-entries 2500   # packs/kaikki-zh-en-poc (Chinese headwords, EN definitions)
python3 scripts/ingest_kaikki_poc.py zh-zh --max-entries 2500   # packs/kaikki-zh-zh-poc (zhwiktionary; Chinese definitions)
```

Use `--source-file PATH` to read from a local JSONL or `.jsonl.gz` instead of streaming from Kaikki.

Output (WordNet/Webster):

- `packs/webster-1913/manifest.json`
- `packs/webster-1913/entries.jsonl`
- `packs/wordnet/manifest.json`
- `packs/wordnet/entries.jsonl`

Build a Chinese pack (CC-CEDICT; pinyin index, search by pinyin; English definitions):

```bash
python3 scripts/ingest_cedict.py
```

Optional: `--max-entries 5000`, `--traditional` for traditional headwords. Use `--source-file /path/to/cedict_*.txt.gz` if the default download URL returns HTML. The ingest produces: accented pinyin (e.g. nǐ hǎo), short vs full definitions (short = first gloss, truncated to 100 chars), and inferred part-of-speech/usage (v., cl., abbr., slang, etc.) from definition text. Output: `packs/cc-cedict/`. For Chinese-in-Chinese definitions, a Wiktionary zh–based ingest can be added later.

The app discovers packs from both:

1. Config directory (`ProjectDirs(...)/packs`)
2. Repo-local `packs/` (useful for default bundled packs and development)
