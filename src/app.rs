//! TUI application loop and rendering.

use crate::config::{load_config, save_config, AppConfig};
use crate::pack::discover_packs;
use crate::provider::{LocalProvider, Provider};
use crate::schema::{ListEntry, PackManifest};
use crossterm::event::{self, Event, KeyCode, KeyEventKind};
use crossterm::terminal::{
    disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen,
};
use crossterm::ExecutableCommand;
use ratatui::backend::CrosstermBackend;
use ratatui::layout::{Constraint, Direction, Layout};
use ratatui::style::{Modifier, Style};
use ratatui::text::Line;
use ratatui::widgets::{Block, Borders, List, ListItem, ListState, Paragraph, Wrap};
use ratatui::Terminal;
use std::error::Error;
use std::io::{self, Stdout};
use std::path::PathBuf;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

type AppResult<T> = Result<T, Box<dyn Error + Send + Sync>>;

const INCREMENT_PRESETS: [u64; 6] = [1, 2, 5, 10, 50, 100];
const HEADWORD_WIDTH: usize = 24;
const POS_WIDTH: usize = 6;

/// Leading key for grouping (first word/syllable of `sort_key`).
fn entry_leading_key(entry: &ListEntry) -> &str {
    entry
        .leading_key
        .as_deref()
        .unwrap_or_else(|| entry.sort_key.split_whitespace().next().unwrap_or(""))
}

fn is_compound(entry: &ListEntry) -> bool {
    entry
        .is_phrase
        .unwrap_or_else(|| entry.sort_key.contains(' '))
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum ViewMode {
    /// Only root entries (one per `leading_key`); fewer pages.
    Collapsed,
    /// All entries; full page count.
    Expanded,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Screen {
    List,
    Detail,
    IncrementInput,
}

struct AppState {
    provider: LocalProvider,
    screen: Screen,
    page_size: usize,
    current_page: u64,
    selected_idx: usize,
    current_entries: Vec<ListEntry>,
    /// Collapsed = page over roots only; Expanded = page over all entries. Page count and indices depend on this.
    view_mode: ViewMode,
    increment_pages: u64,
    increment_preset_idx: usize,
    increment_input: String,
    /// Inline search: buffer and active flag. When true, typing filters list to first prefix match.
    search_buffer: String,
    search_active: bool,
}

struct PackPickerState {
    packs: Vec<(PathBuf, PackManifest)>,
    selected_idx: usize,
}

impl PackPickerState {
    const fn new(packs: Vec<(PathBuf, PackManifest)>) -> Self {
        Self {
            packs,
            selected_idx: 0,
        }
    }

    fn selected(&self) -> Option<(PathBuf, PackManifest)> {
        self.packs.get(self.selected_idx).cloned()
    }

    const fn move_next(&mut self) {
        if self.packs.is_empty() {
            return;
        }
        self.selected_idx = (self.selected_idx + 1) % self.packs.len();
    }

    const fn move_prev(&mut self) {
        if self.packs.is_empty() {
            return;
        }
        if self.selected_idx == 0 {
            self.selected_idx = self.packs.len().saturating_sub(1);
        } else {
            self.selected_idx -= 1;
        }
    }
}

impl AppState {
    fn new(provider: LocalProvider) -> AppResult<Self> {
        let config = load_config();
        let jump = config.jump_size.max(1);
        let preset_idx = INCREMENT_PRESETS
            .iter()
            .position(|&p| p == jump)
            .unwrap_or(0);
        let mut state = Self {
            provider,
            screen: Screen::List,
            page_size: 15,
            current_page: 0,
            selected_idx: 0,
            current_entries: Vec::new(),
            view_mode: ViewMode::Collapsed,
            increment_pages: jump,
            increment_preset_idx: preset_idx,
            increment_input: String::new(),
            search_buffer: String::new(),
            search_active: false,
        };
        state.reload_page()?;
        Ok(state)
    }

    fn persist_jump_size(&self) {
        let config = AppConfig {
            jump_size: self.increment_pages,
        };
        let _ = save_config(&config);
    }

    fn page_count(&self) -> u64 {
        let total = self.view_entry_count();
        if total == 0 {
            return 1;
        }
        let page_size_u64 = self.page_size as u64;
        total.div_ceil(page_size_u64).max(1)
    }

    const fn offset(&self) -> u64 {
        self.current_page.saturating_mul(self.page_size as u64)
    }

    /// Entry count for the current view (roots only or all).
    fn view_entry_count(&self) -> u64 {
        match self.view_mode {
            ViewMode::Collapsed => self.provider.root_count(),
            ViewMode::Expanded => self.provider.entry_count(),
        }
    }

    /// Selected entry on the current page, or None.
    fn selected_entry(&self) -> Option<&ListEntry> {
        self.current_entries.get(self.selected_idx)
    }

    fn reload_page(&mut self) -> AppResult<()> {
        let offset = self.offset();
        self.current_entries = match self.view_mode {
            ViewMode::Collapsed => self.provider.list_root_entries(offset, self.page_size)?,
            ViewMode::Expanded => self.provider.list_entries(offset, self.page_size)?,
        };
        self.selected_idx = if self.current_entries.is_empty() {
            0
        } else {
            self.selected_idx
                .min(self.current_entries.len().saturating_sub(1))
        };
        Ok(())
    }

    fn move_next_row(&mut self) -> AppResult<()> {
        if self.selected_idx + 1 < self.current_entries.len() {
            self.selected_idx += 1;
            return Ok(());
        }
        self.next_page()
    }

    fn move_prev_row(&mut self) -> AppResult<()> {
        if self.selected_idx > 0 {
            self.selected_idx -= 1;
            return Ok(());
        }
        if self.current_page > 0 {
            self.current_page -= 1;
            self.reload_page()?;
            if !self.current_entries.is_empty() {
                self.selected_idx = self.current_entries.len().saturating_sub(1);
            }
        }
        Ok(())
    }

    fn next_page(&mut self) -> AppResult<()> {
        let page_count = self.page_count();
        if self.current_page + self.increment_pages < page_count {
            self.current_page += self.increment_pages;
        } else {
            self.current_page = page_count.saturating_sub(1);
        }
        self.selected_idx = 0;
        self.reload_page()
    }

    fn prev_page(&mut self) -> AppResult<()> {
        self.current_page = self.current_page.saturating_sub(self.increment_pages);
        self.selected_idx = 0;
        self.reload_page()
    }

    fn random_page(&mut self) -> AppResult<()> {
        let page_count = self.page_count();
        if page_count <= 1 {
            return Ok(());
        }
        let seed = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_secs() ^ u64::from(d.subsec_nanos()))
            .unwrap_or(0);
        self.current_page = seed % page_count;
        self.reload_page()?;
        let n = self.current_entries.len();
        if n > 0 {
            let entry_seed = (seed >> 16).wrapping_add(seed) as usize;
            self.selected_idx = entry_seed % n;
        }
        Ok(())
    }

    const fn cycle_increment_next(&mut self) {
        self.increment_preset_idx = (self.increment_preset_idx + 1) % INCREMENT_PRESETS.len();
        self.increment_pages = INCREMENT_PRESETS[self.increment_preset_idx];
    }

    const fn cycle_increment_prev(&mut self) {
        if self.increment_preset_idx == 0 {
            self.increment_preset_idx = INCREMENT_PRESETS.len().saturating_sub(1);
        } else {
            self.increment_preset_idx -= 1;
        }
        self.increment_pages = INCREMENT_PRESETS[self.increment_preset_idx];
    }

    /// Jump to the entry at the given global offset (0-based). In collapsed view, maps to the root that contains it.
    fn jump_to_offset(&mut self, global_offset: u64) -> AppResult<()> {
        let page_size_u = self.page_size as u64;
        match self.view_mode {
            ViewMode::Collapsed => {
                let root_idx = self.provider.root_index_for_entry(global_offset);
                self.current_page = root_idx / page_size_u;
                self.reload_page()?;
                self.selected_idx = usize::try_from(root_idx % page_size_u)
                    .unwrap_or(0)
                    .min(self.current_entries.len().saturating_sub(1));
            }
            ViewMode::Expanded => {
                self.current_page = global_offset / page_size_u;
                self.reload_page()?;
                self.selected_idx = usize::try_from(global_offset % page_size_u)
                    .unwrap_or(0)
                    .min(self.current_entries.len().saturating_sub(1));
            }
        }
        Ok(())
    }

    /// Toggle between collapsed (roots only) and expanded (all entries). Keeps focus on the same word/location.
    fn toggle_view_mode(&mut self) -> AppResult<()> {
        let page_size_u = self.page_size as u64;
        let global_offset = match self.view_mode {
            ViewMode::Collapsed => {
                let collapsed_index = self.current_page * page_size_u + self.selected_idx as u64;
                self.provider.root_offset_at(collapsed_index)
            }
            ViewMode::Expanded => self.current_page * page_size_u + self.selected_idx as u64,
        };

        self.view_mode = match self.view_mode {
            ViewMode::Collapsed => ViewMode::Expanded,
            ViewMode::Expanded => ViewMode::Collapsed,
        };

        match self.view_mode {
            ViewMode::Collapsed => {
                let root_index = self.provider.root_index_for_entry(global_offset);
                self.current_page = root_index / page_size_u;
                self.reload_page()?;
                let n = self.current_entries.len();
                self.selected_idx = usize::try_from(root_index % page_size_u)
                    .unwrap_or(0)
                    .min(n.saturating_sub(1));
            }
            ViewMode::Expanded => {
                self.current_page = global_offset / page_size_u;
                self.reload_page()?;
                let n = self.current_entries.len();
                self.selected_idx = usize::try_from(global_offset % page_size_u)
                    .unwrap_or(0)
                    .min(n.saturating_sub(1));
            }
        }
        Ok(())
    }
}

struct TerminalGuard {
    stdout: Stdout,
}

impl TerminalGuard {
    fn new() -> AppResult<Self> {
        enable_raw_mode()?;
        let mut stdout = io::stdout();
        stdout.execute(EnterAlternateScreen)?;
        Ok(Self { stdout })
    }
}

impl Drop for TerminalGuard {
    fn drop(&mut self) {
        let _ = disable_raw_mode();
        let _ = self.stdout.execute(LeaveAlternateScreen);
    }
}

/// Runs the full TUI loop and returns when the user exits.
pub fn run() -> AppResult<()> {
    let packs = discover_packs()?;
    if packs.is_empty() {
        return Err(
            "no dictionary packs found. Add one under the config packs directory and retry.".into(),
        );
    }
    let _guard = TerminalGuard::new()?;
    let backend = CrosstermBackend::new(io::stdout());
    let mut terminal = Terminal::new(backend)?;

    let Some((pack_root, manifest)) = choose_pack(&mut terminal, packs)? else {
        return Ok(());
    };
    let provider = LocalProvider::open(&pack_root, manifest.clone()).map_err(|e| {
        format!(
            "failed to open pack \"{}\" at {}: {}",
            manifest.name,
            pack_root.display(),
            e
        )
    })?;
    let mut app = AppState::new(provider)?;

    loop {
        if let Ok(size) = terminal.size() {
            let body_height = size.height.saturating_sub(4).max(1);
            let list_inner = body_height.saturating_sub(2).max(1);
            let new_page_size = list_inner as usize;
            if new_page_size != app.page_size {
                app.page_size = new_page_size;
                let _ = app.reload_page();
            }
        }
        terminal.draw(|frame| render(frame, &app))?;

        if !event::poll(Duration::from_millis(120))? {
            continue;
        }
        let evt = event::read()?;
        if let Event::Key(key_event) = evt {
            if key_event.kind != KeyEventKind::Press {
                continue;
            }
            if handle_key(&mut app, key_event.code)? {
                break;
            }
        }
    }

    Ok(())
}

fn choose_pack(
    terminal: &mut Terminal<CrosstermBackend<Stdout>>,
    packs: Vec<(PathBuf, PackManifest)>,
) -> AppResult<Option<(PathBuf, PackManifest)>> {
    let mut picker = PackPickerState::new(packs);

    loop {
        terminal.draw(|frame| render_pack_picker(frame, &picker))?;

        if !event::poll(Duration::from_millis(120))? {
            continue;
        }
        let evt = event::read()?;
        let Event::Key(key_event) = evt else {
            continue;
        };
        if key_event.kind != KeyEventKind::Press {
            continue;
        }
        match key_event.code {
            KeyCode::Char('q' | 'Q') | KeyCode::Esc => return Ok(None),
            KeyCode::Down | KeyCode::Char('j') => picker.move_next(),
            KeyCode::Up | KeyCode::Char('k') => picker.move_prev(),
            KeyCode::Enter => return Ok(picker.selected()),
            _ => {}
        }
    }
}

fn render_pack_picker(frame: &mut ratatui::Frame<'_>, picker: &PackPickerState) {
    let area = frame.area();
    let [header_area, body_area, footer_area] = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(2),
            Constraint::Min(5),
            Constraint::Length(2),
        ])
        .areas(area);

    let title = format!("Select dictionary pack ({} found)", picker.packs.len());
    let header = Paragraph::new(title).block(Block::default().borders(Borders::ALL));
    frame.render_widget(header, header_area);

    let items: Vec<ListItem<'_>> = picker
        .packs
        .iter()
        .map(|(_, manifest)| {
            let label = format!(
                "{} [{}] • {} entries",
                manifest.name, manifest.language, manifest.entry_count
            );
            ListItem::new(Line::from(label))
        })
        .collect();

    let list = List::new(items)
        .block(Block::default().borders(Borders::ALL).title("Dictionaries"))
        .highlight_style(Style::default().add_modifier(Modifier::REVERSED));
    let mut state = ListState::default();
    state.select(Some(picker.selected_idx));
    frame.render_stateful_widget(list, body_area, &mut state);

    let footer = Paragraph::new("j/k or arrows select | Enter open | q/Esc quit")
        .block(Block::default().borders(Borders::ALL));
    frame.render_widget(footer, footer_area);
}

fn render(frame: &mut ratatui::Frame<'_>, app: &AppState) {
    let area = frame.area();
    let [header_area, body_area, footer_area] = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(2),
            Constraint::Min(3),
            Constraint::Length(2),
        ])
        .areas(area);

    let hints = match app.screen {
        Screen::List => {
            "↑↓ j/k move · Enter detail · Space expand/collapse · / search · ←→ pg · r random · +/- jump · i custom · q quit"
        }
        Screen::Detail => "Esc/Backspace back · q quit",
        Screen::IncrementInput => "Enter set jump · Esc cancel",
    };
    let title = format!(" dictionary-tui · {} ", app.provider.metadata().name);
    let header =
        Paragraph::new(hints).block(Block::default().borders(Borders::BOTTOM).title(title));
    frame.render_widget(header, header_area);

    match app.screen {
        Screen::List | Screen::IncrementInput => render_list(frame, body_area, app),
        Screen::Detail => render_detail(frame, body_area, app),
    }

    let (footer_text, page_info) = match app.screen {
        Screen::List => {
            let total = app.view_entry_count();
            let label = match app.view_mode {
                ViewMode::Collapsed => "roots",
                ViewMode::Expanded => "entries",
            };
            (
                "q quit · Space collapse/expand · Enter detail · / search · r random · +/- jump",
                format!(
                    "Page {} of {} · {} {} · jump {}",
                    app.current_page + 1,
                    app.page_count(),
                    total,
                    label,
                    app.increment_pages
                ),
            )
        }
        Screen::Detail => ("Esc back · q quit", String::new()),
        Screen::IncrementInput => (
            "Esc cancel · Enter set",
            format!(
                "Page {} of {} · jump {}",
                app.current_page + 1,
                app.page_count(),
                app.increment_pages
            ),
        ),
    };
    let footer_line = if page_info.is_empty() {
        footer_text.to_string()
    } else {
        format!("{page_info}  │  {footer_text}")
    };
    let footer = Paragraph::new(footer_line).block(Block::default().borders(Borders::TOP));
    frame.render_widget(footer, footer_area);
}

fn render_list(frame: &mut ratatui::Frame<'_>, area: ratatui::layout::Rect, app: &AppState) {
    let col_reserved = HEADWORD_WIDTH + POS_WIDTH + 2;
    let def_max = area
        .width
        .saturating_sub(u16::try_from(col_reserved).unwrap_or(32))
        .max(10) as usize;

    let entries = &app.current_entries;
    let mut items = Vec::with_capacity(entries.len().max(1));
    if entries.is_empty() {
        items.push(ListItem::new("No entries on this page"));
    } else {
        let max_head_chars = HEADWORD_WIDTH.saturating_sub(3);
        let mut prev_leading: Option<&str> = None;
        let show_tree = matches!(app.view_mode, ViewMode::Expanded);
        for entry in entries {
            let leading = entry_leading_key(entry);
            let compound = is_compound(entry);
            let indent = show_tree && prev_leading == Some(leading) && compound;
            prev_leading = Some(leading);

            let head = if entry.headword.chars().count() > max_head_chars {
                format!(
                    "{}…",
                    entry
                        .headword
                        .chars()
                        .take(max_head_chars)
                        .collect::<String>()
                )
            } else {
                entry.headword.clone()
            };
            let pos_str = entry.part_of_speech.as_deref().unwrap_or("").to_string();
            let def_str = entry.short_definition.as_deref().unwrap_or("");
            let def: String = def_str.chars().take(def_max).collect();
            let def = if def_str.chars().count() > def_max {
                format!("{}…", def.trim_end())
            } else {
                def
            };
            let prefix = if indent { " ·" } else { "  " };
            let trimmed_def = def.trim_start();
            let line =
                format!("{prefix:<2} {head:<HEADWORD_WIDTH$} {pos_str:<POS_WIDTH$} {trimmed_def}");
            items.push(ListItem::new(Line::from(line)));
        }
    }

    let view_label = match app.view_mode {
        ViewMode::Collapsed => "Collapsed",
        ViewMode::Expanded => "Expanded",
    };
    let list_title: String = if app.search_active && !app.search_buffer.is_empty() {
        format!(" Search: {} ", app.search_buffer)
    } else if app.search_active {
        " Search: (type to filter) ".to_string()
    } else {
        format!(" Entries · {view_label} ")
    };
    let list = List::new(items)
        .block(Block::default().borders(Borders::ALL).title(list_title))
        .highlight_style(Style::default().add_modifier(Modifier::REVERSED));

    let mut state = ListState::default();
    if !entries.is_empty() {
        state.select(Some(app.selected_idx));
    }
    frame.render_stateful_widget(list, area, &mut state);

    if app.screen == Screen::IncrementInput {
        let overlay_area = centered_rect(60, 20, area);
        let prompt = format!("Jump pages: {}", app.increment_input);
        let overlay = Paragraph::new(prompt).block(
            Block::default()
                .borders(Borders::ALL)
                .title(" Custom Increment "),
        );
        frame.render_widget(overlay, overlay_area);
    }
}

fn render_detail(frame: &mut ratatui::Frame<'_>, area: ratatui::layout::Rect, app: &AppState) {
    let Some(selected) = app.selected_entry() else {
        let missing = Paragraph::new("No selected entry")
            .block(Block::default().borders(Borders::ALL).title("Detail"));
        frame.render_widget(missing, area);
        return;
    };

    let detail = app.provider.get_detail(&selected.headword).ok().flatten();
    let text = if let Some(detail) = detail {
        let mut lines = vec![format!("Headword: {}", detail.headword)];
        if let Some(pos) = &detail.part_of_speech {
            lines.push(format!("Part of speech: {pos}"));
        }
        if let Some(pron) = detail.pronunciation {
            lines.push(format!("Pronunciation: {pron}"));
        }
        lines.push(String::new());
        lines.push(
            detail
                .full_definition
                .unwrap_or_else(|| "(none)".to_string()),
        );
        if let Some(phrases) = detail.phrases {
            lines.push(String::new());
            lines.push("Phrases:".to_string());
            for phrase in phrases {
                lines.push(format!("- {}: {}", phrase.form, phrase.definition));
            }
        }
        lines.join("\n")
    } else {
        "Detail not found for selected headword.".to_string()
    };

    let paragraph = Paragraph::new(text)
        .block(Block::default().borders(Borders::ALL).title("Detail"))
        .wrap(Wrap { trim: false });
    frame.render_widget(paragraph, area);
}

fn centered_rect(
    percent_x: u16,
    percent_y: u16,
    area: ratatui::layout::Rect,
) -> ratatui::layout::Rect {
    let [_, vertical, _] = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Percentage((100 - percent_y) / 2),
            Constraint::Percentage(percent_y),
            Constraint::Percentage((100 - percent_y) / 2),
        ])
        .areas::<3>(area);
    let [_, horizontal, _] = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Percentage((100 - percent_x) / 2),
            Constraint::Percentage(percent_x),
            Constraint::Percentage((100 - percent_x) / 2),
        ])
        .areas::<3>(vertical);
    horizontal
}

fn handle_key(app: &mut AppState, code: KeyCode) -> AppResult<bool> {
    if matches!(code, KeyCode::Char('q' | 'Q')) {
        return Ok(true);
    }

    match app.screen {
        Screen::List => {
            if app.search_active {
                match code {
                    KeyCode::Esc => {
                        app.search_buffer.clear();
                        app.search_active = false;
                    }
                    KeyCode::Backspace => {
                        app.search_buffer.pop();
                        if let Ok(Some(offset)) =
                            app.provider.search_first_prefix(app.search_buffer.as_str())
                        {
                            let _ = app.jump_to_offset(offset);
                        }
                    }
                    KeyCode::Char(c) => {
                        app.search_buffer.push(c);
                        if let Ok(Some(offset)) =
                            app.provider.search_first_prefix(app.search_buffer.as_str())
                        {
                            let _ = app.jump_to_offset(offset);
                        }
                    }
                    _ => {}
                }
            } else {
                match code {
                    KeyCode::Down | KeyCode::Char('j') => app.move_next_row()?,
                    KeyCode::Up | KeyCode::Char('k') => app.move_prev_row()?,
                    KeyCode::Right | KeyCode::Char('l') | KeyCode::PageDown => app.next_page()?,
                    KeyCode::Left | KeyCode::Char('h') | KeyCode::PageUp => app.prev_page()?,
                    KeyCode::Char(' ') => app.toggle_view_mode()?,
                    KeyCode::Enter => app.screen = Screen::Detail,
                    KeyCode::Char('r' | 'R') => app.random_page()?,
                    KeyCode::Char('+' | '=') => {
                        app.cycle_increment_next();
                        app.persist_jump_size();
                    }
                    KeyCode::Char('-' | '_') => {
                        app.cycle_increment_prev();
                        app.persist_jump_size();
                    }
                    KeyCode::Char('i' | 'I') => {
                        app.increment_input = app.increment_pages.to_string();
                        app.screen = Screen::IncrementInput;
                    }
                    KeyCode::Char('/' | 's' | 'S') => {
                        app.search_buffer.clear();
                        app.search_active = true;
                    }
                    _ => {}
                }
            }
        }
        Screen::Detail => match code {
            KeyCode::Esc | KeyCode::Backspace | KeyCode::Enter => app.screen = Screen::List,
            _ => {}
        },
        Screen::IncrementInput => match code {
            KeyCode::Esc => app.screen = Screen::List,
            KeyCode::Enter => {
                if let Ok(value) = app.increment_input.parse::<u64>() {
                    if value > 0 {
                        app.increment_pages = value;
                        app.persist_jump_size();
                    }
                }
                app.screen = Screen::List;
            }
            KeyCode::Backspace => {
                app.increment_input.pop();
            }
            KeyCode::Char(c) if c.is_ascii_digit() => {
                app.increment_input.push(c);
            }
            _ => {}
        },
    }
    Ok(false)
}
