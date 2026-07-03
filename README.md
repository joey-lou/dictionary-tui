# dictionary-tui

A terminal UI for browsing local dictionary packs. Flip through paginated word lists, search by prefix, and expand entries for full definitions and phrases.

English ([Webster's 1913](https://www.gutenberg.org/ebooks/29765)), Chinese–Chinese ([Xinhua](https://github.com/pwxcoo/chinese-xinhua)), and Chinese–English ([CC-CEDICT](https://cc-cedict.org/)).

## Quick start

**Requirements:** Rust ≥ 1.88 (`rustup update stable`).

```bash
cargo install dictionary-tui
dictionary-tui pack install --all
dictionary-tui
```

Or from git:

```bash
cargo install --git https://github.com/joey-lou/dictionary-tui
dictionary-tui pack install --all
dictionary-tui
```

Or clone and run (includes packs under `packs/`, no download needed):

```bash
git clone https://github.com/joey-lou/dictionary-tui.git
cd dictionary-tui
cargo run --release
```

The app needs a real TTY (your terminal emulator, not a non-interactive shell).

## Dictionary packs

Installed packs live in:

| Platform | Path |
|----------|------|
| macOS | `~/Library/Application Support/dictionary-tui/packs/` |
| Linux | `~/.config/dictionary-tui/packs/` |

```bash
dictionary-tui pack list                    # available + installed
dictionary-tui pack install --all             # download from GitHub Releases
dictionary-tui pack install webster1913-en    # one pack
dictionary-tui pack install --from ./foo.tar.gz cc-cedict
dictionary-tui pack update
```

| Pack ID | Language | Download size |
|---------|----------|---------------|
| `webster1913-en` | English | ~6.5 MB |
| `xinhua-zh-zh` | Chinese (中中) | ~12 MB |
| `cc-cedict` | Chinese–English (中英) | ~3.4 MB |

Releases are tagged `packs-v*` on [GitHub Releases](https://github.com/joey-lou/dictionary-tui/releases). Checksums are in `packs/catalog.json`.

## Key bindings

| Key | Action |
|-----|--------|
| `j` / `k` or arrows | Move selection |
| `h` / `l` or Page Up/Down | Previous / next page |
| `Space` | Toggle collapsed / expanded view |
| `Enter` | Detail view |
| `Esc` / Backspace | Back to list |
| `/` or `s` | Prefix search (pinyin or Chinese) |
| `r` | Random page |
| `+` / `-` or `i` | Page-jump increment |
| `q` | Quit |

## Development

**Check:** `cargo fmt && cargo clippy -- -D warnings && cargo test` (CI runs the same on push/PR).

**Optional:** `pre-commit install` — hooks for fmt, clippy, tests, and `ruff check py/`.

**Rebuild packs:** `python3 py/ingest_webster1913.py` (and `ingest_xinhua.py`, `ingest_cedict.py`). Details in [py/README.md](py/README.md).

### Releases

Tag the **latest `main` commit** — CI routes by prefix (`release.yml`):

| Tag | Example | What ships |
|-----|---------|------------|
| `v*` | `v0.1.0` | crates.io publish + GitHub Release binaries (Linux/macOS) |
| `packs-v*` | `packs-v1.1.0` | GitHub Release pack tarballs + `packs/catalog.json` sync to `main` |

`v*` tag must match `version` in `Cargo.toml` (e.g. tag `v0.1.0` → `version = "0.1.0"`).

**One-time:** add repo secret `CARGO_REGISTRY_TOKEN` ([crates.io token](https://crates.io/settings/tokens)) for `v*` publishes.

```bash
# App + crates.io (bump Cargo.toml version first)
git tag v0.1.0 && git push origin v0.1.0

# Dictionary packs (after updating packs/)
git tag packs-v1.1.0 && git push origin packs-v1.1.0
```

## License

MIT — see [LICENSE](LICENSE).

Dictionary data carries its own licenses (see each pack's `manifest.json`):

| Pack | License |
|------|---------|
| Webster's 1913 | Public Domain |
| Xinhua | MIT (source data) |
| CC-CEDICT | CC BY-SA 4.0 |
