"""Shared fixtures for work-tracker tests."""

import os
import tempfile
from pathlib import Path

import pytest

from work_tracker.models import WorkEntry


@pytest.fixture
def tmp_db(tmp_path):
    """Return a path to a temporary SQLite database."""
    return str(tmp_path / "test.db")


@pytest.fixture
def tmp_config_dir(tmp_path, monkeypatch):
    """Set XDG dirs to temp paths so tests don't touch real config/data."""
    config_home = tmp_path / "config"
    data_home = tmp_path / "data"
    config_home.mkdir()
    data_home.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    monkeypatch.setenv("XDG_DATA_HOME", str(data_home))
    return tmp_path


@pytest.fixture
def sample_entry():
    """Return a factory for WorkEntry with fixed timestamps for predictable tests."""
    def _make(
        raw_text="Did some coding",
        source="prompt",
        category="dev",
        timestamp="2026-03-08T10:00:00+00:00",
        **kwargs,
    ):
        return WorkEntry(
            raw_text=raw_text,
            source=source,
            category=category,
            timestamp=timestamp,
            created_at=timestamp,
            updated_at=timestamp,
            **kwargs,
        )
    return _make
