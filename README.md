# dictionary-tui

A terminal UI for browsing local dictionary packs. Flip through paginated word lists, search by prefix, and expand entries for full definitions and phrases.

Supports English (Webster's 1913), Chinese–Chinese (Xinhua), and Chinese–English (CC-CEDICT).

## Quick start

**Requirements:** Rust ≥ 1.88 (see `rust-toolchain.toml` if present, or `rustup update stable`).

```bash
cargo run
```

The app needs a real TTY. Run it in your terminal emulator, not a non-interactive shell.

On first launch, pick a dictionary pack. Three packs ship under `packs/` — no ingest step required.

## Key bindings

| Key | Action |
|-----|--------|
| `j` / `k` or arrows | Move selection |
| `h` / `l` or Page Up/Down | Previous / next page |
| `Space` | Toggle collapsed / expanded view |
| `Enter` | Open detail view |
| `Esc` / Backspace | Back to list |
| `/` or `s` | Prefix search |
| `r` | Jump to random page |
| `+` / `-` or `i` | Adjust page-jump increment |
| `q` | Quit |

## Dictionary packs

| Pack | Language | Entries |
|------|----------|---------|
| `webster1913-en` | English | ~109K |
| `xinhua-zh-zh` | Chinese (中中) | ~17K |
| `cc-cedict` | Chinese–English (中英) | ~13K |

Rebuild a pack from source:

```bash
python3 py/ingest_webster1913.py
python3 py/ingest_xinhua.py
python3 py/ingest_cedict.py
```

See `py/README.md` and `DEVELOPMENT.md` for details.

## Development

```bash
cargo fmt
cargo clippy -- -D warnings
cargo test
ruff check py/
ruff format --check py/
```

See `DEVELOPMENT.md` for pre-commit hooks and CI.

## License

MIT. Dictionary data carries its own licenses — see each pack's `manifest.json`.
