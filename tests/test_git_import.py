"""Tests for git commit import."""

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from work_tracker.db import insert_entry, query_entries
from work_tracker.models import WorkEntry
from work_tracker.sources.git import categorize_commit, import_commits


class TestCategorizeCommit:
    def test_dev_default(self):
        assert categorize_commit("Fix login bug") == "dev"

    def test_review(self):
        assert categorize_commit("Code review for auth module") == "review"
        assert categorize_commit("Approve PR #42") == "review"

    def test_planning(self):
        assert categorize_commit("Add PLAN.md with roadmap") == "planning"
        assert categorize_commit("RFC: new auth design") == "planning"
        assert categorize_commit("Design spec for API v2") == "planning"

    def test_meeting(self):
        assert categorize_commit("Notes from standup") == "meeting"
        assert categorize_commit("Retro action items") == "meeting"

    def test_case_insensitive(self):
        assert categorize_commit("CODE REVIEW feedback") == "review"


def _mock_commit(hexsha, message, authored_datetime=None):
    commit = MagicMock()
    commit.hexsha = hexsha
    commit.message = message
    commit.authored_datetime = authored_datetime or datetime.now(timezone.utc)
    return commit


class TestImportCommits:
    @patch("work_tracker.sources.git.git")
    def test_dry_run_no_inserts(self, mock_git, test_db):
        repo = MagicMock()
        repo.iter_commits.return_value = [
            _mock_commit("abc123", "Fix bug"),
        ]
        mock_git.Repo.return_value = repo

        result = import_commits(".", test_db, dry_run=True)
        assert result["imported"] == 1
        assert query_entries(test_db) == []

    @patch("work_tracker.sources.git.git")
    def test_imports_commits(self, mock_git, test_db):
        repo = MagicMock()
        repo.iter_commits.return_value = [
            _mock_commit("abc123", "Fix bug"),
            _mock_commit("def456", "Add feature"),
        ]
        mock_git.Repo.return_value = repo

        result = import_commits(".", test_db)
        assert result["imported"] == 2
        entries = query_entries(test_db)
        assert len(entries) == 2
        assert all(e.source == "git" for e in entries)

    @patch("work_tracker.sources.git.git")
    def test_skips_duplicates(self, mock_git, test_db):
        repo = MagicMock()
        commits = [_mock_commit("abc123", "Fix bug")]
        repo.iter_commits.return_value = commits
        mock_git.Repo.return_value = repo

        import_commits(".", test_db)

        repo.iter_commits.return_value = commits
        result = import_commits(".", test_db)
        assert result["imported"] == 0
        assert result["skipped"] == 1

    @patch("work_tracker.sources.git.git")
    def test_commit_metadata(self, mock_git, test_db):
        repo = MagicMock()
        repo.iter_commits.return_value = [
            _mock_commit("abc123def456", "Fix bug"),
        ]
        mock_git.Repo.return_value = repo

        import_commits(".", test_db)
        entry = query_entries(test_db)[0]
        meta = json.loads(entry.metadata)
        assert meta["commit_hash"] == "abc123def456"

    @patch("work_tracker.sources.git.git")
    def test_summary_is_first_line(self, mock_git, test_db):
        repo = MagicMock()
        repo.iter_commits.return_value = [
            _mock_commit("abc123", "First line\n\nDetailed description"),
        ]
        mock_git.Repo.return_value = repo

        import_commits(".", test_db)
        entry = query_entries(test_db)[0]
        assert entry.summary == "First line"
        assert "Detailed description" in entry.raw_text

    @patch("work_tracker.sources.git.git")
    def test_auto_categorization(self, mock_git, test_db):
        repo = MagicMock()
        repo.iter_commits.return_value = [
            _mock_commit("aaa", "Code review for PR"),
            _mock_commit("bbb", "Fix login bug"),
            _mock_commit("ccc", "Design spec for new API"),
        ]
        mock_git.Repo.return_value = repo

        import_commits(".", test_db)
        entries = query_entries(test_db)
        cats = {e.summary: e.category for e in entries}
        assert cats["Code review for PR"] == "review"
        assert cats["Fix login bug"] == "dev"
        assert cats["Design spec for new API"] == "planning"

    @patch("work_tracker.sources.git.git")
    def test_empty_repo(self, mock_git, test_db):
        repo = MagicMock()
        repo.iter_commits.side_effect = ValueError("empty repo")
        mock_git.Repo.return_value = repo

        result = import_commits(".", test_db)
        assert result["imported"] == 0

    @patch("work_tracker.sources.git.git")
    def test_invalid_repo(self, mock_git, test_db):
        import git as real_git
        mock_git.InvalidGitRepositoryError = real_git.InvalidGitRepositoryError
        mock_git.Repo.side_effect = real_git.InvalidGitRepositoryError("not a repo")

        with pytest.raises(RuntimeError, match="Not a git repository"):
            import_commits("/fake/path", test_db)
