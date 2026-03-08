"""PostgreSQL storage for work-tracker."""

from __future__ import annotations

import psycopg2
import psycopg2.extras
from datetime import date, datetime, timedelta

from work_tracker.models import WorkEntry


SCHEMA = """\
CREATE TABLE IF NOT EXISTS entries (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    source TEXT NOT NULL,
    category TEXT,
    raw_text TEXT NOT NULL,
    summary TEXT,
    duration_minutes INTEGER,
    metadata TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def _connect(dsn: str) -> psycopg2.extensions.connection:
    conn = psycopg2.connect(dsn)
    with conn.cursor() as cur:
        cur.execute(SCHEMA)
    conn.commit()
    return conn


def insert_entry(dsn: str, entry: WorkEntry) -> None:
    conn = _connect(dsn)
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO entries
               (id, timestamp, source, category, raw_text, summary,
                duration_minutes, metadata, created_at, updated_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                entry.id,
                entry.timestamp,
                entry.source,
                entry.category,
                entry.raw_text,
                entry.summary,
                entry.duration_minutes,
                entry.metadata,
                entry.created_at,
                entry.updated_at,
            ),
        )
    conn.commit()
    conn.close()


def query_entries(
    dsn: str,
    *,
    start: str | None = None,
    end: str | None = None,
    category: str | None = None,
    limit: int | None = None,
) -> list[WorkEntry]:
    conn = _connect(dsn)
    clauses = []
    params: list = []

    if start:
        clauses.append("timestamp >= %s")
        params.append(start)
    if end:
        clauses.append("timestamp < %s")
        params.append(end)
    if category:
        clauses.append("category = %s")
        params.append(category)

    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    order = " ORDER BY timestamp ASC"
    lim = f" LIMIT {limit}" if limit else ""

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(f"SELECT * FROM entries{where}{order}{lim}", params)
        rows = cur.fetchall()
    conn.close()

    return [
        WorkEntry(
            id=r["id"],
            timestamp=r["timestamp"],
            source=r["source"],
            category=r["category"],
            raw_text=r["raw_text"],
            summary=r["summary"],
            duration_minutes=r["duration_minutes"],
            metadata=r["metadata"],
            created_at=r["created_at"],
            updated_at=r["updated_at"],
        )
        for r in rows
    ]


def delete_entry(dsn: str, entry_id: str) -> bool:
    conn = _connect(dsn)
    with conn.cursor() as cur:
        cur.execute("DELETE FROM entries WHERE id = %s", (entry_id,))
        rowcount = cur.rowcount
    conn.commit()
    conn.close()
    return rowcount > 0


def update_entry(dsn: str, entry_id: str, **fields) -> bool:
    if not fields:
        return False
    fields["updated_at"] = datetime.now().astimezone().isoformat()
    set_clause = ", ".join(f"{k} = %s" for k in fields)
    vals = list(fields.values()) + [entry_id]
    conn = _connect(dsn)
    with conn.cursor() as cur:
        cur.execute(f"UPDATE entries SET {set_clause} WHERE id = %s", vals)
        rowcount = cur.rowcount
    conn.commit()
    conn.close()
    return rowcount > 0


def date_range_for(period: str) -> tuple[str, str]:
    """Return (start_iso, end_iso) for 'today', 'yesterday', or 'week'."""
    today = date.today()
    if period == "today":
        start = today
        end = today + timedelta(days=1)
    elif period == "yesterday":
        start = today - timedelta(days=1)
        end = today
    elif period == "week":
        start = today - timedelta(days=today.weekday())  # Monday
        end = start + timedelta(days=7)
    else:
        raise ValueError(f"Unknown period: {period}")
    return start.isoformat(), end.isoformat()
