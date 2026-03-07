# Development setup

## Prerequisites

- **Rust** — Install via [rustup](https://rustup.rs/). Includes `cargo`, `rustfmt`, and `clippy` (install with `rustup component add clippy rustfmt` if missing).
- **Python 3.12+** — For running dictionary ingest scripts (stdlib only, no pip dependencies).
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

## Dictionary packs

The app discovers packs from both:

1. Config directory (`ProjectDirs(...)/packs`)
2. Repo-local `packs/` (bundled packs for development)

Three packs ship with the repo:

| Pack | Command | Description |
|------|---------|-------------|
| **Wordset EN** | `python3 scripts/ingest_wordset.py` | 77K English words (single-word only, POS, definitions) |
| **Xinhua ZH-ZH** | `python3 scripts/ingest_xinhua.py` | 17K Chinese characters with Chinese definitions + 295K phrases/idioms |
| **CC-CEDICT ZH-EN** | `python3 scripts/ingest_cedict.py` | 13K Chinese character heads + 102K compound phrases with English definitions |

All ingest scripts auto-download source data into `.cache/` on first run.
Use `--help` on any script for options (e.g. `--source-file`, `--out`).

### Adding a new dictionary source

See `scripts/ingest/README.md` for the pack format and how to add a new source.

## Optional: cargo-audit

```bash
cargo install cargo-audit
cargo audit
```
