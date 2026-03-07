//! Pack discovery and manifest loading for dictionary packs.

use crate::schema::PackManifest;
use std::collections::HashSet;
use std::path::{Path, PathBuf};
use std::{fmt, io};

/// Returns the absolute path to the bundled `packs` directory when the binary
/// is run from `target/debug` or `target/release`, so packs are found regardless of cwd.
fn bundled_packs_root() -> PathBuf {
    let exe = match std::env::current_exe() {
        Ok(p) => p,
        Err(_) => return PathBuf::from("packs"),
    };
    // exe is e.g. .../target/debug/dictionary-tui or .../target/release/dictionary-tui
    let exe_dir = match exe.parent() {
        Some(d) => d.to_path_buf(),
        None => return PathBuf::from("packs"),
    };
    let project_root = exe_dir.parent().map(|p| p.join("packs"));
    match project_root {
        Some(p) if p.exists() => p,
        _ => PathBuf::from("packs"),
    }
}

/// Errors that can occur when loading or discovering packs.
#[derive(Debug)]
pub enum PackError {
    Io(io::Error),
    Json(serde_json::Error),
}

impl fmt::Display for PackError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Io(e) => write!(f, "IO error: {e}"),
            Self::Json(e) => write!(f, "invalid manifest JSON: {e}"),
        }
    }
}

impl std::error::Error for PackError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::Io(e) => Some(e),
            Self::Json(e) => Some(e),
        }
    }
}

impl From<io::Error> for PackError {
    fn from(e: io::Error) -> Self {
        Self::Io(e)
    }
}

impl From<serde_json::Error> for PackError {
    fn from(e: serde_json::Error) -> Self {
        Self::Json(e)
    }
}

/// Returns the root directory where dictionary packs are stored, or `None` if
/// the project config directory cannot be determined.
pub fn packs_root() -> Option<PathBuf> {
    directories::ProjectDirs::from("", "", "dictionary-tui").map(|p| p.config_dir().join("packs"))
}

/// Loads and parses the manifest from a pack directory.
///
/// Reads `pack_root/manifest.json` and returns a descriptive error on IO or
/// JSON parse failure.
pub fn load_manifest(pack_root: &Path) -> Result<PackManifest, PackError> {
    let path = pack_root.join("manifest.json");
    let contents = std::fs::read_to_string(&path).map_err(PackError::Io)?;
    serde_json::from_str(&contents).map_err(PackError::Json)
}

/// Discovers all packs under the packs root.
///
/// Returns `Ok(vec![])` if no packs root is available. Iterates directory
/// entries, loads manifests for each subdirectory that has `manifest.json`,
/// and collects `(path, manifest)`. Skips non-directories and entries whose
/// manifest is missing or invalid (logged to stderr); does not fail the
/// entire discovery.
pub fn discover_packs() -> Result<Vec<(PathBuf, PackManifest)>, PackError> {
    let mut packs = Vec::new();
    let mut seen_ids = HashSet::new();

    if let Some(root) = packs_root() {
        for (path, manifest) in discover_packs_under(&root)? {
            if seen_ids.insert(manifest.id.clone()) {
                packs.push((path, manifest));
            }
        }
    }
    let bundled_root = bundled_packs_root();
    for (path, manifest) in discover_packs_under(&bundled_root)? {
        if seen_ids.insert(manifest.id.clone()) {
            packs.push((path, manifest));
        }
    }

    Ok(packs)
}

fn discover_packs_under(root: &Path) -> Result<Vec<(PathBuf, PackManifest)>, PackError> {
    let entries = match std::fs::read_dir(root) {
        Ok(e) => e,
        Err(e) => {
            if e.kind() == io::ErrorKind::NotFound {
                return Ok(vec![]);
            }
            return Err(PackError::Io(e));
        }
    };

    let mut packs = Vec::new();
    for entry in entries {
        let entry = match entry {
            Ok(e) => e,
            Err(e) => {
                eprintln!("pack discovery: skip entry: {e}");
                continue;
            }
        };
        let path = entry.path();
        if !path.is_dir() {
            continue;
        }
        let manifest_path = path.join("manifest.json");
        if !manifest_path.exists() {
            continue;
        }
        match load_manifest(&path) {
            Ok(manifest) => packs.push((path, manifest)),
            Err(e) => {
                eprintln!("pack discovery: skip {}: {e}", path.display());
            }
        }
    }
    Ok(packs)
}
