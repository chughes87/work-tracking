"""Click CLI for work-tracker."""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from work_tracker import __version__
from work_tracker.config import load_config, save_config, config_path
from work_tracker.db import (
    insert_entry,
    query_entries,
    delete_entry,
    update_entry,
    date_range_for,
)
from work_tracker.models import CATEGORIES, WorkEntry
from work_tracker.reports import render_report, render_entries_table

console = Console()


@click.group()
@click.version_option(version=__version__)
@click.pass_context
def cli(ctx):
    """wt — capture your work, generate reports."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = load_config()


@cli.command()
@click.argument("text", nargs=-1)
@click.option(
    "--category", "-c",
    type=click.Choice(CATEGORIES, case_sensitive=False),
    default=None,
    help="Entry category.",
)
@click.option("--duration", "-d", type=int, default=None, help="Duration in minutes.")
@click.pass_context
def log(ctx, text: tuple[str, ...], category: str | None, duration: int | None):
    """Log a work entry. Provide text inline or omit for interactive prompt."""
    cfg = ctx.obj["config"]
    raw = " ".join(text) if text else click.prompt("What did you work on?")

    if not raw.strip():
        console.print("[red]Empty entry, nothing saved.[/red]")
        return

    cat = category or cfg.get("default_category", "other")
    entry = WorkEntry(raw_text=raw.strip(), category=cat, duration_minutes=duration)
    insert_entry(cfg["database_url"], entry)
    console.print(f"[green]Logged:[/green] {entry.raw_text} [dim][{cat}][/dim]")


@cli.command()
@click.option("--date", "-d", "date_str", default=None, help="Date filter (YYYY-MM-DD).")
@click.option(
    "--category", "-c",
    type=click.Choice(CATEGORIES, case_sensitive=False),
    default=None,
)
@click.option("--limit", "-n", type=int, default=50)
@click.pass_context
def entries(ctx, date_str: str | None, category: str | None, limit: int):
    """List recent work entries."""
    cfg = ctx.obj["config"]
    start, end = None, None

    if date_str:
        start = date_str
        from datetime import date, timedelta

        d = date.fromisoformat(date_str)
        end = (d + timedelta(days=1)).isoformat()

    items = query_entries(
        cfg["database_url"], start=start, end=end, category=category, limit=limit
    )

    if not items:
        console.print("[dim]No entries found.[/dim]")
        return

    table = Table(show_header=True)
    table.add_column("ID", style="dim", width=8)
    table.add_column("Time", width=5)
    table.add_column("Cat", width=8)
    table.add_column("Source", width=6)
    table.add_column("Text")

    for row in render_entries_table(items):
        table.add_row(row["id"], row["time"], row["category"], row["source"], row["text"])

    console.print(table)


@cli.command()
@click.argument("entry_id")
@click.pass_context
def delete(ctx, entry_id: str):
    """Delete a work entry by ID (or prefix)."""
    cfg = ctx.obj["config"]
    # Support prefix matching
    all_entries = query_entries(cfg["database_url"])
    matches = [e for e in all_entries if e.id.startswith(entry_id)]

    if len(matches) == 0:
        console.print(f"[red]No entry matching '{entry_id}'[/red]")
    elif len(matches) > 1:
        console.print(f"[red]Ambiguous prefix '{entry_id}', {len(matches)} matches[/red]")
    else:
        delete_entry(cfg["database_url"], matches[0].id)
        console.print(f"[green]Deleted entry {matches[0].id[:8]}[/green]")


@cli.command()
@click.argument("entry_id")
@click.option("--text", "-t", default=None, help="New text.")
@click.option(
    "--category", "-c",
    type=click.Choice(CATEGORIES, case_sensitive=False),
    default=None,
)
@click.pass_context
def edit(ctx, entry_id: str, text: str | None, category: str | None):
    """Edit a work entry by ID (or prefix)."""
    cfg = ctx.obj["config"]
    all_entries = query_entries(cfg["database_url"])
    matches = [e for e in all_entries if e.id.startswith(entry_id)]

    if len(matches) == 0:
        console.print(f"[red]No entry matching '{entry_id}'[/red]")
        return
    if len(matches) > 1:
        console.print(f"[red]Ambiguous prefix '{entry_id}', {len(matches)} matches[/red]")
        return

    fields = {}
    if text:
        fields["raw_text"] = text
    if category:
        fields["category"] = category

    if not fields:
        console.print("[dim]Nothing to update. Use --text or --category.[/dim]")
        return

    update_entry(cfg["database_url"], matches[0].id, **fields)
    console.print(f"[green]Updated entry {matches[0].id[:8]}[/green]")


@cli.command()
@click.argument("period", type=click.Choice(["today", "yesterday", "week"]), default="today")
@click.option("--format", "fmt", type=click.Choice(["md", "text"]), default="md")
@click.pass_context
def report(ctx, period: str, fmt: str):
    """Generate a report for a time period."""
    cfg = ctx.obj["config"]
    start, end = date_range_for(period)
    items = query_entries(cfg["database_url"], start=start, end=end)

    title = f"Work Report — {period.capitalize()}"
    md = render_report(items, title)
    console.print(md)


@cli.command()
@click.argument("args", nargs=-1)
@click.pass_context
def config(ctx, args: tuple[str, ...]):
    """Show or set configuration. Usage: wt config [set key value]"""
    cfg = ctx.obj["config"]

    if not args:
        console.print(f"[dim]Config file:[/dim] {config_path()}")
        _print_config(cfg)
        return

    if args[0] == "set" and len(args) >= 3:
        key, value = args[1], args[2]
        # Handle dotted keys like ai.model
        parts = key.split(".")
        target = cfg
        for part in parts[:-1]:
            if part not in target or not isinstance(target[part], dict):
                target[part] = {}
            target = target[part]

        # Type coercion
        if value.lower() in ("true", "false"):
            value = value.lower() == "true"
        elif value.isdigit():
            value = int(value)

        target[parts[-1]] = value
        save_config(cfg)
        console.print(f"[green]Set {key} = {value}[/green]")
    else:
        console.print("[red]Usage: wt config set <key> <value>[/red]")


def _print_config(cfg: dict, indent: int = 0) -> None:
    prefix = "  " * indent
    for k, v in cfg.items():
        if isinstance(v, dict):
            console.print(f"{prefix}[bold]{k}:[/bold]")
            _print_config(v, indent + 1)
        else:
            console.print(f"{prefix}{k} = {v}")
