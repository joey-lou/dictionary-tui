//! CLI entry points (`pack install`, `pack uninstall`, `pack list`, etc.).

use crate::pack_install::{
    install_packs, is_pack_installed, load_catalog, uninstall_packs, update_packs,
};
use clap::{Parser, Subcommand};
use std::path::{Path, PathBuf};

/// Terminal UI for browsing local dictionary packs.
#[derive(Parser)]
#[command(
    name = "dictionary-tui",
    version,
    about,
    arg_required_else_help = false
)]
pub struct Cli {
    #[command(subcommand)]
    pub command: Option<Command>,
}

#[derive(Subcommand)]
pub enum Command {
    /// Download and install dictionary packs.
    Pack {
        #[command(subcommand)]
        command: PackCommand,
    },
}

#[derive(Subcommand)]
pub enum PackCommand {
    /// List available packs and installation status.
    List,
    /// Download and install one or more packs.
    Install {
        /// Pack ids to install (e.g. webster1913-en cc-cedict).
        #[arg(value_name = "PACK_ID")]
        packs: Vec<String>,

        /// Install every pack in the catalog.
        #[arg(long)]
        all: bool,

        /// Install from a local `.tar.gz` instead of downloading (requires one `PACK_ID`).
        #[arg(long, value_name = "ARCHIVE")]
        from: Option<PathBuf>,
    },
    /// Re-download and install all catalog packs.
    Update,
    /// Remove installed packs from the config directory.
    Uninstall {
        /// Pack ids to remove (e.g. webster1913-en cc-cedict).
        #[arg(value_name = "PACK_ID")]
        packs: Vec<String>,

        /// Remove every installed catalog pack.
        #[arg(long)]
        all: bool,
    },
}

/// Result of parsing CLI arguments.
pub enum CliResult {
    /// Exit with the given code (CLI command ran).
    Exit(u8),
    /// Launch the interactive TUI.
    RunTui,
}

/// Parse `args` and run a subcommand, or indicate the TUI should start.
pub fn run_from_args<I, T>(args: I) -> CliResult
where
    I: IntoIterator<Item = T>,
    T: Into<std::ffi::OsString> + Clone,
{
    let cli = match Cli::try_parse_from(args) {
        Ok(c) => c,
        Err(e) if e.kind() == clap::error::ErrorKind::DisplayHelp => {
            e.print().ok();
            return CliResult::Exit(0);
        }
        Err(e) if e.kind() == clap::error::ErrorKind::DisplayVersion => {
            e.print().ok();
            return CliResult::Exit(0);
        }
        Err(e) => {
            e.print().ok();
            return CliResult::Exit(2);
        }
    };

    let Some(Command::Pack { command }) = cli.command else {
        return CliResult::RunTui;
    };

    let code = match command {
        PackCommand::List => run_pack_list(),
        PackCommand::Install { packs, all, from } => run_pack_install(&packs, all, from.as_deref()),
        PackCommand::Update => run_pack_update(),
        PackCommand::Uninstall { packs, all } => run_pack_uninstall(&packs, all),
    };
    CliResult::Exit(code)
}

fn run_pack_list() -> u8 {
    match load_catalog() {
        Ok(catalog) => {
            println!(
                "Catalog {} ({}) — install with: dictionary-tui pack install --all\n",
                catalog.release_tag, catalog.repository
            );
            for pack in &catalog.packs {
                let status = if is_pack_installed(&pack.id) {
                    "installed"
                } else {
                    "not installed"
                };
                let size_mb = pack.size / (1024 * 1024);
                let size_frac = (pack.size % (1024 * 1024)) * 10 / (1024 * 1024);
                println!(
                    "  {:<18} {:<28} {:>3}.{:<1} MB  {}",
                    pack.id, pack.name, size_mb, size_frac, status
                );
            }
            0
        }
        Err(e) => {
            eprintln!("dictionary-tui pack list error: {e}");
            1
        }
    }
}

fn run_pack_install(packs: &[String], all: bool, from: Option<&Path>) -> u8 {
    match install_packs(packs, all, from) {
        Ok(()) => 0,
        Err(e) => {
            eprintln!("dictionary-tui pack install error: {e}");
            1
        }
    }
}

fn run_pack_update() -> u8 {
    match update_packs() {
        Ok(()) => 0,
        Err(e) => {
            eprintln!("dictionary-tui pack update error: {e}");
            1
        }
    }
}

fn run_pack_uninstall(packs: &[String], all: bool) -> u8 {
    match uninstall_packs(packs, all) {
        Ok(()) => 0,
        Err(e) => {
            eprintln!("dictionary-tui pack uninstall error: {e}");
            1
        }
    }
}
