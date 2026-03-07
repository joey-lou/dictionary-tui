//! Persisted app preferences (e.g. jump size).

use serde::{Deserialize, Serialize};
use std::path::PathBuf;

const CONFIG_FILENAME: &str = "config.json";

/// Persisted application config.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfig {
    /// Number of pages to jump on prev/next (page-turn increment).
    #[serde(default = "default_jump_size")]
    pub jump_size: u64,
}

const fn default_jump_size() -> u64 {
    1
}

impl Default for AppConfig {
    fn default() -> Self {
        Self {
            jump_size: default_jump_size(),
        }
    }
}

/// Returns the config directory, or `None` if it cannot be determined.
pub fn config_dir() -> Option<PathBuf> {
    directories::ProjectDirs::from("", "", "dictionary-tui").map(|p| p.config_dir().to_path_buf())
}

fn config_path() -> Option<PathBuf> {
    config_dir().map(|d| d.join(CONFIG_FILENAME))
}

/// Loads config from disk; returns default if file is missing or invalid.
pub fn load_config() -> AppConfig {
    let Some(path) = config_path() else {
        return AppConfig::default();
    };
    let Ok(data) = std::fs::read_to_string(&path) else {
        return AppConfig::default();
    };
    serde_json::from_str(&data).unwrap_or_default()
}

/// Saves config to disk; creates config dir if needed.
pub fn save_config(config: &AppConfig) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let Some(dir) = config_dir() else {
        return Ok(());
    };
    std::fs::create_dir_all(&dir)?;
    let path = dir.join(CONFIG_FILENAME);
    let data = serde_json::to_string_pretty(config)?;
    std::fs::write(path, data)?;
    Ok(())
}
