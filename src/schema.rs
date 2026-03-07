//! Schema types for dictionary pack manifests and entries (list/detail).

use serde::{Deserialize, Serialize};

/// Manifest for a dictionary pack (metadata and file references).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PackManifest {
    pub id: String,
    pub name: String,
    pub language: String,
    pub sort: String,
    pub entry_count: u64,
    pub data_file: String,
    pub license: Option<String>,
    pub source_url: Option<String>,
}

/// Entry shown in list view (headword and summary).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ListEntry {
    pub headword: String,
    pub sort_key: String,
    #[serde(default)]
    pub leading_key: Option<String>,
    #[serde(default)]
    pub is_phrase: Option<bool>,
    pub pronunciation: Option<String>,
    pub short_definition: Option<String>,
    #[serde(default)]
    pub part_of_speech: Option<String>,
}

/// One phrase form and its definition within a detail entry.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PhraseItem {
    pub form: String,
    pub definition: String,
}

/// Full entry for detail view (extends list fields with full text and phrases).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DetailEntry {
    pub headword: String,
    pub sort_key: String,
    #[serde(default)]
    pub leading_key: Option<String>,
    #[serde(default)]
    pub is_phrase: Option<bool>,
    pub pronunciation: Option<String>,
    pub short_definition: Option<String>,
    pub full_definition: Option<String>,
    pub phrases: Option<Vec<PhraseItem>>,
    #[serde(default)]
    pub part_of_speech: Option<String>,
}
