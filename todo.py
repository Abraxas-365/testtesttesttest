"""Todo model for the todo app.

Defines the :class:`Todo` dataclass and supporting helpers for priorities
and (de)serialization to/from plain dicts suitable for JSON storage.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

# Valid priority levels, ordered from most to least urgent.
PRIORITIES = ("high", "medium", "low")


def _now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    """Return a new random UUID4 hex string."""
    return uuid.uuid4().hex


@dataclass
class Todo:
    """A single todo item.

    Attributes:
        id: Unique identifier (UUID4 hex string).
        title: Human readable description of the task.
        done: Whether the task is complete.
        priority: One of ``high``, ``medium`` or ``low``.
        created_at: ISO 8601 datetime string of when the todo was created.
        due_date: Optional ISO 8601 date string (``YYYY-MM-DD``).
    """

    title: str
    priority: str = "medium"
    done: bool = False
    due_date: Optional[str] = None
    id: str = field(default_factory=_new_id)
    created_at: str = field(default_factory=_now_iso)

    def __post_init__(self) -> None:
        self.title = self.title.strip()
        if not self.title:
            raise ValueError("title must not be empty")
        if self.priority not in PRIORITIES:
            raise ValueError(
                f"priority must be one of {PRIORITIES!r}, got {self.priority!r}"
            )

    def to_dict(self) -> dict:
        """Serialize the todo to a plain dict for JSON storage."""
        return {
            "id": self.id,
            "title": self.title,
            "done": self.done,
            "priority": self.priority,
            "created_at": self.created_at,
            "due_date": self.due_date,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Todo":
        """Reconstruct a :class:`Todo` from a stored dict."""
        return cls(
            id=data["id"],
            title=data["title"],
            done=data.get("done", False),
            priority=data.get("priority", "medium"),
            created_at=data.get("created_at", _now_iso()),
            due_date=data.get("due_date"),
        )
