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


def cmd_add(store: Store, args: argparse.Namespace) -> int:
    todo = Todo(title=args.title, priority=args.priority, due_date=args.due)
    store.add(todo)
    enabled = _use_color(sys.stdout)
    color = PRIORITY_COLORS[todo.priority]
    print(
        "Added "
        + _color(f"[{todo.priority}]", color, enabled)
        + f" {todo.title} "
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
        lines.append(
            f"{checkbox:<3} {t.id[:8]:<8} {indicator:<5} {title:<30} {due:<12}"
        )
    return "\n".join(lines)


def cmd_list(store: Store, args: argparse.Namespace) -> int:
    todos = store.list()
    print(_format_table(todos, _use_color(sys.stdout)))
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
    p_add.set_defaults(func=cmd_add)

    p_list = sub.add_parser("list", help="List all todos")
    p_list.set_defaults(func=cmd_list)

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
