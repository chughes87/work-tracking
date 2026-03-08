"""Tests for work_tracker.models."""

import uuid

from work_tracker.models import CATEGORIES, WorkEntry


class TestWorkEntry:
    def test_defaults(self):
        entry = WorkEntry(raw_text="test")
        assert entry.raw_text == "test"
        assert entry.source == "prompt"
        assert entry.category == "other"
        assert entry.summary is None
        assert entry.duration_minutes is None
        assert entry.metadata is None

    def test_auto_id(self):
        e1 = WorkEntry(raw_text="a")
        e2 = WorkEntry(raw_text="b")
        assert e1.id != e2.id
        uuid.UUID(e1.id)  # validates UUID format

    def test_auto_timestamps(self):
        entry = WorkEntry(raw_text="test")
        assert entry.timestamp is not None
        assert entry.created_at is not None
        assert entry.updated_at is not None

    def test_explicit_fields(self):
        entry = WorkEntry(
            raw_text="reviewed PR",
            source="git",
            category="review",
            duration_minutes=30,
            metadata='{"pr": 42}',
        )
        assert entry.source == "git"
        assert entry.category == "review"
        assert entry.duration_minutes == 30
        assert entry.metadata == '{"pr": 42}'


class TestCategories:
    def test_expected_categories(self):
        assert "dev" in CATEGORIES
        assert "meeting" in CATEGORIES
        assert "review" in CATEGORIES
        assert "planning" in CATEGORIES
        assert "other" in CATEGORIES
        assert len(CATEGORIES) == 5
