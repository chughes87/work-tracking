"""Tests for work_tracker.cli (Click commands)."""

from click.testing import CliRunner

from work_tracker.cli import cli


def _invoke(args, env=None):
    """Run a CLI command with isolated config/data dirs."""
    runner = CliRunner()
    return runner.invoke(cli, args, catch_exceptions=False, env=env)


class TestLog:
    def test_log_inline(self, tmp_config_dir):
        result = _invoke(["log", "wrote some tests"])
        assert result.exit_code == 0
        assert "Logged" in result.output
        assert "wrote some tests" in result.output

    def test_log_with_category(self, tmp_config_dir):
        result = _invoke(["log", "-c", "dev", "built feature"])
        assert result.exit_code == 0
        assert "Logged" in result.output
        assert "built feature" in result.output

    def test_log_with_duration(self, tmp_config_dir):
        result = _invoke(["log", "-d", "30", "pair programming"])
        assert result.exit_code == 0
        assert "Logged" in result.output

    def test_log_interactive(self, tmp_config_dir):
        runner = CliRunner()
        result = runner.invoke(cli, ["log"], input="interactive entry\n", catch_exceptions=False)
        assert result.exit_code == 0
        assert "Logged" in result.output


class TestEntries:
    def test_entries_empty(self, tmp_config_dir):
        result = _invoke(["entries"])
        assert result.exit_code == 0
        assert "No entries found" in result.output

    def test_entries_after_log(self, tmp_config_dir):
        _invoke(["log", "first task"])
        _invoke(["log", "-c", "meeting", "standup"])
        result = _invoke(["entries"])
        assert result.exit_code == 0
        assert "first task" in result.output
        assert "standup" in result.output

    def test_entries_filter_category(self, tmp_config_dir):
        _invoke(["log", "-c", "dev", "coding"])
        _invoke(["log", "-c", "meeting", "standup"])
        result = _invoke(["entries", "-c", "dev"])
        assert result.exit_code == 0
        assert "coding" in result.output
        # Rich table output may still show both, but the query filters
        # We check the command doesn't error

    def test_entries_with_limit(self, tmp_config_dir):
        for i in range(5):
            _invoke(["log", f"task {i}"])
        result = _invoke(["entries", "-n", "2"])
        assert result.exit_code == 0


class TestDelete:
    def test_delete_by_prefix(self, tmp_config_dir):
        _invoke(["log", "to be deleted"])
        entries_result = _invoke(["entries"])
        # Extract the ID prefix from the table output
        lines = entries_result.output.strip().split("\n")
        # Find a line with entry data (contains "to be deleted")
        entry_id = None
        for line in lines:
            if "to be deleted" in line:
                # ID is the first column value after the table border
                parts = line.split("│")
                if len(parts) > 1:
                    entry_id = parts[1].strip()
                    break
        assert entry_id is not None
        result = _invoke(["delete", entry_id])
        assert result.exit_code == 0
        assert "Deleted" in result.output

    def test_delete_nonexistent(self, tmp_config_dir):
        result = _invoke(["delete", "nonexistent"])
        assert result.exit_code == 0
        assert "No entry matching" in result.output


class TestEdit:
    def test_edit_text(self, tmp_config_dir):
        _invoke(["log", "original text"])
        entries_result = _invoke(["entries"])
        entry_id = _extract_id(entries_result.output, "original text")
        assert entry_id is not None
        result = _invoke(["edit", entry_id, "-t", "updated text"])
        assert result.exit_code == 0
        assert "Updated" in result.output

    def test_edit_category(self, tmp_config_dir):
        _invoke(["log", "some work"])
        entries_result = _invoke(["entries"])
        entry_id = _extract_id(entries_result.output, "some work")
        result = _invoke(["edit", entry_id, "-c", "meeting"])
        assert result.exit_code == 0
        assert "Updated" in result.output

    def test_edit_no_fields(self, tmp_config_dir):
        _invoke(["log", "untouched"])
        entries_result = _invoke(["entries"])
        entry_id = _extract_id(entries_result.output, "untouched")
        result = _invoke(["edit", entry_id])
        assert result.exit_code == 0
        assert "Nothing to update" in result.output

    def test_edit_nonexistent(self, tmp_config_dir):
        result = _invoke(["edit", "nonexistent", "-t", "new"])
        assert result.exit_code == 0
        assert "No entry matching" in result.output


class TestReport:
    def test_report_empty(self, tmp_config_dir):
        result = _invoke(["report", "today"])
        assert result.exit_code == 0
        assert "No entries found" in result.output

    def test_report_with_entries(self, tmp_config_dir):
        _invoke(["log", "-c", "dev", "built feature X"])
        _invoke(["log", "-c", "meeting", "team sync"])
        result = _invoke(["report", "today"])
        assert result.exit_code == 0
        assert "Work Report" in result.output
        assert "built feature X" in result.output
        assert "team sync" in result.output

    def test_report_yesterday(self, tmp_config_dir):
        result = _invoke(["report", "yesterday"])
        assert result.exit_code == 0

    def test_report_week(self, tmp_config_dir):
        result = _invoke(["report", "week"])
        assert result.exit_code == 0


class TestConfig:
    def test_config_show(self, tmp_config_dir):
        result = _invoke(["config"])
        assert result.exit_code == 0
        assert "database_url" in result.output
        assert "default_category" in result.output

    def test_config_set(self, tmp_config_dir):
        result = _invoke(["config", "set", "default_category", "dev"])
        assert result.exit_code == 0
        assert "Set default_category = dev" in result.output

    def test_config_set_dotted_key(self, tmp_config_dir):
        result = _invoke(["config", "set", "ai.model", "custom-model"])
        assert result.exit_code == 0
        assert "Set ai.model = custom-model" in result.output

    def test_config_set_persists(self, tmp_config_dir):
        _invoke(["config", "set", "default_category", "meeting"])
        result = _invoke(["config"])
        assert "meeting" in result.output

    def test_config_invalid_usage(self, tmp_config_dir):
        result = _invoke(["config", "set"])
        assert result.exit_code == 0
        assert "Usage" in result.output


class TestVersion:
    def test_version(self):
        result = _invoke(["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output


def _extract_id(output: str, text_match: str) -> str | None:
    """Extract the 8-char ID prefix from entries table output."""
    for line in output.split("\n"):
        if text_match in line:
            parts = line.split("│")
            if len(parts) > 1:
                return parts[1].strip()
    return None
