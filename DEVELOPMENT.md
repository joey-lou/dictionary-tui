# Development setup

## Prerequisites

- **Rust ≥ 1.88** — [rustup](https://rustup.rs/)
- **Python 3.12+** — ingest scripts (stdlib only)
- **pre-commit** (optional) — `pip install pre-commit` or `brew install pre-commit`

## Quick check

```bash
cargo fmt
cargo clippy -- -D warnings
cargo test
ruff check py/          # pip install ruff / brew install ruff
```

## Pre-commit

```bash
pre-commit install
pre-commit run --all-files
```

Hooks run `cargo fmt`, `cargo clippy`, `cargo test`, and ruff on `py/`.

## CI

GitHub Actions on push/PR to `main`: Rust fmt, clippy, tests; Python ruff.

## Dictionary packs

**Discovery:** config dir (`~/.config/dictionary-tui/packs/` or macOS Application Support) first, then repo `packs/` for dev builds.

**End users:** `dictionary-tui pack install --all` — see [README.md](README.md).

**Rebuild from source:**

```bash
python3 py/ingest_webster1913.py
python3 py/ingest_xinhua.py
python3 py/ingest_cedict.py
```

**Publish a pack release:**

```bash
./scripts/build-pack-release.sh packs-v1.0.0
git add packs/catalog.json && git commit -m "Update pack catalog for packs-v1.0.0"
git tag packs-v1.0.0 && git push && git push --tags
```

The `pack-release` workflow uploads `dist/*.tar.gz` to GitHub Releases and syncs the catalog to `main`.

## Adding a dictionary source

See [py/README.md](py/README.md).
