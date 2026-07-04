# dictionary-tui

[![Crates.io](https://img.shields.io/crates/v/dictionary-tui?logo=rust)](https://crates.io/crates/dictionary-tui)
[![CI](https://img.shields.io/github/actions/workflow/status/joey-lou/dictionary-tui/ci.yml?branch=main&label=CI)](https://github.com/joey-lou/dictionary-tui/actions/workflows/ci.yml)
[![GitHub release](https://img.shields.io/github/v/release/joey-lou/dictionary-tui)](https://github.com/joey-lou/dictionary-tui/releases)
[![License: MIT](https://img.shields.io/crates/l/dictionary-tui)](LICENSE)
[![Rust](https://img.shields.io/badge/rust-1.88+-orange?logo=rust)](https://www.rust-lang.org/)

Terminal dictionary browser — paginated word lists, prefix search, and expandable entries.  
English ([Webster's 1913](https://www.gutenberg.org/ebooks/29765)), Chinese–Chinese ([Xinhua](https://github.com/pwxcoo/chinese-xinhua)), Chinese–English ([CC-CEDICT](https://cc-cedict.org/)).

<p align="center">
  <img src="assets/demo.gif" alt="dictionary-tui demo — CC-CEDICT Chinese–English pinyin search and detail view" width="860">
</p>

## Install & run

**Requires:** Rust ≥ 1.88 and a real terminal (TTY).

```bash
cargo install dictionary-tui
dictionary-tui pack install --all   # ~22 MB of dictionary data
dictionary-tui
```

<details>
<summary>Other install options</summary>

**From git**

```bash
cargo install --git https://github.com/joey-lou/dictionary-tui
dictionary-tui pack install --all
```

**Clone & run** (bundled `packs/` in repo — no download)

```bash
git clone https://github.com/joey-lou/dictionary-tui.git && cd dictionary-tui
cargo run --release
```

**Pre-built binaries** — [GitHub Releases](https://github.com/joey-lou/dictionary-tui/releases) (`v*` tags, Linux x86_64 + macOS arm64)

</details>

## Features

- **Three dictionaries** — English, 中中, 中英; install all or pick one
- **Fast prefix search** — English headwords; pinyin or Chinese characters for ZH packs
- **Page-flip browsing** — jump by page, random page, collapse/expand entries
- **Offline** — packs stored locally after install; no network needed to look up words

## Dictionary packs

| Pack ID | Language | Size |
|---------|----------|------|
| `webster1913-en` | English | ~6.5 MB |
| `xinhua-zh-zh` | Chinese (中中) | ~12 MB |
| `cc-cedict` | Chinese–English (中英) | ~3.4 MB |

```bash
dictionary-tui pack list
dictionary-tui pack install --all
dictionary-tui pack install webster1913-en cc-cedict
dictionary-tui pack update
dictionary-tui pack uninstall cc-cedict
dictionary-tui pack uninstall --all
```

Installed to `~/Library/Application Support/dictionary-tui/packs/` (macOS) or `~/.config/dictionary-tui/packs/` (Linux).

Pack releases are tagged `packs-v*` on [GitHub Releases](https://github.com/joey-lou/dictionary-tui/releases); checksums in [`packs/catalog.json`](packs/catalog.json).

## Key bindings

| Key | Action |
|-----|--------|
| `j` / `k`, arrows | Move selection |
| `h` / `l`, Page Up/Down | Previous / next page |
| `Space` | Collapse / expand entry |
| `Enter` | Detail view |
| `Esc`, Backspace | Back to list |
| `/`, `s` | Prefix search |
| `r` | Random page |
| `+` / `-`, `i` | Page-jump increment |
| `q` | Quit |

## Development

```bash
cargo fmt && cargo clippy -- -D warnings && cargo test
```

Optional: `pre-commit install` (fmt, clippy, tests, `ruff check py/`).

**Demo GIF:** `brew install vhs && ./scripts/record-demo.sh` (from Terminal.app; edit `scripts/demo.tape`).

**Rebuild pack data** — `python3 py/ingest_webster1913.py` (also `ingest_xinhua.py`, `ingest_cedict.py`). See [py/README.md](py/README.md).

<details>
<summary>Releasing (maintainers)</summary>

Tag the **latest `main` commit** — [`.github/workflows/release.yml`](.github/workflows/release.yml) routes by prefix. The release workflow re-runs CI (fmt, clippy, tests) before shipping.

| Tag | Ships |
|-----|-------|
| `v0.1.0` | crates.io + GitHub binaries (Linux/macOS) |
| `packs-v1.0.0` | Pack tarballs + `catalog.json` sync to `main` |

**Pre-flight**

1. Merge to `main` and ensure CI is green (`release-app.sh` also runs fmt, clippy, and tests locally).
2. Pack release: re-run ingest scripts if pack data changed (`py/ingest_*.py`).
3. Optional dry-run: `./scripts/release-app.sh patch --dry-run` or `./scripts/build-pack-release.sh packs-vX.Y.Z`.

**App release** — from a clean `main` synced with `origin/main`:

```bash
./scripts/release-app.sh patch          # 0.1.1 → 0.1.2
./scripts/release-app.sh minor          # 0.1.1 → 0.2.0
./scripts/release-app.sh 0.2.0          # explicit version
./scripts/release-app.sh patch --dry-run
```

The script runs fmt/clippy/tests, bumps `Cargo.toml`, commits, tags `v*`, and pushes. It rolls back local commit/tag changes if a step fails before push completes. Tag and `Cargo.toml` always match on the release commit — no bot follow-up commit.

**Pack release** — tag pack content on `main` (no `Cargo.toml` change):

```bash
git tag packs-v1.1.0 && git push origin packs-v1.1.0
```

Set repo secret `CARGO_REGISTRY_TOKEN` for automated crates.io publish. crates.io publish runs only after binaries are built and the GitHub Release is created.

**Pack catalog note:** a `packs-v*` tag points at the pack *content* on `main`. The workflow then pushes a follow-up commit updating `packs/catalog.json` (checksums and URLs). Clients fetch the live catalog from `main`; the tag itself does not include that commit.

</details>

## License

MIT — see [LICENSE](LICENSE).

Dictionary data has separate licenses (see each pack's `manifest.json`):

| Pack | License |
|------|---------|
| Webster's 1913 | Public Domain |
| Xinhua | MIT (source data) |
| CC-CEDICT | CC BY-SA 4.0 |
