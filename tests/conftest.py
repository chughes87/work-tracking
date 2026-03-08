"""Shared fixtures for work-tracker tests."""

import os

import psycopg2
import pytest

from work_tracker.models import WorkEntry


TEST_DSN = os.environ.get("TEST_DATABASE_URL", "dbname=work_tracker_test port=5433")


@pytest.fixture
def test_db():
    """Provide a clean PostgreSQL test database, dropping entries table between tests."""
    conn = psycopg2.connect(TEST_DSN)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS entries")
    conn.close()
    return TEST_DSN


@pytest.fixture
def tmp_config_dir(tmp_path, monkeypatch):
    """Set XDG dirs to temp paths and DATABASE_URL to test database."""
    config_home = tmp_path / "config"
    config_home.mkdir()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    monkeypatch.setenv("DATABASE_URL", TEST_DSN)
    # Clean the test database
    conn = psycopg2.connect(TEST_DSN)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS entries")
    conn.close()
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
