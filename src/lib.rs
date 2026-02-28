//! Dictionary TUI — terminal UI for browsing dictionary packs.
//!
//! See [PLAN.md](../PLAN.md) for architecture and pack format.

use std::io;

/// Run the TUI event loop. Returns an exit code (0 = success).
pub fn run_app() -> u8 {
    let _ = io::stdout();
    // TODO: initialize terminal, run ratatui app, restore terminal
    0u8
}
