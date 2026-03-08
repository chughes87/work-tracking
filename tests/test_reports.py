"""Tests for work_tracker.reports."""

from work_tracker.models import WorkEntry
from work_tracker.reports import render_report, render_entries_table, _format_time


def _entry(raw_text="did work", category="dev", timestamp="2026-03-08T10:30:00+00:00", **kw):
    return WorkEntry(
        raw_text=raw_text,
        category=category,
        timestamp=timestamp,
        created_at=timestamp,
        updated_at=timestamp,
        **kw,
    )


class TestRenderReport:
    def test_empty_entries(self):
        md = render_report([], "Test Report")
        assert "# Test Report" in md
        assert "No entries found" in md

    def test_single_entry(self):
        md = render_report([_entry()], "Daily Report")
        assert "# Daily Report" in md
        assert "1 entries" in md
        assert "did work" in md
        assert "10:30" in md

    def test_multiple_categories(self):
        entries = [
            _entry(category="dev"),
            _entry(category="meeting"),
            _entry(category="dev"),
        ]
        md = render_report(entries, "Report")
        assert "dev: 2" in md
        assert "meeting: 1" in md

    def test_single_category_no_breakdown(self):
        entries = [_entry(category="dev"), _entry(category="dev")]
        md = render_report(entries, "Report")
        assert "Categories:" not in md

    def test_duration_shown(self):
        md = render_report([_entry(duration_minutes=45)], "Report")
        assert "(45m)" in md

    def test_no_duration_no_parens(self):
        md = render_report([_entry()], "Report")
        assert "(m)" not in md

    def test_summary_preferred_over_raw(self):
        md = render_report([_entry(summary="AI summary")], "Report")
        assert "AI summary" in md

    def test_entries_section_present(self):
        md = render_report([_entry()], "Report")
        assert "## Entries" in md


class TestRenderEntriesTable:
    def test_returns_dicts(self):
        rows = render_entries_table([_entry()])
        assert len(rows) == 1
        row = rows[0]
        assert "id" in row
        assert "time" in row
        assert "category" in row
        assert "source" in row
        assert "text" in row

    def test_id_truncated(self):
        entry = _entry()
        rows = render_entries_table([entry])
        assert rows[0]["id"] == entry.id[:8]

    def test_text_truncated_at_60(self):
        long_text = "x" * 100
        rows = render_entries_table([_entry(raw_text=long_text)])
        assert len(rows[0]["text"]) == 60

    def test_summary_preferred(self):
        rows = render_entries_table([_entry(summary="short summary")])
        assert rows[0]["text"] == "short summary"


class TestFormatTime:
    def test_iso_format(self):
        assert _format_time("2026-03-08T14:30:00+00:00") == "14:30"

    def test_invalid_returns_raw(self):
        assert _format_time("not-a-date") == "not-a-date"

    def test_none_returns_none(self):
        assert _format_time(None) is None  # type: ignore
