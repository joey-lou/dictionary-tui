//! Dictionary data provider abstraction.

use crate::schema::{DetailEntry, ListEntry, PackManifest};
use std::collections::HashMap;
use std::io::{BufRead, BufReader, Seek, SeekFrom};
use std::path::Path;

/// Strip tone marks from pinyin to plain ASCII letters for search matching (e.g. "ài" -> "ai").
fn pinyin_to_plain(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    for c in s.chars() {
        let plain = match c {
            'ā' | 'á' | 'ǎ' | 'à' => 'a',
            'ē' | 'é' | 'ě' | 'è' => 'e',
            'ī' | 'í' | 'ǐ' | 'ì' => 'i',
            'ō' | 'ó' | 'ǒ' | 'ò' => 'o',
            'ū' | 'ú' | 'ǔ' | 'ù' => 'u',
            'ǖ' | 'ǘ' | 'ǚ' | 'ǜ' | 'ü' | 'Ü' => 'v',
            'ɡ' => 'g',
            _ => c,
        };
        out.push(plain);
    }
    out.to_lowercase()
}

/// One syllable in plain letters without tone digit (e.g. "ai1" -> "ai", "lu:2" -> "lv", "nǚ" -> "nv").
fn pinyin_syllable_base(syllable: &str) -> String {
    let mut s = pinyin_to_plain(syllable);
    if let Some(stripped) = s.strip_suffix(['1', '2', '3', '4', '5']) {
        s = stripped.to_string();
    }
    s = s.replace("u:", "v");
    s
}

/// Plain searchable syllable bases for a `sort_key` (space-separated syllables).
fn pinyin_syllable_bases(sort_key: &str) -> Vec<String> {
    sort_key
        .split_whitespace()
        .map(pinyin_syllable_base)
        .filter(|s| !s.is_empty())
        .collect()
}

/// Prefix match on pinyin syllables; avoids "ni" matching "niu" (CC-CEDICT numbered keys).
fn pinyin_syllable_prefix_match(sort_key: &str, query: &str) -> bool {
    let q = pinyin_query_plain(query);
    if q.is_empty() {
        return false;
    }
    pinyin_syllable_bases(sort_key).iter().any(|base| {
        if !base.starts_with(&q) {
            return false;
        }
        if base.len() == q.len() {
            return true;
        }
        // "ni" must not match syllable base "niu"
        !base
            .chars()
            .nth(q.len())
            .is_some_and(|c| c.is_ascii_alphabetic())
    })
}

/// Substring match on concatenated syllable bases (for `search_first`).
fn pinyin_syllable_contains_match(sort_key: &str, query: &str) -> bool {
    let q = pinyin_query_plain(query);
    if q.is_empty() {
        return false;
    }
    let joined: String = pinyin_syllable_bases(sort_key).concat();
    joined.contains(&q)
}

/// Normalize a search query to plain letters (strip tone digits from numbered pinyin).
fn pinyin_query_plain(query: &str) -> String {
    let query = query.trim();
    if query.is_empty() {
        return String::new();
    }
    if query.split_whitespace().count() > 1 {
        return pinyin_syllable_bases(query).concat();
    }
    pinyin_syllable_base(query)
}

fn query_has_cjk(query: &str) -> bool {
    query.chars().any(|c| {
        let u = u32::from(c);
        (0x4E00..=0x9FFF).contains(&u)
            || (0x3400..=0x4DBF).contains(&u)
            || (0x20000..=0x2A6DF).contains(&u)
    })
}

fn zh_entry_matches_prefix(entry: &ListEntry, query: &str, sort: &str) -> bool {
    if query_has_cjk(query) {
        return entry.headword.starts_with(query);
    }
    if sort == "pinyin" {
        return pinyin_syllable_prefix_match(&entry.sort_key, query);
    }
    entry
        .sort_key
        .to_lowercase()
        .starts_with(&query.to_lowercase())
}

fn zh_entry_matches_contains(entry: &ListEntry, query: &str, sort: &str) -> bool {
    if query_has_cjk(query) {
        return entry.headword.contains(query);
    }
    if sort == "pinyin" {
        return pinyin_syllable_contains_match(&entry.sort_key, query);
    }
    entry
        .sort_key
        .to_lowercase()
        .contains(&query.to_lowercase())
}

/// Display pronunciation in the list/detail columns (lowercase tone-marked pinyin for Chinese).
pub fn format_pronunciation_display(language: &str, pronunciation: Option<&str>) -> String {
    let Some(pron) = pronunciation else {
        return String::new();
    };
    if language == "zh" {
        pron.to_lowercase()
    } else {
        pron.to_string()
    }
}

/// Normalize pinyin for sort: base letter + tone digit so a<b<c and 1st<2nd<3rd<4th tone.
fn pinyin_sort_key(s: &str) -> String {
    let mut out = String::with_capacity(s.len() + 4);
    for c in s.chars() {
        match c {
            'ā' => out.push_str("a1"),
            'á' => out.push_str("a2"),
            'ǎ' => out.push_str("a3"),
            'à' => out.push_str("a4"),
            'ē' => out.push_str("e1"),
            'é' => out.push_str("e2"),
            'ě' => out.push_str("e3"),
            'è' => out.push_str("e4"),
            'ī' => out.push_str("i1"),
            'í' => out.push_str("i2"),
            'ǐ' => out.push_str("i3"),
            'ì' => out.push_str("i4"),
            'ō' => out.push_str("o1"),
            'ó' => out.push_str("o2"),
            'ǒ' => out.push_str("o3"),
            'ò' => out.push_str("o4"),
            'ū' => out.push_str("u1"),
            'ú' => out.push_str("u2"),
            'ǔ' => out.push_str("u3"),
            'ù' => out.push_str("u4"),
            'ǖ' => out.push_str("v1"),
            'ǘ' => out.push_str("v2"),
            'ǚ' => out.push_str("v3"),
            'ǜ' => out.push_str("v4"),
            'ü' | 'Ü' => out.push_str("v5"), // neutral
            'ɡ' => out.push('g'),            // U+0261
            _ => out.push(c),
        }
    }
    out.to_lowercase()
}

/// Abstraction for dictionary pack data: metadata, listing, and detail lookup.
pub trait Provider: Send + Sync {
    fn metadata(&self) -> &PackManifest;
    fn entry_count(&self) -> u64;

    /// Number of root entries (one per unique headword group) for collapsed view.
    fn root_count(&self) -> u64;

    /// List entries in sorted order; `offset` is 0-based into the sorted list.
    fn list_entries(
        &self,
        offset: u64,
        limit: usize,
    ) -> Result<Vec<ListEntry>, Box<dyn std::error::Error + Send + Sync>>;

    /// Full entry at the given sorted index; returns `None` if out of range.
    fn get_detail(
        &self,
        sorted_index: u64,
    ) -> Result<Option<DetailEntry>, Box<dyn std::error::Error + Send + Sync>>;

    /// First sorted index whose headword or `sort_key` contains the query (case-insensitive).
    fn search_first(
        &self,
        query: &str,
    ) -> Result<Option<u64>, Box<dyn std::error::Error + Send + Sync>>;

    /// First sorted index where headword or `sort_key` starts with the query (case-insensitive).
    fn search_first_prefix(
        &self,
        query: &str,
    ) -> Result<Option<u64>, Box<dyn std::error::Error + Send + Sync>>;

    /// List only root entries (one per headword group) in sorted order.
    fn list_root_entries(
        &self,
        offset: u64,
        limit: usize,
    ) -> Result<Vec<ListEntry>, Box<dyn std::error::Error + Send + Sync>>;

    /// Collapsed-view index of the root containing the given sorted entry offset.
    fn root_index_for_entry(&self, sorted_offset: u64) -> u64;

    /// Sorted entry offset of the Nth root.
    fn root_offset_at(&self, collapsed_index: u64) -> u64;

    /// Number of entries sharing the headword of root at `collapsed_index`.
    fn group_size(&self, collapsed_index: u64) -> usize;
}

/// Provider that reads dictionary data from a local pack directory.
/// Keeps lightweight entry metadata in memory; seeks to disk only for detail view.
pub struct LocalProvider {
    pub manifest: PackManifest,
    data_path: std::path::PathBuf,
    line_offsets: Vec<u64>,
    entries: Vec<ListEntry>,
    /// Sorted position to original JSONL line index.
    sorted_line_map: Vec<usize>,
    /// First entry index of each headword group.
    root_indices: Vec<usize>,
}

#[allow(clippy::cast_possible_truncation)]
impl LocalProvider {
    pub fn open(
        pack_root: &Path,
        manifest: PackManifest,
    ) -> Result<Self, Box<dyn std::error::Error + Send + Sync>> {
        let data_path = pack_root.join(&manifest.data_file);
        let content = std::fs::read(&data_path)?;

        let mut line_offsets: Vec<u64> = vec![0];
        for (i, &b) in content.iter().enumerate() {
            if b == b'\n' {
                line_offsets.push((i + 1) as u64);
            }
        }

        let mut raw_entries: Vec<(usize, ListEntry)> = Vec::with_capacity(line_offsets.len());
        for (line_index, &start) in line_offsets.iter().enumerate() {
            let end = line_offsets
                .get(line_index + 1)
                .copied()
                .unwrap_or(content.len() as u64);
            let end = usize::try_from(end).unwrap_or(content.len());
            let start = usize::try_from(start).unwrap_or(0);
            let line = &content[start..end];
            if line.is_empty() {
                continue;
            }
            let entry: ListEntry = match serde_json::from_slice(line) {
                Ok(e) => e,
                Err(_) => continue,
            };
            if entry.headword.is_empty() {
                continue;
            }
            raw_entries.push((line_index, entry));
        }

        if manifest.sort == "pinyin" {
            let mut primary_key: HashMap<String, String> = HashMap::new();
            for (_, entry) in &raw_entries {
                let existing = primary_key
                    .entry(entry.headword.clone())
                    .or_insert_with(|| entry.sort_key.clone());
                if entry.sort_key < *existing {
                    existing.clone_from(&entry.sort_key);
                }
            }
            raw_entries.sort_by(|(_, a), (_, b)| {
                let pa = primary_key.get(&a.headword).map_or("", String::as_str);
                let pb = primary_key.get(&b.headword).map_or("", String::as_str);
                pinyin_sort_key(pa)
                    .cmp(&pinyin_sort_key(pb))
                    .then_with(|| a.headword.cmp(&b.headword))
                    .then_with(|| pinyin_sort_key(&a.sort_key).cmp(&pinyin_sort_key(&b.sort_key)))
            });
        } else {
            raw_entries.sort_by(|(_, a), (_, b)| {
                a.sort_key
                    .cmp(&b.sort_key)
                    .then_with(|| a.headword.cmp(&b.headword))
            });
        }

        let mut entries = Vec::with_capacity(raw_entries.len());
        let mut sorted_line_map = Vec::with_capacity(raw_entries.len());
        let mut root_indices = Vec::new();
        let mut prev_headword: Option<&str> = None;

        for (i, (line_idx, entry)) in raw_entries.iter().enumerate() {
            if prev_headword != Some(entry.headword.as_str()) {
                root_indices.push(i);
                prev_headword = Some(entry.headword.as_str());
            }
            sorted_line_map.push(*line_idx);
            entries.push(entry.clone());
        }

        Ok(Self {
            manifest,
            data_path,
            line_offsets,
            entries,
            sorted_line_map,
            root_indices,
        })
    }
}

#[allow(clippy::cast_possible_truncation)]
impl Provider for LocalProvider {
    fn metadata(&self) -> &PackManifest {
        &self.manifest
    }

    fn entry_count(&self) -> u64 {
        self.entries.len() as u64
    }

    fn root_count(&self) -> u64 {
        self.root_indices.len() as u64
    }

    fn list_entries(
        &self,
        offset: u64,
        limit: usize,
    ) -> Result<Vec<ListEntry>, Box<dyn std::error::Error + Send + Sync>> {
        let start = usize::try_from(offset)
            .unwrap_or(usize::MAX)
            .min(self.entries.len());
        let end = start.saturating_add(limit).min(self.entries.len());
        Ok(self.entries[start..end].to_vec())
    }

    fn get_detail(
        &self,
        sorted_index: u64,
    ) -> Result<Option<DetailEntry>, Box<dyn std::error::Error + Send + Sync>> {
        let idx = usize::try_from(sorted_index).unwrap_or(usize::MAX);
        let Some(&line_index) = self.sorted_line_map.get(idx) else {
            return Ok(None);
        };
        let Some(&start_pos) = self.line_offsets.get(line_index) else {
            return Ok(None);
        };

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
        let found = if self.manifest.language == "zh" {
            self.entries
                .iter()
                .enumerate()
                .find(|(_, e)| zh_entry_matches_contains(e, query, self.manifest.sort.as_str()))
        } else {
            let q = query.to_lowercase();
            self.entries
                .iter()
                .enumerate()
                .find(|(_, e)| e.headword.to_lowercase().contains(&q))
        };
        Ok(found.map(|(i, _)| i as u64))
    }

    fn search_first_prefix(
        &self,
        query: &str,
    ) -> Result<Option<u64>, Box<dyn std::error::Error + Send + Sync>> {
        if query.is_empty() {
            return Ok(None);
        }
        let found = if self.manifest.language == "zh" {
            self.entries
                .iter()
                .enumerate()
                .find(|(_, e)| zh_entry_matches_prefix(e, query, self.manifest.sort.as_str()))
        } else {
            let q = query.to_lowercase();
            self.entries
                .iter()
                .enumerate()
                .find(|(_, e)| e.headword.to_lowercase().starts_with(&q))
        };
        Ok(found.map(|(i, _)| i as u64))
    }

    fn list_root_entries(
        &self,
        offset: u64,
        limit: usize,
    ) -> Result<Vec<ListEntry>, Box<dyn std::error::Error + Send + Sync>> {
        let start = usize::try_from(offset)
            .unwrap_or(usize::MAX)
            .min(self.root_indices.len());
        let end = start.saturating_add(limit).min(self.root_indices.len());
        let list: Vec<ListEntry> = self.root_indices[start..end]
            .iter()
            .map(|&idx| self.entries[idx].clone())
            .collect();
        Ok(list)
    }

    fn root_index_for_entry(&self, sorted_offset: u64) -> u64 {
        let idx = usize::try_from(sorted_offset).unwrap_or(usize::MAX);
        match self.root_indices.binary_search(&idx) {
            Ok(i) => i as u64,
            Err(0) => 0,
            Err(i) => (i - 1) as u64,
        }
    }

    fn root_offset_at(&self, collapsed_index: u64) -> u64 {
        if self.root_indices.is_empty() {
            return 0;
        }
        let i = usize::try_from(collapsed_index)
            .unwrap_or(usize::MAX)
            .min(self.root_indices.len().saturating_sub(1));
        self.root_indices[i] as u64
    }

    fn group_size(&self, collapsed_index: u64) -> usize {
        let i = usize::try_from(collapsed_index).unwrap_or(usize::MAX);
        if i >= self.root_indices.len() {
            return 1;
        }
        let start = self.root_indices[i];
        let end = self
            .root_indices
            .get(i + 1)
            .copied()
            .unwrap_or(self.entries.len());
        end - start
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

        let bee = provider.get_detail(1).expect("get_detail");
        assert!(bee.is_some());
        assert_eq!(bee.unwrap().headword, "bee");

        assert!(provider.get_detail(99).expect("get_detail").is_none());

        let _ = fs::remove_dir_all(&temp_dir);
    }

    #[test]
    fn pinyin_sorted_and_grouped() {
        let temp_dir = test_pack_dir().with_extension("pinyin");
        fs::create_dir_all(&temp_dir).expect("create test dir");

        let manifest_json = r#"{
            "id": "zh-test",
            "name": "ZH Test",
            "language": "zh",
            "sort": "pinyin",
            "entry_count": 4,
            "data_file": "entries.jsonl"
        }"#;
        fs::write(temp_dir.join("manifest.json"), manifest_json).expect("write manifest");

        let entries = vec![
            r#"{"headword":"三","sort_key":"sān","pronunciation":"sān","short_definition":"three"}"#,
            r#"{"headword":"一","sort_key":"yī","pronunciation":"yī","short_definition":"one"}"#,
            r#"{"headword":"乤","sort_key":"shànɡ","pronunciation":"shànɡ","short_definition":"up (archaic)"}"#,
            r#"{"headword":"乤","sort_key":"hal","pronunciation":"hal","short_definition":"Korean reading"}"#,
        ];
        fs::write(temp_dir.join("entries.jsonl"), entries.join("\n")).expect("write entries");

        let manifest: PackManifest = serde_json::from_str(manifest_json).expect("parse manifest");
        let provider = LocalProvider::open(&temp_dir, manifest).expect("open pack");

        assert_eq!(provider.entry_count(), 4);

        let all = provider.list_entries(0, 10).expect("list all");
        assert_eq!(all[0].headword, "\u{4e64}");
        assert_eq!(all[0].sort_key, "hal");
        assert_eq!(all[1].headword, "\u{4e64}");
        assert_eq!(all[1].sort_key, "sh\u{00e0}n\u{0261}");
        assert_eq!(all[2].headword, "\u{4e09}");
        assert_eq!(all[3].headword, "\u{4e00}");

        assert_eq!(provider.root_count(), 3);
        assert_eq!(provider.group_size(0), 2);
        assert_eq!(provider.group_size(1), 1);

        // Search uses plain letters (ignore tone): "san" matches "sān"
        let idx = provider.search_first_prefix("san").expect("search");
        assert!(idx.is_some(), "'san' should match sān");

        let _ = fs::remove_dir_all(&temp_dir);
    }

    #[test]
    fn pinyin_search_plain_letters() {
        let temp_dir = test_pack_dir().with_extension("pinyin_search");
        fs::create_dir_all(&temp_dir).expect("create test dir");
        let manifest_json = r#"{"id":"zh","name":"ZH","language":"zh","sort":"pinyin","entry_count":2,"data_file":"entries.jsonl"}"#;
        fs::write(temp_dir.join("manifest.json"), manifest_json).expect("write manifest");
        let entries = vec![
            r#"{"headword":"爱","sort_key":"ài","pronunciation":"ài","short_definition":"love"}"#,
            r#"{"headword":"一","sort_key":"yī","pronunciation":"yī","short_definition":"one"}"#,
        ];
        fs::write(temp_dir.join("entries.jsonl"), entries.join("\n")).expect("write entries");
        let manifest: PackManifest = serde_json::from_str(manifest_json).expect("parse");
        let provider = LocalProvider::open(&temp_dir, manifest).expect("open");
        // Plain "ai" (no tone) must match "ài"
        let found = provider.search_first_prefix("ai").expect("search");
        assert_eq!(found, Some(0));
        let _ = fs::remove_dir_all(&temp_dir);
    }

    #[test]
    fn cedict_numbered_pinyin_search() {
        let temp_dir = test_pack_dir().with_extension("cedict_search");
        fs::create_dir_all(&temp_dir).expect("create test dir");
        let manifest_json = r#"{"id":"cc-cedict","name":"CEDICT","language":"zh","sort":"pinyin","entry_count":4,"data_file":"entries.jsonl"}"#;
        fs::write(temp_dir.join("manifest.json"), manifest_json).expect("write manifest");
        let entries = vec![
            r#"{"headword":"拗","sort_key":"niu4","pronunciation":"niù","short_definition":"stubborn"}"#,
            r#"{"headword":"你","sort_key":"ni3","pronunciation":"nǐ","short_definition":"you"}"#,
            r#"{"headword":"女","sort_key":"nu:3","pronunciation":"nǚ","short_definition":"woman"}"#,
            r#"{"headword":"驴","sort_key":"lu:2","pronunciation":"lǘ","short_definition":"donkey"}"#,
        ];
        fs::write(temp_dir.join("entries.jsonl"), entries.join("\n")).expect("write entries");
        let manifest: PackManifest = serde_json::from_str(manifest_json).expect("parse");
        let provider = LocalProvider::open(&temp_dir, manifest).expect("open");

        assert_eq!(provider.search_first_prefix("ni").expect("ni"), Some(1));
        assert_eq!(provider.search_first_prefix("ni3").expect("ni3"), Some(1));
        assert_eq!(provider.search_first_prefix("lv").expect("lv"), Some(0));
        assert_eq!(provider.search_first_prefix("nv").expect("nv"), Some(3));
        assert_eq!(provider.search_first_prefix("女").expect("女"), Some(3));

        let _ = fs::remove_dir_all(&temp_dir);
    }

    #[test]
    fn format_pronunciation_display_lowercases_zh() {
        assert_eq!(format_pronunciation_display("zh", Some("Āi")), "āi");
        assert_eq!(format_pronunciation_display("en", Some("Apˈple")), "Apˈple");
    }

    #[test]
    fn english_grouped_by_headword() {
        let temp_dir = test_pack_dir().with_extension("en_group");
        fs::create_dir_all(&temp_dir).expect("create test dir");

        let manifest_json = r#"{
            "id": "en-test",
            "name": "EN Test",
            "language": "en",
            "sort": "alphabetical",
            "entry_count": 4,
            "data_file": "entries.jsonl"
        }"#;
        fs::write(temp_dir.join("manifest.json"), manifest_json).expect("write manifest");

        let entries = vec![
            r#"{"headword":"abstract","sort_key":"abstract","part_of_speech":"adj","short_definition":"existing only in mind"}"#,
            r#"{"headword":"abstract","sort_key":"abstract","part_of_speech":"noun","short_definition":"a concept"}"#,
            r#"{"headword":"abstract","sort_key":"abstract","part_of_speech":"verb","short_definition":"to consider apart"}"#,
            r#"{"headword":"apple","sort_key":"apple","part_of_speech":"noun","short_definition":"a fruit"}"#,
        ];
        fs::write(temp_dir.join("entries.jsonl"), entries.join("\n")).expect("write entries");

        let manifest: PackManifest = serde_json::from_str(manifest_json).expect("parse manifest");
        let provider = LocalProvider::open(&temp_dir, manifest).expect("open pack");

        assert_eq!(provider.root_count(), 2);
        assert_eq!(provider.group_size(0), 3);
        assert_eq!(provider.group_size(1), 1);

        let _ = fs::remove_dir_all(&temp_dir);
    }
}
