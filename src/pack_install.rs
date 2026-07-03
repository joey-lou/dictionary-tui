//! Download, verify, and install dictionary packs from release tarballs.

use crate::pack::{load_manifest, packs_root};
use flate2::read::GzDecoder;
use serde::Deserialize;
use sha2::{Digest, Sha256};
use std::fs::{self, File};
use std::io::{self, Read};
use std::path::{Path, PathBuf};
use tar::Archive;

const EMBEDDED_CATALOG: &str = include_str!("../packs/catalog.json");
const CATALOG_URL: &str =
    "https://raw.githubusercontent.com/joey-lou/dictionary-tui/main/packs/catalog.json";

/// Release metadata for downloadable packs (`packs/catalog.json`).
#[derive(Debug, Clone, Deserialize)]
pub struct PackCatalog {
    pub release_tag: String,
    pub repository: String,
    pub packs: Vec<PackRelease>,
}

/// One pack entry in the release catalog.
#[derive(Debug, Clone, Deserialize)]
pub struct PackRelease {
    pub id: String,
    pub name: String,
    pub url: String,
    pub sha256: String,
    pub size: u64,
}

/// Load the pack catalog from GitHub, falling back to the embedded copy.
pub fn load_catalog() -> Result<PackCatalog, Box<dyn std::error::Error + Send + Sync>> {
    if let Ok(catalog) = fetch_catalog(CATALOG_URL) {
        return Ok(catalog);
    }
    Ok(serde_json::from_str(EMBEDDED_CATALOG)?)
}

fn fetch_catalog(url: &str) -> Result<PackCatalog, Box<dyn std::error::Error + Send + Sync>> {
    let response = ureq::get(url).call()?;
    if !response.status().is_success() {
        return Err(format!("catalog fetch failed: HTTP {}", response.status()).into());
    }
    let body = response.into_body().read_to_string()?;
    Ok(serde_json::from_str(&body)?)
}

/// Returns true when `packs_root/<id>/manifest.json` exists and parses.
pub fn is_pack_installed(id: &str) -> bool {
    let Some(root) = packs_root() else {
        return false;
    };
    let pack_dir = root.join(id);
    load_manifest(&pack_dir).is_ok()
}

/// Install packs by id from the catalog (`all` installs every catalog entry).
pub fn install_packs(
    ids: &[String],
    all: bool,
    from: Option<&Path>,
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let dest = packs_root().ok_or("could not resolve config packs directory")?;
    fs::create_dir_all(&dest)?;

    if let Some(archive) = from {
        let id = ids
            .first()
            .ok_or("specify a pack id when using --from (e.g. webster1913-en)")?;
        install_from_archive(archive, id, &dest)?;
        println!("Installed pack \"{id}\" to {}", dest.display());
        return Ok(());
    }

    let catalog = load_catalog()?;
    let to_install: Vec<&PackRelease> = if all {
        catalog.packs.iter().collect()
    } else {
        if ids.is_empty() {
            return Err("specify pack ids (e.g. webster1913-en) or pass --all".into());
        }
        let mut selected = Vec::with_capacity(ids.len());
        for id in ids {
            let pack = catalog.packs.iter().find(|p| p.id == *id).ok_or_else(|| {
                format!("unknown pack id \"{id}\" (see: dictionary-tui pack list)")
            })?;
            selected.push(pack);
        }
        selected
    };

    for pack in to_install {
        eprint!("Installing {} ({})… ", pack.name, pack.id);
        let tmp = download_pack(pack)?;
        verify_sha256(&tmp, &pack.sha256)?;
        extract_pack(&tmp, &dest)?;
        let _ = fs::remove_file(&tmp);
        println!("done → {}", dest.join(&pack.id).display());
    }

    Ok(())
}

/// Re-install all catalog packs (same as `install --all`).
pub fn update_packs() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    install_packs(&[], true, None)
}

fn download_pack(pack: &PackRelease) -> Result<PathBuf, Box<dyn std::error::Error + Send + Sync>> {
    let response = ureq::get(&pack.url).call()?;
    if !response.status().is_success() {
        return Err(format!(
            "download failed for {}: HTTP {}",
            pack.id,
            response.status()
        )
        .into());
    }

    let tmp = tempfile_path(&format!("{}.tar.gz", pack.id));
    let mut file = File::create(&tmp)?;
    let mut reader = response.into_body().into_reader();
    io::copy(&mut reader, &mut file)?;
    Ok(tmp)
}

fn install_from_archive(
    archive: &Path,
    id: &str,
    dest: &Path,
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    if !archive.is_file() {
        return Err(format!("archive not found: {}", archive.display()).into());
    }
    extract_pack(archive, dest)?;
    let pack_dir = dest.join(id);
    if !pack_dir.join("manifest.json").exists() {
        return Err(format!(
            "archive did not contain pack \"{id}\" (expected {}/manifest.json)",
            pack_dir.display()
        )
        .into());
    }
    Ok(())
}

fn verify_sha256(
    path: &Path,
    expected: &str,
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let mut file = File::open(path)?;
    let mut hasher = Sha256::new();
    let mut buf = [0u8; 16 * 1024];
    loop {
        let n = file.read(&mut buf)?;
        if n == 0 {
            break;
        }
        hasher.update(&buf[..n]);
    }
    let digest = hex_encode(hasher.finalize());
    let expected = expected.to_lowercase();
    if digest != expected {
        return Err(format!(
            "checksum mismatch for {} (got {digest}, expected {expected})",
            path.display()
        )
        .into());
    }
    Ok(())
}

fn extract_pack(
    archive_path: &Path,
    dest_packs_root: &Path,
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let file = File::open(archive_path)?;
    let decoder = GzDecoder::new(file);
    let mut archive = Archive::new(decoder);
    archive.unpack(dest_packs_root)?;
    Ok(())
}

fn tempfile_path(name: &str) -> PathBuf {
    std::env::temp_dir().join(format!("dictionary-tui-{name}"))
}

fn hex_encode(bytes: impl AsRef<[u8]>) -> String {
    bytes.as_ref().iter().fold(
        String::with_capacity(bytes.as_ref().len() * 2),
        |mut s, b| {
            use std::fmt::Write;
            let _ = write!(s, "{b:02x}");
            s
        },
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::process::Command;

    #[test]
    fn embedded_catalog_parses() {
        let catalog: PackCatalog = serde_json::from_str(EMBEDDED_CATALOG).expect("catalog json");
        assert_eq!(catalog.packs.len(), 3);
        assert!(!catalog.release_tag.is_empty());
    }

    #[test]
    fn verify_local_dist_tarball_if_present() {
        let path = PathBuf::from("dist/webster1913-en.tar.gz");
        if !path.exists() {
            return;
        }
        let catalog: PackCatalog = serde_json::from_str(EMBEDDED_CATALOG).unwrap();
        let pack = catalog
            .packs
            .iter()
            .find(|p| p.id == "webster1913-en")
            .unwrap();
        verify_sha256(&path, &pack.sha256).expect("checksum");
    }

    #[test]
    fn extract_tarball_roundtrip() {
        let src = PathBuf::from("packs/cc-cedict");
        if !src.exists() {
            return;
        }
        let tmp = std::env::temp_dir().join(format!("dict-tui-pack-test-{}", std::process::id()));
        let _ = fs::remove_dir_all(&tmp);
        fs::create_dir_all(&tmp).unwrap();
        let archive = tmp.join("cc-cedict.tar.gz");
        let dest = tmp.join("out");
        fs::create_dir_all(&dest).unwrap();

        let status = Command::new("tar")
            .args([
                "-czf",
                archive.to_str().unwrap(),
                "-C",
                "packs",
                "cc-cedict",
            ])
            .status()
            .expect("tar");
        assert!(status.success());

        extract_pack(&archive, &dest).expect("extract");
        assert!(dest.join("cc-cedict/manifest.json").exists());

        let _ = fs::remove_dir_all(&tmp);
    }
}
