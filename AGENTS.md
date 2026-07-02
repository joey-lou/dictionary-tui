## Cursor Cloud specific instructions

### Overview

`dictionary-tui` is a single-crate Rust TUI application for browsing local dictionary packs. No external services, databases, or Docker containers are needed. See `DEVELOPMENT.md` for standard quality-check commands (`cargo fmt`, `cargo clippy -- -D warnings`, `cargo test`).

### Rust toolchain

The VM ships with Rust 1.83 but the project requires **≥ 1.88** (due to `darling` and `instability` crate MSRVs). The update script runs `rustup update stable` to keep the toolchain current.

### Running the TUI

The app requires a real TTY — running `cargo run` from a non-interactive shell fails with "No such device or address (os error 6)". To test interactively, launch it inside a desktop terminal emulator (e.g. Xfce Terminal) or use `script -qc "cargo run" /dev/null` as a PTY wrapper.

### Dictionary packs

Three packs are committed under `packs/` (`webster1913-en`, `xinhua-zh-zh`, `cc-cedict`). The app auto-discovers them at startup — no ingest step is needed to run. Rebuild packs with the `py/ingest_*.py` scripts (see `DEVELOPMENT.md`).
