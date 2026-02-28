//! Binary entry point for the dictionary TUI.
//! Library logic lives in `lib.rs` and sibling modules.

use dictionary_tui::run_app;
use std::process::ExitCode;

fn main() -> ExitCode {
    ExitCode::from(run_app())
}
