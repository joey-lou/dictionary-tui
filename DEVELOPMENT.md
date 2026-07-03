# Development setup

## Prerequisites

- **Rust** — Install via [rustup](https://rustup.rs/). Includes `cargo`, `rustfmt`, and `clippy` (install with `rustup component add clippy rustfmt` if missing).
- **Python 3.12+** — For running dictionary ingest scripts (stdlib only, no pip dependencies).
- **pre-commit** (optional) — `pip install pre-commit` or `brew install pre-commit`.

## Quick check

```bash
# Rust
cargo fmt
cargo clippy -- -D warnings
cargo test

# Python (requires: pip install ruff)
ruff check py/
ruff format --check py/
```

## Pre-commit (recommended)

Install hooks so format, lint, and tests run on every commit:

```bash
pre-commit install
```

Then each `git commit` will run:

1. **cargo fmt** — Reformats Rust code.
2. **cargo clippy -- -D warnings** — Fails if Clippy reports any warning.
3. **cargo test** — Runs Rust tests.
4. **ruff** — Lints Python code under `py/` (with auto-fix).
5. **ruff-format** — Formats Python code under `py/`.

Run manually on all files:

```bash
pre-commit run --all-files
```

## CI

On push/PR to `main`, GitHub Actions runs:

- `cargo fmt -- --check` (Rust format check)
- `cargo clippy -- -D warnings` (Rust lint)
- `cargo test` (Rust tests)
- `ruff check py/` (Python lint)
- `ruff format --check py/` (Python format check)

Fix format and lint issues locally before pushing.

## Config files

| File | Purpose |
|------|--------|
| `rustfmt.toml` | Rust line width (100), edition. |
| `Cargo.toml` → `[lints.rust]` | Forbid `unsafe_code`. |
| `Cargo.toml` → `[lints.clippy]` | Pedantic/nursery lints (warn by default). |
| `pyproject.toml` | Ruff lint/format config for Python. |
| `.pre-commit-config.yaml` | Pre-commit hooks (Rust + Python). |
| `.github/workflows/ci.yml` | CI pipeline. |

## Dictionary packs

The app discovers packs from:

1. **Config directory** — `ProjectDirs(...)/packs` (where `pack install` writes)
2. **Repo-local `packs/`** — bundled for `cargo run` from a clone

### Installing packs (end users)

```bash
dictionary-tui pack list
dictionary-tui pack install --all
```

Downloads from GitHub Releases (`packs/catalog.json`). For **private** repositories, set a GitHub token:

```bash
export GITHUB_TOKEN="$(gh auth token)"   # or GH_TOKEN
dictionary-tui pack install --all
```

Public repos do not need a token. See `README.md`.

### Bundled packs (development)

Three packs ship in the repo:

| Pack | Command | Description |
|------|---------|-------------|
| **Webster's 1913** | `python3 py/ingest_webster1913.py` | 109K English words with POS, pronunciation, and definitions |
| **Xinhua ZH-ZH** | `python3 py/ingest_xinhua.py` | 17K Chinese characters with pinyin, Chinese definitions + phrases/idioms |
| **CC-CEDICT ZH-EN** | `python3 py/ingest_cedict.py` | 13K Chinese character heads with pinyin, POS, English definitions |

All ingest scripts auto-download source data into `.cache/` on first run.
Use `--help` on any script for options (e.g. `--source-file`, `--out`).

### Publishing pack releases

```bash
./scripts/build-pack-release.sh packs-v1.0.0   # dist/*.tar.gz + packs/catalog.json
git add packs/catalog.json && git commit -m "Update pack catalog for packs-v1.0.0"
git tag packs-v1.0.0 && git push && git push --tags
```

The `pack-release` workflow uploads tarballs to the GitHub Release.

### Adding a new dictionary source

See `py/README.md` for the pack format and how to add a new source.

## Optional: cargo-audit

```bash
cargo install cargo-audit
cargo audit
```
