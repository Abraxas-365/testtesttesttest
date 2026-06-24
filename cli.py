#!/usr/bin/env python3
"""Command-line interface for the todo app.

Provides ``add``, ``list``, ``done`` and ``remove`` subcommands via argparse.
Output is colorized using ANSI escape codes (no external dependencies):
high priority is red, medium is yellow and low is green.
"""

from __future__ import annotations

import argparse
import sys
from typing import List

from export import to_csv, to_markdown
from filters import (
    bar,
    category_counts,
    compute_stats,
    filter_by_category,
    filter_by_tag,
    filter_todos,
    is_overdue,
    search_todos,
    sort_todos,
)
from store import Store
from todo import PRIORITIES, Todo

# -- ANSI colors -----------------------------------------------------------
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
YELLOW = "\033[33m"
GREEN = "\033[32m"
CYAN = "\033[36m"

PRIORITY_COLORS = {
    "high": RED,
    "medium": YELLOW,
    "low": GREEN,
}

# A short glyph shown next to each priority in the table.
PRIORITY_INDICATORS = {
    "high": "!!!",
    "medium": "!!",
    "low": "!",
}


def _color(text: str, color: str, enabled: bool) -> str:
    """Wrap ``text`` in an ANSI color if ``enabled``."""
    if not enabled:
        return text
    return f"{color}{text}{RESET}"


def _use_color(stream) -> bool:
    """Only emit color codes when writing to a real terminal."""
    return hasattr(stream, "isatty") and stream.isatty()


def _parse_tags(raw: str | None) -> List[str]:
    """Split a comma-separated ``--tags`` value into a clean list."""
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def cmd_add(store: Store, args: argparse.Namespace) -> int:
    todo = Todo(
        title=args.title,
        priority=args.priority,
        due_date=args.due,
        category=getattr(args, "category", "") or "",
        tags=_parse_tags(getattr(args, "tags", None)),
    )
    store.add(todo)
    enabled = _use_color(sys.stdout)
    color = PRIORITY_COLORS[todo.priority]
    extras = ""
    if todo.category:
        extras += " " + _color(f"@{todo.category}", CYAN, enabled)
    if todo.tags:
        extras += " " + _color(
            " ".join(f"#{tag}" for tag in todo.tags), GREEN, enabled
        )
    print(
        "Added "
        + _color(f"[{todo.priority}]", color, enabled)
        + f" {todo.title}"
        + extras
        + " "
        + _color(f"({todo.id[:8]})", DIM, enabled)
    )
    return 0


def _format_table(todos: List[Todo], enabled: bool) -> str:
    if not todos:
        return _color("No todos yet. Add one with: cli.py add \"...\"", DIM, enabled)

    header = (
        f"{BOLD if enabled else ''}"
        f"{'':<3} {'ID':<8} {'PRI':<5} {'TITLE':<30} {'DUE':<12}"
        f"{RESET if enabled else ''}"
    )
    lines = [header]
    for t in todos:
        checkbox = "[x]" if t.done else "[ ]"
        checkbox = _color(checkbox, GREEN if t.done else CYAN, enabled)
        color = PRIORITY_COLORS[t.priority]
        indicator = _color(
            f"{PRIORITY_INDICATORS[t.priority]:<3}", color, enabled
        )
        title = t.title if len(t.title) <= 30 else t.title[:27] + "..."
        if t.done:
            title = _color(title, DIM, enabled)
        due = t.due_date or "-"
        if is_overdue(t):
            due = _color(due, RED, enabled)
        lines.append(
            f"{checkbox:<3} {t.id[:8]:<8} {indicator:<5} {title:<30} {due:<12}"
        )
    return "\n".join(lines)


def _apply_filters_and_sort(
    todos: List[Todo], args: argparse.Namespace
) -> List[Todo]:
    """Apply --filter, --priority and --sort options to ``todos``."""
    status = getattr(args, "filter", "all") or "all"
    priority = getattr(args, "priority", None)
    todos = filter_todos(todos, status=status, priority=priority)
    category = getattr(args, "category", None)
    if category:
        todos = filter_by_category(todos, category)
    tag = getattr(args, "tag", None)
    if tag:
        todos = filter_by_tag(todos, tag)
    sort_key = getattr(args, "sort", None)
    if sort_key:
        todos = sort_todos(todos, sort_key)
    return todos


def cmd_list(store: Store, args: argparse.Namespace) -> int:
    todos = _apply_filters_and_sort(store.list(), args)
    print(_format_table(todos, _use_color(sys.stdout)))
    return 0


def cmd_search(store: Store, args: argparse.Namespace) -> int:
    matches = search_todos(store.list(), args.query)
    enabled = _use_color(sys.stdout)
    if not matches:
        print(
            _color(f"No todos match '{args.query}'.", DIM, enabled),
        )
        return 0
    label = "match" if len(matches) == 1 else "matches"
    print(
        _color(f"{len(matches)} {label} for '{args.query}':", BOLD, enabled)
        if enabled
        else f"{len(matches)} {label} for '{args.query}':"
    )
    print(_format_table(matches, enabled))
    return 0


def cmd_stats(store: Store, args: argparse.Namespace) -> int:
    enabled = _use_color(sys.stdout)
    todos = store.list()
    stats = compute_stats(todos)

    title = _color("Todo Statistics", BOLD, enabled) if enabled else "Todo Statistics"
    print(title)
    print(_color("=" * 30, DIM, enabled))
    print(f"  Total:   {stats['total']}")
    print(f"  Done:    " + _color(str(stats['done']), GREEN, enabled))
    print(f"  Pending: " + _color(str(stats['pending']), CYAN, enabled))
    print(
        f"  Overdue: "
        + _color(str(stats['overdue']), RED, enabled)
    )

    print()
    header = "By priority:"
    print(_color(header, BOLD, enabled) if enabled else header)
    total = stats["total"]
    for priority in PRIORITIES:
        count = stats["by_priority"][priority]
        chart = bar(count, total)
        color = PRIORITY_COLORS[priority]
        print(
            f"  {_color(f'{priority:<7}', color, enabled)} "
            f"{_color(chart, color, enabled)} {count}"
        )
    return 0


def cmd_categories(store: Store, args: argparse.Namespace) -> int:
    enabled = _use_color(sys.stdout)
    pairs = category_counts(store.list())
    if not pairs:
        print(_color("No todos yet.", DIM, enabled))
        return 0
    title = "Categories" if not enabled else _color("Categories", BOLD, enabled)
    print(title)
    print(_color("=" * 30, DIM, enabled))
    for name, count in pairs:
        label = name if name == "(none)" else f"@{name}"
        print(f"  {_color(label, CYAN, enabled)}  {count}")
    return 0


def cmd_export(store: Store, args: argparse.Namespace) -> int:
    todos = store.list()
    if args.format == "csv":
        # csv text already contains its own line terminators.
        sys.stdout.write(to_csv(todos))
    else:  # markdown
        sys.stdout.write(to_markdown(todos))
    return 0


def cmd_done(store: Store, args: argparse.Namespace) -> int:
    enabled = _use_color(sys.stdout)
    try:
        todo = store.complete(args.id_prefix)
    except ValueError as exc:
        print(_color(f"Error: {exc}", RED, enabled), file=sys.stderr)
        return 2
    if todo is None:
        print(
            _color(f"No todo found matching '{args.id_prefix}'", RED, enabled),
            file=sys.stderr,
        )
        return 1
    print(_color(f"Completed: {todo.title} ({todo.id[:8]})", GREEN, enabled))
    return 0


def cmd_remove(store: Store, args: argparse.Namespace) -> int:
    enabled = _use_color(sys.stdout)
    try:
        todo = store.remove(args.id_prefix)
    except ValueError as exc:
        print(_color(f"Error: {exc}", RED, enabled), file=sys.stderr)
        return 2
    if todo is None:
        print(
            _color(f"No todo found matching '{args.id_prefix}'", RED, enabled),
            file=sys.stderr,
        )
        return 1
    print(_color(f"Removed: {todo.title} ({todo.id[:8]})", YELLOW, enabled))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cli.py", description="A polished CLI todo app."
    )
    parser.add_argument(
        "--file",
        default="todos.json",
        help="Path to the JSON storage file (default: todos.json)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="Add a new todo")
    p_add.add_argument("title", help="Title of the todo")
    p_add.add_argument(
        "--priority",
        choices=PRIORITIES,
        default="medium",
        help="Priority level (default: medium)",
    )
    p_add.add_argument(
        "--due", default=None, help="Optional due date (YYYY-MM-DD)"
    )
    p_add.add_argument(
        "--category", default="", help="Optional category label (e.g. work)"
    )
    p_add.add_argument(
        "--tags",
        default=None,
        help="Comma-separated tags (e.g. reading,evening)",
    )
    p_add.set_defaults(func=cmd_add)

    p_list = sub.add_parser("list", help="List all todos")
    p_list.add_argument(
        "--filter",
        choices=("all", "done", "pending"),
        default="all",
        help="Filter by status (default: all)",
    )
    p_list.add_argument(
        "--priority",
        choices=PRIORITIES,
        default=None,
        help="Show only todos with this priority",
    )
    p_list.add_argument(
        "--sort",
        choices=("priority", "due", "created"),
        default=None,
        help="Sort by priority (high first), due date (soonest first) or created",
    )
    p_list.add_argument(
        "--category",
        default=None,
        help="Show only todos in this category (case-insensitive)",
    )
    p_list.add_argument(
        "--tag",
        default=None,
        help="Show only todos that have this tag (case-insensitive)",
    )
    p_list.set_defaults(func=cmd_list)

    p_search = sub.add_parser(
        "search", help="Case-insensitive substring search on titles"
    )
    p_search.add_argument("query", help="Text to search for in todo titles")
    p_search.set_defaults(func=cmd_search)

    p_stats = sub.add_parser("stats", help="Show a summary dashboard")
    p_stats.set_defaults(func=cmd_stats)

    p_categories = sub.add_parser(
        "categories", help="List all unique categories with todo counts"
    )
    p_categories.set_defaults(func=cmd_categories)

    p_export = sub.add_parser(
        "export", help="Export all todos to stdout (CSV or Markdown)"
    )
    p_export.add_argument(
        "--format",
        choices=("csv", "markdown"),
        default="csv",
        help="Export format (default: csv)",
    )
    p_export.set_defaults(func=cmd_export)

    p_done = sub.add_parser("done", help="Mark a todo as done")
    p_done.add_argument("id_prefix", help="First few characters of the todo id")
    p_done.set_defaults(func=cmd_done)

    p_remove = sub.add_parser("remove", help="Remove a todo")
    p_remove.add_argument(
        "id_prefix", help="First few characters of the todo id"
    )
    p_remove.set_defaults(func=cmd_remove)

    return parser


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    store = Store(args.file)
    return args.func(store, args)


if __name__ == "__main__":
    raise SystemExit(main())
