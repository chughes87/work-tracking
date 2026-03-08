"""Markdown report generation for work-tracker."""

from __future__ import annotations

from datetime import datetime

from work_tracker.models import WorkEntry


def render_report(entries: list[WorkEntry], title: str) -> str:
    """Render entries as a chronological markdown report."""
    if not entries:
        return f"# {title}\n\nNo entries found for this period.\n"

    lines = [f"# {title}", ""]

    # Group by category
    by_category: dict[str, list[WorkEntry]] = {}
    for e in entries:
        cat = e.category or "other"
        by_category.setdefault(cat, []).append(e)

    # Summary counts
    lines.append(f"**{len(entries)} entries**")
    if len(by_category) > 1:
        parts = [f"{cat}: {len(items)}" for cat, items in sorted(by_category.items())]
        lines.append(f"Categories: {', '.join(parts)}")
    lines.append("")

    # Chronological listing
    lines.append("## Entries")
    lines.append("")
    for entry in entries:
        ts = _format_time(entry.timestamp)
        cat_tag = f" [{entry.category}]" if entry.category else ""
        text = entry.summary or entry.raw_text
        duration = f" ({entry.duration_minutes}m)" if entry.duration_minutes else ""
        lines.append(f"- **{ts}**{cat_tag}{duration} — {text}")

    lines.append("")
    return "\n".join(lines)


def render_entries_table(entries: list[WorkEntry]) -> list[dict]:
    """Return entries as dicts suitable for Rich table rendering."""
    return [
        {
            "id": e.id[:8],
            "time": _format_time(e.timestamp),
            "category": e.category or "",
            "source": e.source,
            "text": (e.summary or e.raw_text)[:60],
        }
        for e in entries
    ]


def _format_time(iso_str: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%H:%M")
    except (ValueError, TypeError):
        return iso_str
