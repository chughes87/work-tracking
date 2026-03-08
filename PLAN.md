# Work Tracker — Implementation Plan

## Overview

A Python CLI tool (`wt`) that captures day-to-day work activities and generates summarized reports for self-review and manager discussions. Privacy-conscious: all data local, only text sent to Claude API for summarization.

## Architecture

- **CLI:** Click + Rich
- **Storage:** SQLite at `~/.local/share/work-tracker/work-tracker.db`
- **Config:** TOML at `~/.config/work-tracker/config.toml`
- **AI:** Claude API (anthropic SDK)
- **Voice:** faster-whisper (local transcription, optional)
- **Calendar:** icalendar for .ics parsing
- **Git:** gitpython for commit/branch inspection

## CLI Commands

```
wt log ["text"]                    # Log a work entry (interactive or inline)
wt voice [--duration 60]          # Record voice memo, transcribe, store
wt import git [--since] [--repo]  # Import git activity
wt import calendar <file/url>     # Import calendar events
wt entries [--date] [--category]  # List entries
wt edit <id> / wt delete <id>     # Manage entries
wt report today|yesterday|week    # Generate reports (--no-ai for raw)
wt remind on|off|status           # Periodic reminder via cron
wt config [set key value]         # Manage configuration
```

## Phases

### Phase 1: MVP — Manual Logging + Raw Reports ✅

- [x] Project scaffolding (pyproject.toml, package structure)
- [x] WorkEntry dataclass and category definitions
- [x] SQLite storage layer (insert, query, update, delete)
- [x] XDG-compliant config loading/saving
- [x] Markdown report rendering (chronological, grouped by category)
- [x] Click CLI: `log`, `entries`, `edit`, `delete`, `report --no-ai`, `config`
- [x] Unit tests (79 tests across all modules)

### Phase 2: AI Summarization via Claude API

- [ ] Implement `ai.py` with anthropic SDK
- [ ] Voice distillation: raw transcription → structured entry (summary, category, duration)
- [ ] Daily summary: batch of entries → grouped markdown report with time breakdown
- [ ] Weekly summary: daily summaries → weekly report with accomplishments, patterns, % breakdown
- [ ] `wt report` uses AI by default, `--no-ai` falls back to raw
- [ ] Handle missing API key gracefully (prompt user, fall back to raw)
- [ ] Add `ANTHROPIC_API_KEY` config support

### Phase 3: Git Import

- [ ] `wt import git` command using gitpython
- [ ] Scan commits from current repo (or `--repo <path>`)
- [ ] `--since` flag (default: today)
- [ ] Deduplicate: skip commits already imported (store commit hash in metadata)
- [ ] Auto-categorize as "dev"
- [ ] Extract branch name, files changed, commit message

### Phase 4: Voice Memos

- [ ] `wt voice` command
- [ ] Audio recording via sounddevice or pyaudio
- [ ] `--duration` flag (default: 60s), stop on silence or keypress
- [ ] Local transcription via faster-whisper
- [ ] Pipe transcription through AI distillation (Phase 2) for structured entry
- [ ] Graceful error if faster-whisper not installed

### Phase 5: Calendar Integration

- [ ] `wt import calendar <file>` for .ics files
- [ ] Parse events using icalendar library
- [ ] Extract: event title, start/end time, duration, attendees
- [ ] Auto-categorize as "meeting"
- [ ] `--since` / `--until` date filters
- [ ] Deduplicate by event UID in metadata
- [ ] Optional: URL support for remote calendars

### Phase 6: Scheduled Reminders

- [ ] `wt remind on --interval 90` installs cron job (weekdays only)
- [ ] `wt remind off` removes cron job
- [ ] `wt remind status` shows current schedule
- [ ] Desktop notification via `notify-send` prompting user to run `wt log`
- [ ] No background daemon — uses OS cron/systemd timer
- [ ] Guard against duplicate cron entries

## Data Model

```sql
CREATE TABLE entries (
    id TEXT PRIMARY KEY,           -- UUID
    timestamp TEXT NOT NULL,       -- ISO 8601
    source TEXT NOT NULL,          -- 'prompt' | 'voice' | 'git' | 'calendar'
    category TEXT,                 -- 'dev' | 'meeting' | 'review' | 'planning' | 'other'
    raw_text TEXT NOT NULL,
    summary TEXT,                  -- AI-distilled (populated at report time)
    duration_minutes INTEGER,
    metadata TEXT,                 -- JSON blob for source-specific data
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

## Privacy

- All data stored locally in SQLite
- Only text content sent to Claude API for summarization
- Metadata, file paths, audio files never leave the machine
- `--no-ai` flag available on all commands that use AI
