//! Version string for `--version`.
//!
//! Dev builds (`0.0.0-dev`) append `git describe`. Release builds print only
//! the crate version. CI rewrites `Cargo.toml` before compiling a release,
//! which dirties the worktree, so that describe must not appear on the
//! published binary. crates.io installs have no git history.

use std::process::Command;

fn main() {
    println!("cargo:rerun-if-changed=.git/HEAD");
    println!("cargo:rerun-if-changed=.git/refs");
    println!("cargo:rerun-if-env-changed=CARGO_PKG_VERSION");

    let version = std::env::var("CARGO_PKG_VERSION").unwrap_or_else(|_| "0.0.0-dev".to_string());
    let display = if version == "0.0.0-dev" {
        format!("{version} ({})", git_describe())
    } else {
        version
    };
    println!("cargo:rustc-env=BUILD_VERSION={display}");
}

fn git_describe() -> String {
    Command::new("git")
        .args(["describe", "--tags", "--always", "--dirty"])
        .output()
        .ok()
        .filter(|output| output.status.success())
        .and_then(|output| String::from_utf8(output.stdout).ok())
        .map_or_else(
            || "unknown".to_string(),
            |describe| describe.trim().to_string(),
        )
}
