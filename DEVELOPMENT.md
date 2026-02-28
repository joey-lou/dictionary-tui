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
