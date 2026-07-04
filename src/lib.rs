//! Dictionary TUI — terminal UI for browsing dictionary packs.

mod app;
pub mod cli;
pub mod config;
pub mod pack;
pub mod pack_install;
pub mod provider;
pub mod schema;

pub use cli::{run_from_args, CliResult};
pub use pack::{discover_packs, load_manifest, packs_root, PackError};
pub use pack_install::{
    install_packs, is_pack_installed, load_catalog, uninstall_packs, PackCatalog, PackRelease,
};
pub use provider::{format_pronunciation_display, LocalProvider, Provider};
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
