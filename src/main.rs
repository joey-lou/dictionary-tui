//! Binary entry point for the dictionary TUI.
//! Library logic lives in `lib.rs` and sibling modules.

use dictionary_tui::{run_app, run_from_args, CliResult};
use std::io::IsTerminal;
use std::process::ExitCode;

fn main() -> ExitCode {
    install_panic_hook();
    match run_from_args(std::env::args()) {
        CliResult::Exit(code) => ExitCode::from(code),
        CliResult::RunTui => ExitCode::from(run_app()),
    }
}

/// Restore terminal on panic so the panic message is visible and the shell is usable.
fn install_panic_hook() {
    let default_hook = std::panic::take_hook();
    std::panic::set_hook(Box::new(move |info| {
        if std::io::stderr().is_terminal() {
            let _ = crossterm::terminal::disable_raw_mode();
            let _ = crossterm::ExecutableCommand::execute(
                &mut std::io::stdout(),
                crossterm::terminal::LeaveAlternateScreen,
            );
        }
        default_hook(info);
    }));
}
