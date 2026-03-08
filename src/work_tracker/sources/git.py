"""Git commit import for work-tracker."""

from __future__ import annotations

import json
import re

try:
    import git
except ImportError:
    git = None  # type: ignore[assignment]

from work_tracker.db import insert_entry, query_entries
from work_tracker.models import WorkEntry

CATEGORY_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("review", re.compile(r"\b(review|code.review|cr|approve)\b", re.I)),
    ("planning", re.compile(r"\b(plan|design|rfc|spec|proposal)\b", re.I)),
    ("meeting", re.compile(r"\b(meeting|sync|standup|retro|1[:\-]1)\b", re.I)),
]


def categorize_commit(message: str) -> str:
    """Categorize a commit message by keyword matching. Default: dev."""
    for category, pattern in CATEGORY_PATTERNS:
        if pattern.search(message):
            return category
    return "dev"


def _get_imported_hashes(dsn: str, start: str | None, end: str | None) -> set[str]:
    """Return set of commit hashes already imported in the given date range."""
    entries = query_entries(dsn, source="git", start=start, end=end)
    hashes = set()
    for e in entries:
        if e.metadata:
            try:
                meta = json.loads(e.metadata)
                if "commit_hash" in meta:
                    hashes.add(meta["commit_hash"])
            except (json.JSONDecodeError, TypeError):
                pass
    return hashes


def import_commits(
    repo_path: str,
    dsn: str,
    *,
    since: str | None = None,
    until: str | None = None,
    author: str | None = None,
    dry_run: bool = False,
) -> dict[str, int]:
    """Import git commits as work entries. Returns counts of imported/skipped."""
    if git is None:
        raise RuntimeError(
            "GitPython not installed. Run: pip install work-tracker[git]"
        )

    try:
        repo = git.Repo(repo_path)
    except git.InvalidGitRepositoryError:
        raise RuntimeError(f"Not a git repository: {repo_path}")

    kwargs: dict = {}
    if since:
        kwargs["since"] = since
    if until:
        kwargs["until"] = until
    if author:
        kwargs["author"] = author

    try:
        commits = list(repo.iter_commits(**kwargs))
    except ValueError:
        return {"imported": 0, "skipped": 0}

    existing_hashes = _get_imported_hashes(dsn, since, until) if not dry_run else set()

    imported = 0
    skipped = 0

    for commit in commits:
        if commit.hexsha in existing_hashes:
            skipped += 1
            continue

        subject = commit.message.strip().split("\n")[0]
        metadata = json.dumps({
            "commit_hash": commit.hexsha,
            "repo": repo_path,
        })

        entry = WorkEntry(
            raw_text=commit.message.strip(),
            source="git",
            category=categorize_commit(commit.message),
            summary=subject,
            metadata=metadata,
            timestamp=commit.authored_datetime.isoformat(),
            created_at=commit.authored_datetime.isoformat(),
        )

        if not dry_run:
            insert_entry(dsn, entry)
        imported += 1

    return {"imported": imported, "skipped": skipped}
