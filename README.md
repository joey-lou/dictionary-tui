# dictionary-tui

A terminal UI for browsing local dictionary packs. Flip through paginated word lists, search by prefix, and expand entries for full definitions and phrases.

Supports English (Webster's 1913), Chinese–Chinese (Xinhua), and Chinese–English (CC-CEDICT).

## Quick start

**Requirements:** Rust ≥ 1.88 (`rustup update stable`).

### From crates.io (recommended once published)

```bash
cargo install dictionary-tui
dictionary-tui pack install --all
dictionary-tui
```

### From source

```bash
git clone https://github.com/joey-lou/dictionary-tui.git
cd dictionary-tui
cargo run --release
```

Cloning includes packs under `packs/` (~86 MB) — no download step needed for development.

The app needs a real TTY (your terminal emulator, not a non-interactive shell).

## Dictionary packs

Packs are installed to your platform config directory:

| Platform | Path |
|----------|------|
| macOS | `~/Library/Application Support/dictionary-tui/packs/` |
| Linux | `~/.config/dictionary-tui/packs/` |

### Pack commands

```bash
dictionary-tui pack list                    # available packs + install status
dictionary-tui pack install --all           # download all packs from GitHub Releases
dictionary-tui pack install webster1913-en  # one pack
dictionary-tui pack install --from ./cc-cedict.tar.gz cc-cedict  # offline / local
dictionary-tui pack update                  # re-download all packs
```

| Pack ID | Language | Size (compressed) |
|---------|----------|-------------------|
| `webster1913-en` | English | ~6.5 MB |
| `xinhua-zh-zh` | Chinese (中中) | ~12 MB |
| `cc-cedict` | Chinese–English (中英) | ~3.4 MB |

Pack tarballs are hosted on [GitHub Releases](https://github.com/joey-lou/dictionary-tui/releases) (`packs-v*` tags). The catalog is `packs/catalog.json`.

**Private repository:** release downloads require authentication:

```bash
export GITHUB_TOKEN="$(gh auth token)"
dictionary-tui pack install --all
```

Make the repo public (or host packs elsewhere) for token-free installs.

### Rebuild from source data (ETL)

```bash
python3 py/ingest_webster1913.py
python3 py/ingest_xinhua.py
python3 py/ingest_cedict.py
```

See `py/README.md` and `DEVELOPMENT.md`.

## Key bindings

| Key | Action |
|-----|--------|
| `j` / `k` or arrows | Move selection |
| `h` / `l` or Page Up/Down | Previous / next page |
| `Space` | Toggle collapsed / expanded view |
| `Enter` | Open detail view |
| `Esc` / Backspace | Back to list |
| `/` or `s` | Prefix search (pinyin or Chinese characters) |
| `r` | Jump to random page |
| `+` / `-` or `i` | Adjust page-jump increment |
| `q` | Quit |

## Development

```bash
cargo fmt
cargo clippy -- -D warnings
cargo test
ruff check py/
```

See `DEVELOPMENT.md` for pre-commit hooks and CI.

### Publishing pack releases

```bash
./scripts/build-pack-release.sh packs-v1.0.0
git add packs/catalog.json
git commit -m "Update pack catalog for packs-v1.0.0"
git tag packs-v1.0.0
git push && git push --tags
```

GitHub Actions uploads `dist/*.tar.gz` to the release.

## License

MIT. Dictionary data carries its own licenses — see each pack's `manifest.json`.
