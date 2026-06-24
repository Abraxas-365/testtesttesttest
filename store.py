"""JSON-file storage backend for todos.

The :class:`Store` class persists a list of :class:`~todo.Todo` items to a
``todos.json`` file using only the standard library ``json`` module.
"""

from __future__ import annotations

import json
import os
from typing import List, Optional

from todo import Todo

DEFAULT_FILENAME = "todos.json"


class Store:
    """Reads and writes todos to a JSON file."""

    def __init__(self, path: str = DEFAULT_FILENAME) -> None:
        self.path = path

    # -- persistence ------------------------------------------------------
    def load(self) -> List[Todo]:
        """Load all todos from disk. Returns an empty list if no file."""
        if not os.path.exists(self.path):
            return []
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
        except (json.JSONDecodeError, ValueError):
            # Corrupt or empty file: treat as no todos rather than crashing.
            return []
        return [Todo.from_dict(item) for item in raw]

    def save(self, todos: List[Todo]) -> None:
        """Persist the given list of todos to disk atomically."""
        directory = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(directory, exist_ok=True)
        tmp_path = f"{self.path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump([t.to_dict() for t in todos], fh, indent=2)
            fh.write("\n")
        os.replace(tmp_path, self.path)

    # -- operations -------------------------------------------------------
    def add(self, todo: Todo) -> Todo:
        """Add a todo and persist. Returns the added todo."""
        todos = self.load()
        todos.append(todo)
        self.save(todos)
        return todo

    def list(self) -> List[Todo]:
        """Return all todos."""
        return self.load()

    def find_by_prefix(self, id_prefix: str) -> Optional[Todo]:
        """Return the single todo whose id starts with ``id_prefix``.

        Raises:
            ValueError: if the prefix is empty or matches more than one todo.
        """
        if not id_prefix:
            raise ValueError("id prefix must not be empty")
        matches = [t for t in self.load() if t.id.startswith(id_prefix)]
        if len(matches) > 1:
            raise ValueError(
                f"id prefix {id_prefix!r} is ambiguous ({len(matches)} matches)"
            )
        return matches[0] if matches else None

    def complete(self, id_prefix: str) -> Optional[Todo]:
        """Mark the todo matching ``id_prefix`` as done. Returns it or None."""
        todos = self.load()
        target = None
        for todo in todos:
            if todo.id.startswith(id_prefix):
                if target is not None:
                    raise ValueError(
                        f"id prefix {id_prefix!r} is ambiguous"
                    )
                target = todo
        if target is None:
            return None
        target.done = True
        self.save(todos)
        return target

    def remove(self, id_prefix: str) -> Optional[Todo]:
        """Delete the todo matching ``id_prefix``. Returns it or None."""
        if not id_prefix:
            raise ValueError("id prefix must not be empty")
        todos = self.load()
        matches = [t for t in todos if t.id.startswith(id_prefix)]
        if len(matches) > 1:
            raise ValueError(f"id prefix {id_prefix!r} is ambiguous")
        if not matches:
            return None
        target = matches[0]
        remaining = [t for t in todos if t.id != target.id]
        self.save(remaining)
        return target
