# work-trakcing

A small app for tracking what I do day to day.

## Install

```bash
git clone git@github.com:chughes87/work-trakcing.git
cd work-trakcing
pip install -e .
```

## Quick Start

```bash
# Log what you're working on
wt log "Fixed auth bug in login flow"

# Log with a category and duration
wt log -c dev "Refactored database queries" -d 45
wt log -c meeting "Sprint planning" -d 60

# Interactive mode (prompts you for text)
wt log
```

## Commands

### `wt log [TEXT]`

Log a work entry. Pass text inline or omit it for an interactive prompt.

```bash
wt log "Reviewed PR #42"
wt log -c review "Reviewed PR #42"    # set category
wt log -d 30 "Paired on API design"   # set duration in minutes
```

**Categories:** `dev`, `meeting`, `review`, `planning`, `other`

### `wt entries`

List recent entries in a table.

```bash
wt entries                       # show all (up to 50)
wt entries -d 2026-03-08         # filter by date
wt entries -c dev                # filter by category
wt entries -n 10                 # limit to 10 entries
```

### `wt edit <ID>`

Edit an entry by its ID prefix (the 8-char short ID shown in `wt entries`).

```bash
wt edit a1b2c3d4 -t "Updated description"
wt edit a1b2c3d4 -c meeting
```

### `wt delete <ID>`

Delete an entry by its ID prefix.

```bash
wt delete a1b2c3d4
```

### `wt report [PERIOD]`

Generate a markdown report for a time period.

```bash
wt report today              # default
wt report yesterday
wt report week               # current week (Mon–Sun)
wt report today --no-ai      # skip AI summarization
```

### `wt config`

View or update configuration.

```bash
wt config                              # show current config
wt config set default_category dev     # change default category
wt config set ai.model claude-sonnet-4-20250514
wt config set ai.enabled false
```

## Configuration

Config lives at `~/.config/work-tracker/config.toml`. Data is stored in `~/.local/share/work-tracker/work-tracker.db`.

| Key | Default | Description |
|-----|---------|-------------|
| `default_category` | `other` | Category used when none is specified |
| `db_path` | `~/.local/share/work-tracker/work-tracker.db` | Database location |
| `ai.enabled` | `true` | Use Claude API for report summaries |
| `ai.model` | `claude-sonnet-4-20250514` | Claude model for summarization |
| `reminder.enabled` | `false` | Periodic logging reminders |
| `reminder.interval_minutes` | `90` | Reminder interval |

## Running Tests

```bash
pip install -e ".[dev]"
pytest
```
