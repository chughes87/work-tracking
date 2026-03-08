"""Tests for work_tracker.db."""

import pytest

from work_tracker.db import (
    insert_entry,
    query_entries,
    delete_entry,
    update_entry,
    date_range_for,
    _connect,
)
from work_tracker.models import WorkEntry


class TestInsertAndQuery:
    def test_insert_and_retrieve(self, test_db, sample_entry):
        entry = sample_entry()
        insert_entry(test_db, entry)
        results = query_entries(test_db)
        assert len(results) == 1
        assert results[0].raw_text == "Did some coding"
        assert results[0].id == entry.id

    def test_insert_multiple(self, test_db, sample_entry):
        for i in range(3):
            insert_entry(test_db, sample_entry(raw_text=f"task {i}"))
        assert len(query_entries(test_db)) == 3

    def test_duplicate_id_raises(self, test_db, sample_entry):
        entry = sample_entry()
        insert_entry(test_db, entry)
        with pytest.raises(Exception):
            insert_entry(test_db, entry)


class TestQueryFilters:
    def test_filter_by_category(self, test_db, sample_entry):
        insert_entry(test_db, sample_entry(category="dev"))
        insert_entry(test_db, sample_entry(category="meeting"))
        insert_entry(test_db, sample_entry(category="dev"))
        results = query_entries(test_db, category="dev")
        assert len(results) == 2
        assert all(r.category == "dev" for r in results)

    def test_filter_by_date_range(self, test_db, sample_entry):
        insert_entry(test_db, sample_entry(timestamp="2026-03-07T10:00:00+00:00"))
        insert_entry(test_db, sample_entry(timestamp="2026-03-08T10:00:00+00:00"))
        insert_entry(test_db, sample_entry(timestamp="2026-03-09T10:00:00+00:00"))
        results = query_entries(test_db, start="2026-03-08", end="2026-03-09")
        assert len(results) == 1
        assert "2026-03-08" in results[0].timestamp

    def test_filter_combined(self, test_db, sample_entry):
        insert_entry(test_db, sample_entry(timestamp="2026-03-08T10:00:00+00:00", category="dev"))
        insert_entry(test_db, sample_entry(timestamp="2026-03-08T14:00:00+00:00", category="meeting"))
        insert_entry(test_db, sample_entry(timestamp="2026-03-07T10:00:00+00:00", category="dev"))
        results = query_entries(test_db, start="2026-03-08", end="2026-03-09", category="dev")
        assert len(results) == 1

    def test_limit(self, test_db, sample_entry):
        for i in range(10):
            insert_entry(test_db, sample_entry(raw_text=f"task {i}"))
        assert len(query_entries(test_db, limit=3)) == 3

    def test_ordered_by_timestamp(self, test_db, sample_entry):
        insert_entry(test_db, sample_entry(timestamp="2026-03-08T15:00:00+00:00", raw_text="late"))
        insert_entry(test_db, sample_entry(timestamp="2026-03-08T09:00:00+00:00", raw_text="early"))
        results = query_entries(test_db)
        assert results[0].raw_text == "early"
        assert results[1].raw_text == "late"

    def test_empty_db(self, test_db):
        assert query_entries(test_db) == []


class TestDeleteEntry:
    def test_delete_existing(self, test_db, sample_entry):
        entry = sample_entry()
        insert_entry(test_db, entry)
        assert delete_entry(test_db, entry.id) is True
        assert query_entries(test_db) == []

    def test_delete_nonexistent(self, test_db):
        assert delete_entry(test_db, "nonexistent-id") is False

    def test_delete_only_target(self, test_db, sample_entry):
        e1 = sample_entry(raw_text="keep")
        e2 = sample_entry(raw_text="remove")
        insert_entry(test_db, e1)
        insert_entry(test_db, e2)
        delete_entry(test_db, e2.id)
        results = query_entries(test_db)
        assert len(results) == 1
        assert results[0].raw_text == "keep"


class TestUpdateEntry:
    def test_update_text(self, test_db, sample_entry):
        entry = sample_entry()
        insert_entry(test_db, entry)
        assert update_entry(test_db, entry.id, raw_text="Updated text") is True
        results = query_entries(test_db)
        assert results[0].raw_text == "Updated text"

    def test_update_category(self, test_db, sample_entry):
        entry = sample_entry(category="other")
        insert_entry(test_db, entry)
        update_entry(test_db, entry.id, category="meeting")
        assert query_entries(test_db)[0].category == "meeting"

    def test_update_sets_updated_at(self, test_db, sample_entry):
        entry = sample_entry()
        insert_entry(test_db, entry)
        original_updated = entry.updated_at
        update_entry(test_db, entry.id, raw_text="changed")
        result = query_entries(test_db)[0]
        assert result.updated_at != original_updated

    def test_update_no_fields(self, test_db, sample_entry):
        assert update_entry(test_db, "any-id") is False

    def test_update_nonexistent(self, test_db):
        assert update_entry(test_db, "no-such-id", raw_text="x") is False


class TestDateRangeFor:
    def test_today(self):
        start, end = date_range_for("today")
        assert start < end

    def test_yesterday(self):
        start, end = date_range_for("yesterday")
        assert start < end

    def test_week(self):
        start, end = date_range_for("week")
        assert start < end

    def test_invalid_period(self):
        with pytest.raises(ValueError, match="Unknown period"):
            date_range_for("month")


class TestConnect:
    def test_schema_created(self, test_db):
        conn = _connect(test_db)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = 'entries'"
            )
            assert cur.fetchone() is not None
        conn.close()
