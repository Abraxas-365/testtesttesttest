"""Filtering, sorting, search and statistics helpers for the todo app.

All functions in this module are pure: they take an iterable of
:class:`~todo.Todo` objects and return new lists / data structures without
mutating their inputs or touching the filesystem. This keeps them trivial to
unit test in isolation from the :class:`~store.Store`.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Iterable, List, Optional

from todo import PRIORITIES, Todo

# Status filters understood by :func:`filter_todos`.
STATUS_FILTERS = ("all", "done", "pending")

# Sort keys understood by :func:`sort_todos`.
SORT_KEYS = ("priority", "due", "created")

# Lower number == higher urgency, so ``sorted`` puts high priority first.
_PRIORITY_RANK = {name: rank for rank, name in enumerate(PRIORITIES)}


# -- filtering -------------------------------------------------------------
def filter_todos(
    todos: Iterable[Todo],
    *,
    status: str = "all",
    priority: Optional[str] = None,
) -> List[Todo]:
    """Return todos matching the given ``status`` and ``priority``.

    Args:
        todos: The todos to filter.
        status: One of ``all``, ``done`` or ``pending``.
        priority: If given, keep only todos with this priority.

    Raises:
        ValueError: if ``status`` or ``priority`` is not recognised.
    """
    if status not in STATUS_FILTERS:
        raise ValueError(
            f"status must be one of {STATUS_FILTERS!r}, got {status!r}"
        )
    if priority is not None and priority not in PRIORITIES:
        raise ValueError(
            f"priority must be one of {PRIORITIES!r}, got {priority!r}"
        )

    result = list(todos)
    if status == "done":
        result = [t for t in result if t.done]
    elif status == "pending":
        result = [t for t in result if not t.done]
    if priority is not None:
        result = [t for t in result if t.priority == priority]
    return result


# -- sorting ---------------------------------------------------------------
def sort_todos(todos: Iterable[Todo], key: str) -> List[Todo]:
    """Return a new list of ``todos`` sorted by ``key``.

    - ``priority``: high priority first, then medium, then low.
    - ``due``: soonest due date first; todos with no due date sort last.
    - ``created``: oldest created first.

    Raises:
        ValueError: if ``key`` is not a recognised sort key.
    """
    if key not in SORT_KEYS:
        raise ValueError(f"sort key must be one of {SORT_KEYS!r}, got {key!r}")

    items = list(todos)
    if key == "priority":
        return sorted(
            items, key=lambda t: _PRIORITY_RANK.get(t.priority, len(PRIORITIES))
        )
    if key == "due":
        # Todos without a due date sort after those with one. We use a tuple
        # (has_no_date, date_or_empty) so the boolean dominates the ordering.
        return sorted(
            items,
            key=lambda t: (t.due_date is None, t.due_date or ""),
        )
    # key == "created"
    return sorted(items, key=lambda t: t.created_at)


# -- search ----------------------------------------------------------------
def search_todos(todos: Iterable[Todo], query: str) -> List[Todo]:
    """Return todos whose title contains ``query`` (case-insensitive)."""
    needle = query.strip().lower()
    if not needle:
        return list(todos)
    return [t for t in todos if needle in t.title.lower()]


# -- statistics ------------------------------------------------------------
def _parse_due(due_date: Optional[str]) -> Optional[date]:
    """Parse an ISO ``YYYY-MM-DD`` (or datetime) string into a ``date``."""
    if not due_date:
        return None
    try:
        return date.fromisoformat(due_date[:10])
    except ValueError:
        try:
            return datetime.fromisoformat(due_date).date()
        except ValueError:
            return None


def is_overdue(todo: Todo, today: Optional[date] = None) -> bool:
    """Return True if ``todo`` is not done and its due date is in the past."""
    if todo.done:
        return False
    due = _parse_due(todo.due_date)
    if due is None:
        return False
    if today is None:
        today = datetime.now(timezone.utc).date()
    return due < today


def compute_stats(todos: Iterable[Todo], today: Optional[date] = None) -> dict:
    """Compute summary statistics for ``todos``.

    Returns a dict with keys: ``total``, ``done``, ``pending``, ``overdue``
    and ``by_priority`` (a dict mapping each priority to its count).
    """
    items = list(todos)
    done = sum(1 for t in items if t.done)
    by_priority = {p: 0 for p in PRIORITIES}
    for t in items:
        if t.priority in by_priority:
            by_priority[t.priority] += 1
    return {
        "total": len(items),
        "done": done,
        "pending": len(items) - done,
        "overdue": sum(1 for t in items if is_overdue(t, today)),
        "by_priority": by_priority,
    }


def bar(count: int, total: int, width: int = 20, *, fill: str = "█",
        empty: str = "░") -> str:
    """Return a Unicode block-character bar representing ``count`` of ``total``.

    The bar is ``width`` characters wide. When ``total`` is zero the bar is
    fully empty.
    """
    if total <= 0 or count <= 0:
        filled = 0
    else:
        filled = round((count / total) * width)
        # Ensure any non-zero count shows at least one block.
        if filled == 0 and count > 0:
            filled = 1
        filled = min(filled, width)
    return fill * filled + empty * (width - filled)
