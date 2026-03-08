"""Data models for work-tracker."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime


CATEGORIES = ("dev", "meeting", "review", "planning", "other")


@dataclass
class WorkEntry:
    raw_text: str
    source: str = "prompt"
    category: str = "other"
    summary: str | None = None
    duration_minutes: int | None = None
    metadata: str | None = None  # JSON string
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now().astimezone().isoformat())
    created_at: str = field(default_factory=lambda: datetime.now().astimezone().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().astimezone().isoformat())
