"""Tests for reminder scheduler."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

import pytest

from work_tracker.db import insert_entry
from work_tracker.models import WorkEntry
from work_tracker.scheduler import (
    _interval_to_cron,
    install_reminder,
    remove_reminder,
    reminder_status,
    should_notify,
    send_notification,
    CRON_MARKER,
)


class TestIntervalToCron:
    def test_short_interval(self):
        assert _interval_to_cron(10) == "*/10 * * * *"
        assert _interval_to_cron(15) == "*/15 * * * *"
        assert _interval_to_cron(30) == "*/30 * * * *"

    def test_hourly(self):
        assert _interval_to_cron(60) == "0 */1 * * *"
        assert _interval_to_cron(120) == "0 */2 * * *"

    def test_odd_interval_falls_back_to_hourly(self):
        # 90 min can't be expressed cleanly, falls back to hourly
        assert _interval_to_cron(90) == "0 * * * *"


class TestCrontabManagement:
    @patch("work_tracker.scheduler._set_crontab")
    @patch("work_tracker.scheduler._get_crontab", return_value="")
    @patch("work_tracker.scheduler._wt_path", return_value="/usr/bin/wt")
    def test_install_adds_entry(self, mock_path, mock_get, mock_set):
        install_reminder(15)
        written = mock_set.call_args[0][0]
        assert CRON_MARKER in written
        assert "*/15" in written
        assert "/usr/bin/wt remind notify" in written

    @patch("work_tracker.scheduler._set_crontab")
    @patch("work_tracker.scheduler._get_crontab", return_value="")
    @patch("work_tracker.scheduler._wt_path", return_value="/usr/bin/wt")
    def test_install_preserves_existing(self, mock_path, mock_get, mock_set):
        mock_get.return_value = "0 * * * * /some/other/job\n"
        install_reminder(30)
        written = mock_set.call_args[0][0]
        assert "/some/other/job" in written
        assert CRON_MARKER in written

    @patch("work_tracker.scheduler._set_crontab")
    @patch("work_tracker.scheduler._get_crontab")
    def test_remove_cleans_entry(self, mock_get, mock_set):
        mock_get.return_value = f"0 * * * * /some/job\n*/15 * * * * /usr/bin/wt remind notify {CRON_MARKER}\n"
        remove_reminder()
        written = mock_set.call_args[0][0]
        assert CRON_MARKER not in written
        assert "/some/job" in written

    @patch("work_tracker.scheduler._set_crontab")
    @patch("work_tracker.scheduler._get_crontab", return_value="0 * * * * /some/job\n")
    def test_remove_noop_when_not_installed(self, mock_get, mock_set):
        remove_reminder()
        mock_set.assert_not_called()

    @patch("work_tracker.scheduler._get_crontab")
    def test_status_installed(self, mock_get):
        mock_get.return_value = f"*/15 * * * * /usr/bin/wt remind notify {CRON_MARKER}\n"
        info = reminder_status()
        assert info["installed"] is True
        assert "*/15" in info["cron_line"]

    @patch("work_tracker.scheduler._get_crontab", return_value="")
    def test_status_not_installed(self, mock_get):
        info = reminder_status()
        assert info["installed"] is False


class TestShouldNotify:
    @patch("work_tracker.scheduler.load_config")
    @patch("work_tracker.scheduler.query_entries", return_value=[])
    def test_notifies_when_no_recent_entries(self, mock_query, mock_config):
        mock_config.return_value = {
            "database_url": "test",
            "reminder": {"interval_minutes": 15},
        }
        assert should_notify() is True

    @patch("work_tracker.scheduler.load_config")
    @patch("work_tracker.scheduler.query_entries")
    def test_skips_when_recent_entries(self, mock_query, mock_config):
        mock_config.return_value = {
            "database_url": "test",
            "reminder": {"interval_minutes": 15},
        }
        mock_query.return_value = [MagicMock()]
        assert should_notify() is False


class TestSendNotification:
    @patch("work_tracker.scheduler.should_notify", return_value=False)
    def test_no_notification_when_not_needed(self, mock_should):
        assert send_notification() is False

    @patch("subprocess.run")
    @patch("work_tracker.scheduler.shutil.which", return_value="/usr/bin/notify-send")
    @patch("work_tracker.scheduler.should_notify", return_value=True)
    def test_sends_notification(self, mock_should, mock_which, mock_run):
        assert send_notification() is True
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "notify-send" in args[0]

    @patch("work_tracker.scheduler._fire_notification", return_value=False)
    @patch("work_tracker.scheduler.should_notify", return_value=True)
    def test_no_notification_without_notifysend(self, mock_should, mock_fire):
        assert send_notification() is False
