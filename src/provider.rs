//! Dictionary data provider abstraction.

use crate::schema::{DetailEntry, ListEntry, PackManifest};
use std::collections::HashMap;
use std::io::{BufRead, BufReader, Seek, SeekFrom};
use std::path::Path;

/// First token of `sort_key` (word/syllable) for tree grouping.
fn first_token(s: &str) -> &str {
    s.split_whitespace().next().unwrap_or("")
}

/// Abstraction for dictionary pack data: metadata, listing, and detail lookup.
pub trait Provider: Send + Sync {
    /// Pack manifest (id, name, language, entry count, etc.).
    fn metadata(&self) -> &PackManifest;

    /// Total number of entries in the pack.
    fn entry_count(&self) -> u64;

    /// Number of root entries (one per `leading_key` group) for collapsed view.
    fn root_count(&self) -> u64;

    /// List entries in sort order; `offset` is 0-based, `limit` caps the slice.
    fn list_entries(
        &self,
        offset: u64,
        limit: usize,
    ) -> Result<Vec<ListEntry>, Box<dyn std::error::Error + Send + Sync>>;

    /// Look up a full entry by headword or ID; returns `None` if not found.
    fn get_detail(
        &self,
        headword_or_id: &str,
    ) -> Result<Option<DetailEntry>, Box<dyn std::error::Error + Send + Sync>>;

    /// First entry index (offset) whose headword (English) or `sort_key`/pinyin (Chinese) contains
    /// the query. English: case-insensitive headword match. Chinese: case-insensitive `sort_key` match.
    fn search_first(
        &self,
        query: &str,
    ) -> Result<Option<u64>, Box<dyn std::error::Error + Send + Sync>>;

    /// First entry index where headword (English) or `sort_key` (Chinese) starts with the query
    /// (case-insensitive). Used for inline word-by-word search.
    fn search_first_prefix(
        &self,
        query: &str,
    ) -> Result<Option<u64>, Box<dyn std::error::Error + Send + Sync>>;

    /// List only root entries (one per `leading_key`) in order; for collapsed view paging.
    fn list_root_entries(
        &self,
        offset: u64,
        limit: usize,
    ) -> Result<Vec<ListEntry>, Box<dyn std::error::Error + Send + Sync>>;

    /// Collapsed-list index of the root that contains the given global entry offset (for jump/search in collapsed view).
    fn root_index_for_entry(&self, global_offset: u64) -> u64;

    /// Global entry offset of the Nth root (inverse of `root_index` for the root at that index). For focus preservation when toggling to expanded.
    fn root_offset_at(&self, collapsed_index: u64) -> u64;
}

/// Provider that reads dictionary data from a local pack directory.
pub struct LocalProvider {
    pub manifest: PackManifest,
    data_path: std::path::PathBuf,
    line_offsets: Vec<u64>,
    headword_to_line: HashMap<String, u64>,
    /// Headword per line index (for search in dictionary order).
    line_headwords: Vec<String>,
    /// Sort key per line index (for pinyin search when language is zh).
    line_sort_keys: Vec<String>,
    /// Line indices that are roots (first of each `leading_key` group) for collapsed view.
    root_indices: Vec<u64>,
}

impl LocalProvider {
    /// Opens a pack at `pack_root` using the given manifest.
    pub fn open(
        pack_root: &Path,
        manifest: PackManifest,
    ) -> Result<Self, Box<dyn std::error::Error + Send + Sync>> {
        let data_path = pack_root.join(&manifest.data_file);
        let content = std::fs::read(&data_path)?;

        let mut line_offsets = Vec::new();
        line_offsets.push(0);
        for (i, &b) in content.iter().enumerate() {
            if b == b'\n' {
                line_offsets.push((i + 1) as u64);
            }
        }

        let mut headword_to_line = HashMap::new();
        let mut line_headwords = Vec::with_capacity(line_offsets.len());
        let mut line_sort_keys = Vec::with_capacity(line_offsets.len());
        let mut root_indices = Vec::new();
        let mut prev_leading: Option<String> = None;
        for (line_index, &start) in line_offsets.iter().enumerate() {
            let end_u64 = line_offsets
                .get(line_index + 1)
                .copied()
                .unwrap_or(content.len() as u64);
            let end = usize::try_from(end_u64).unwrap_or(content.len());
            let start_usize = usize::try_from(start).unwrap_or(0);
            let line = &content[start_usize..end];
            if line.is_empty() {
                line_headwords.push(String::new());
                line_sort_keys.push(String::new());
                continue;
            }
            let value: serde_json::Value = if let Ok(v) = serde_json::from_slice(line) {
                v
            } else {
                line_headwords.push(String::new());
                line_sort_keys.push(String::new());
                continue;
            };
            let headword = value
                .get("headword")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string();
            let sort_key = value
                .get("sort_key")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string();
            let lead = value
                .get("leading_key")
                .and_then(|v| v.as_str())
                .filter(|s| !s.is_empty())
                .unwrap_or_else(|| first_token(&sort_key))
                .to_string();
            if prev_leading.as_deref() != Some(lead.as_str()) {
                root_indices.push(line_index as u64);
                prev_leading = Some(lead);
            }
            line_headwords.push(headword.clone());
            line_sort_keys.push(sort_key);
            headword_to_line
                .entry(headword)
                .or_insert(line_index as u64);
        }

        Ok(Self {
            manifest,
            data_path,
            line_offsets,
            headword_to_line,
            line_headwords,
            line_sort_keys,
            root_indices,
        })
    }
}

impl Provider for LocalProvider {
    fn metadata(&self) -> &PackManifest {
        &self.manifest
    }

    fn entry_count(&self) -> u64 {
        self.line_offsets.len() as u64
    }

    fn root_count(&self) -> u64 {
        self.root_indices.len() as u64
    }

    fn list_entries(
        &self,
        offset: u64,
        limit: usize,
    ) -> Result<Vec<ListEntry>, Box<dyn std::error::Error + Send + Sync>> {
        let file = std::fs::File::open(&self.data_path)?;
        let mut reader = BufReader::new(file);

        let end = (offset.saturating_add(limit as u64)).min(self.line_offsets.len() as u64);
        let capacity = (end.saturating_sub(offset)).try_into().unwrap_or(0);
        let mut list = Vec::with_capacity(capacity);

        for i in offset..end {
            let idx: usize = i.try_into().unwrap_or(0);
            let start_pos = self.line_offsets[idx];
            reader.seek(SeekFrom::Start(start_pos))?;

            let mut line_bytes = Vec::new();
            let n = reader.read_until(b'\n', &mut line_bytes)?;
            if n == 0 {
                continue;
            }
            if line_bytes.last() == Some(&b'\n') {
                line_bytes.pop();
            }

            let entry: DetailEntry = serde_json::from_slice(&line_bytes)?;
            list.push(ListEntry {
                headword: entry.headword,
                sort_key: entry.sort_key.clone(),
                leading_key: entry.leading_key,
                is_phrase: entry.is_phrase,
                pronunciation: entry.pronunciation,
                short_definition: entry.short_definition,
                part_of_speech: entry.part_of_speech,
            });
        }

        Ok(list)
    }

    fn get_detail(
        &self,
        headword_or_id: &str,
    ) -> Result<Option<DetailEntry>, Box<dyn std::error::Error + Send + Sync>> {
        let Some(&line_index) = self.headword_to_line.get(headword_or_id) else {
            return Ok(None);
        };
        let idx: usize = line_index.try_into().unwrap_or(0);
        let start_pos = self.line_offsets[idx];

        let file = std::fs::File::open(&self.data_path)?;
        let mut reader = BufReader::new(file);
        reader.seek(SeekFrom::Start(start_pos))?;

        let mut line_bytes = Vec::new();
        reader.read_until(b'\n', &mut line_bytes)?;
        if line_bytes.is_empty() {
            return Ok(None);
        }
        if line_bytes.last() == Some(&b'\n') {
            line_bytes.pop();
        }

        let entry: DetailEntry = serde_json::from_slice(&line_bytes)?;
        Ok(Some(entry))
    }

    fn search_first(
        &self,
        query: &str,
    ) -> Result<Option<u64>, Box<dyn std::error::Error + Send + Sync>> {
        if query.is_empty() {
            return Ok(None);
        }
        let q = query.to_lowercase();
        let is_zh = self.manifest.language == "zh";
        let first = if is_zh {
            self.line_sort_keys
                .iter()
                .enumerate()
                .find(|(_, sort_key)| sort_key.to_lowercase().contains(&q))
                .map(|(i, _)| i as u64)
        } else {
            self.line_headwords
                .iter()
                .enumerate()
                .find(|(_, headword)| headword.to_lowercase().contains(&q))
                .map(|(i, _)| i as u64)
        };
        Ok(first)
    }

    fn search_first_prefix(
        &self,
        query: &str,
    ) -> Result<Option<u64>, Box<dyn std::error::Error + Send + Sync>> {
        if query.is_empty() {
            return Ok(None);
        }
        let q = query.to_lowercase();
        let is_zh = self.manifest.language == "zh";
        let first = if is_zh {
            self.line_sort_keys
                .iter()
                .enumerate()
                .find(|(_, sort_key)| sort_key.to_lowercase().starts_with(&q))
                .map(|(i, _)| i as u64)
        } else {
            self.line_headwords
                .iter()
                .enumerate()
                .find(|(_, headword)| headword.to_lowercase().starts_with(&q))
                .map(|(i, _)| i as u64)
        };
        Ok(first)
    }

    fn list_root_entries(
        &self,
        offset: u64,
        limit: usize,
    ) -> Result<Vec<ListEntry>, Box<dyn std::error::Error + Send + Sync>> {
        let end = (offset.saturating_add(limit as u64)).min(self.root_indices.len() as u64);
        let offset_idx = usize::try_from(offset).unwrap_or(0);
        let end_idx = usize::try_from(end).unwrap_or(self.root_indices.len());
        let indices: Vec<u64> = self.root_indices[offset_idx..end_idx].to_vec();
        if indices.is_empty() {
            return Ok(Vec::new());
        }
        let file = std::fs::File::open(&self.data_path)?;
        let mut reader = BufReader::new(file);
        let mut list = Vec::with_capacity(indices.len());
        for &line_index in &indices {
            let line_idx = usize::try_from(line_index).unwrap_or(0);
            let start_pos = self.line_offsets[line_idx];
            reader.seek(SeekFrom::Start(start_pos))?;
            let mut line_bytes = Vec::new();
            let n = reader.read_until(b'\n', &mut line_bytes)?;
            if n == 0 {
                continue;
            }
            if line_bytes.last() == Some(&b'\n') {
                line_bytes.pop();
            }
            let entry: DetailEntry = serde_json::from_slice(&line_bytes)?;
            list.push(ListEntry {
                headword: entry.headword,
                sort_key: entry.sort_key.clone(),
                leading_key: entry.leading_key,
                is_phrase: entry.is_phrase,
                pronunciation: entry.pronunciation,
                short_definition: entry.short_definition,
                part_of_speech: entry.part_of_speech,
            });
        }
        Ok(list)
    }

    fn root_index_for_entry(&self, global_offset: u64) -> u64 {
        let idx = usize::try_from(global_offset).unwrap_or(usize::MAX);
        if idx >= self.line_offsets.len() {
            return self.root_indices.len().saturating_sub(1) as u64;
        }
        match self.root_indices.binary_search(&global_offset) {
            Ok(i) => i as u64,
            Err(0) => 0,
            Err(i) => (i - 1) as u64,
        }
    }

    fn root_offset_at(&self, collapsed_index: u64) -> u64 {
        let i = usize::try_from(collapsed_index).unwrap_or(usize::MAX);
        if self.root_indices.is_empty() {
            return 0;
        }
        let i = i.min(self.root_indices.len() - 1);
        self.root_indices[i]
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::schema::PackManifest;
    use std::fs;
    use std::path::PathBuf;

    fn test_pack_dir() -> PathBuf {
        std::env::temp_dir().join(format!("dict_tui_test_{}", std::process::id()))
    }

    #[test]
    fn local_provider_open_list_and_detail() {
        let temp_dir = test_pack_dir();
        fs::create_dir_all(&temp_dir).expect("create test dir");

        let manifest_json = r#"{
            "id": "test-pack",
            "name": "Test Pack",
            "language": "en",
            "sort": "alphabetical",
            "entry_count": 2,
            "data_file": "entries.jsonl"
        }"#;
        fs::write(temp_dir.join("manifest.json"), manifest_json).expect("write manifest");

        let entries_jsonl = r#"{"headword":"apple","sort_key":"apple","short_definition":"fruit","full_definition":"A fruit."}
{"headword":"bee","sort_key":"bee","short_definition":"insect"}"#;
        fs::write(temp_dir.join("entries.jsonl"), entries_jsonl).expect("write entries");

        let manifest: PackManifest = serde_json::from_str(manifest_json).expect("parse manifest");
        let provider = LocalProvider::open(&temp_dir, manifest).expect("open pack");

        assert_eq!(provider.entry_count(), 2);

        let list = provider.list_entries(0, 2).expect("list_entries");
        assert_eq!(list.len(), 2);
        assert_eq!(list[0].headword, "apple");

        let bee = provider.get_detail("bee").expect("get_detail");
        assert!(bee.is_some());
        assert_eq!(bee.unwrap().headword, "bee");

        assert!(provider
            .get_detail("missing")
            .expect("get_detail")
            .is_none());

        let _ = fs::remove_dir_all(&temp_dir);
    }
}
