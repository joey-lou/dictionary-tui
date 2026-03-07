//! Dictionary TUI — terminal UI for browsing dictionary packs.
//!
//! See [PLAN.md](../PLAN.md) for architecture and pack format.

mod app;
pub mod config;
pub mod pack;
pub mod provider;
pub mod schema;

pub use pack::{discover_packs, load_manifest, packs_root, PackError};
pub use provider::{LocalProvider, Provider};
pub use schema::{DetailEntry, ListEntry, PackManifest, PhraseItem};

/// Run the TUI event loop. Returns an exit code (0 = success).
pub fn run_app() -> u8 {
    match app::run() {
        Ok(()) => 0,
        Err(err) => {
            eprintln!("dictionary-tui error: {err}");
            1
        }
    }
}
