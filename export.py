"""Export helpers for the todo app.

Renders a list of :class:`~todo.Todo` items into portable text formats:

- :func:`to_csv` produces RFC-4180-style CSV (via the stdlib ``csv`` module)
  with a header row, suitable for spreadsheets.
- :func:`to_markdown` produces a Markdown checklist grouped by category.

Both functions are pure: they return a string and never touch the filesystem,
which keeps them trivial to unit test.
"""

from __future__ import annotations

import csv
import io
from typing import Iterable, List

from todo import Todo

# Column order used by the CSV exporter. Kept stable so downstream consumers
# can rely on it.
CSV_FIELDS = (
    "id",
    "title",
    "done",
    "priority",
    "category",
    "tags",
    "due_date",
    "created_at",
)

# Separator used when joining a todo's tags into a single cell / inline string.
TAG_SEPARATOR = ","

# Label used to group todos that have no category.
UNCATEGORIZED = "Uncategorized"


def to_csv(todos: Iterable[Todo]) -> str:
    """Return all ``todos`` serialized as a CSV string with a header row.

    Tags are joined with commas into a single ``tags`` cell. The stdlib ``csv``
    module handles quoting/escaping so titles containing commas, quotes or
    newlines remain valid CSV.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(CSV_FIELDS)
    for t in todos:
        writer.writerow([
            t.id,
            t.title,
            str(t.done).lower(),
            t.priority,
            t.category,
            TAG_SEPARATOR.join(t.tags),
            t.due_date or "",
            t.created_at,
        ])
    return buffer.getvalue()


def _format_item(todo: Todo) -> str:
    """Render a single todo as a Markdown checklist line."""
    checkbox = "[x]" if todo.done else "[ ]"
    line = f"- {checkbox} {todo.title}"
    extras: List[str] = []
    if todo.priority:
        extras.append(f"priority: {todo.priority}")
    if todo.due_date:
        extras.append(f"due: {todo.due_date}")
    if todo.tags:
        extras.append("tags: " + ", ".join(f"#{tag}" for tag in todo.tags))
    if extras:
        line += " _(" + "; ".join(extras) + ")_"
    return line


def to_markdown(todos: Iterable[Todo]) -> str:
    """Return ``todos`` as a Markdown checklist grouped by category.

    Categories are rendered as level-2 headings in alphabetical order
    (case-insensitive). Todos without a category are grouped under an
    ``Uncategorized`` heading which is always rendered last.
    """
    items = list(todos)

    # Group todos by category, preserving the original (first-seen) casing for
    # display while grouping case-insensitively.
    groups: dict[str, List[Todo]] = {}
    display: dict[str, str] = {}
    for t in items:
        raw = t.category.strip()
        key = raw.lower() if raw else ""
        display.setdefault(key, raw if raw else UNCATEGORIZED)
        groups.setdefault(key, []).append(t)

    def sort_key(key: str) -> tuple:
        # Empty (uncategorized) key sorts last.
        return (key == "", key)

    lines: List[str] = ["# Todos", ""]
    if not items:
        lines.append("_No todos._")
        return "\n".join(lines) + "\n"

    for key in sorted(groups, key=sort_key):
        lines.append(f"## {display[key]}")
        for t in groups[key]:
            lines.append(_format_item(t))
        lines.append("")

    # Drop the trailing blank line, then end with a single newline.
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines) + "\n"
