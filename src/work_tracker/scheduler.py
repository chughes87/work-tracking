"""Cron-based reminder system for work-tracker."""

from __future__ import annotations

import shutil
import subprocess
from datetime import datetime, timedelta

from work_tracker.config import load_config
from work_tracker.db import query_entries

CRON_MARKER = "# work-tracker-reminder"


def _wt_path() -> str:
    """Return absolute path to the wt binary."""
    path = shutil.which("wt")
    if path:
        return path
    # Fallback to common location
    from pathlib import Path
    fallback = Path.home() / ".local" / "bin" / "wt"
    return str(fallback)


def _get_crontab() -> str:
    """Read current user crontab."""
    try:
        result = subprocess.run(
            ["crontab", "-l"], capture_output=True, text=True
        )
        if result.returncode != 0:
            return ""
        return result.stdout
    except FileNotFoundError:
        return ""


def _set_crontab(content: str) -> None:
    """Write user crontab."""
    subprocess.run(
        ["crontab", "-"], input=content, text=True, check=True
    )


def _interval_to_cron(interval_minutes: int) -> str:
    """Convert an interval in minutes to a cron schedule expression."""
    if interval_minutes <= 59:
        return f"*/{interval_minutes} * * * *"
    # For longer intervals, pick specific minutes/hours
    # e.g. 90 min -> run at 0:00, 1:30, 3:00, 4:30, ... => "0,30 */3 * * *" won't work cleanly
    # Simplest: run every N hours if divisible, otherwise approximate with hours
    hours = interval_minutes // 60
    remaining = interval_minutes % 60
    if remaining == 0 and hours <= 23:
        return f"0 */{hours} * * *"
    # For odd intervals like 90, use every hour and let should_notify() handle the gating
    return "0 * * * *"


def install_reminder(interval_minutes: int = 90) -> None:
    """Install a crontab entry that fires every interval_minutes."""
    remove_reminder()  # clean any existing entry first

    wt = _wt_path()
    cron_schedule = _interval_to_cron(interval_minutes)
    cron_line = f"{cron_schedule} {wt} remind notify {CRON_MARKER}"

    existing = _get_crontab().rstrip("\n")
    new_crontab = f"{existing}\n{cron_line}\n" if existing else f"{cron_line}\n"
    _set_crontab(new_crontab)


def remove_reminder() -> None:
    """Remove the work-tracker crontab entry."""
    existing = _get_crontab()
    if CRON_MARKER not in existing:
        return

    lines = [l for l in existing.splitlines() if CRON_MARKER not in l]
    _set_crontab("\n".join(lines) + "\n" if lines else "")


def reminder_status() -> dict:
    """Check if reminder is installed and return details."""
    crontab = _get_crontab()
    for line in crontab.splitlines():
        if CRON_MARKER in line and not line.strip().startswith("#"):
            return {"installed": True, "cron_line": line.strip()}
    return {"installed": False, "cron_line": None}


def should_notify() -> bool:
    """Return True if user hasn't logged anything in the configured interval."""
    cfg = load_config()
    interval = cfg.get("reminder", {}).get("interval_minutes", 90)
    cutoff = (datetime.now().astimezone() - timedelta(minutes=interval)).isoformat()

    entries = query_entries(cfg["database_url"], start=cutoff)
    return len(entries) == 0


def send_notification() -> bool:
    """Send a desktop notification if the user should be reminded."""
    if not should_notify():
        return False

    return _fire_notification()


def _fire_notification(message: str | None = None) -> bool:
    """Send a desktop notification immediately."""
    notify = shutil.which("notify-send")
    if not notify:
        return False

    msg = message or "You haven't logged any work recently. What are you working on?"
    subprocess.run([
        notify, "--app-name=work-tracker",
        "Work Tracker",
        msg,
    ])
    return True


def schedule_oneshot(minutes: int) -> None:
    """Schedule a one-shot reminder N minutes from now using a background process."""
    wt = _wt_path()
    # nohup + disown so it survives the parent shell exiting
    subprocess.Popen(
        ["bash", "-c", f"sleep {minutes * 60} && {wt} remind fire-oneshot"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
