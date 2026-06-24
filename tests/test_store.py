"""Tests for the JSON-backed Store and Todo model.

Each test uses a temporary directory (via pytest's ``tmp_path`` fixture) so
that no real ``todos.json`` is touched.
"""

import json
import os
import sys

import pytest

# Make the project root importable when tests are run from the tests/ dir.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from store import Store  # noqa: E402
from todo import Todo  # noqa: E402


@pytest.fixture
def store(tmp_path):
    """A Store backed by a temp todos.json file."""
    return Store(str(tmp_path / "todos.json"))


# -- add -------------------------------------------------------------------
def test_add_creates_file_and_persists(store):
    assert store.list() == []
    todo = store.add(Todo(title="Buy groceries", priority="high"))

    assert os.path.exists(store.path)
    todos = store.list()
    assert len(todos) == 1
    assert todos[0].title == "Buy groceries"
    assert todos[0].priority == "high"
    assert todos[0].done is False
    assert todos[0].id == todo.id

    # Stored as valid JSON with the expected keys.
    with open(store.path, encoding="utf-8") as fh:
        raw = json.load(fh)
    assert raw[0]["title"] == "Buy groceries"
    assert set(raw[0]) >= {
        "id", "title", "done", "priority", "created_at", "due_date"
    }


def test_add_multiple_preserves_order(store):
    store.add(Todo(title="first", priority="low"))
    store.add(Todo(title="second", priority="medium"))
    store.add(Todo(title="third", priority="high"))

    titles = [t.title for t in store.list()]
    assert titles == ["first", "second", "third"]


def test_add_with_due_date(store):
    store.add(Todo(title="taxes", priority="high", due_date="2025-04-15"))
    assert store.list()[0].due_date == "2025-04-15"


# -- list ------------------------------------------------------------------
def test_list_empty_when_no_file(store):
    assert store.list() == []


def test_list_survives_new_store_instance(store):
    store.add(Todo(title="persist me"))
    other = Store(store.path)
    assert [t.title for t in other.list()] == ["persist me"]


def test_load_handles_corrupt_file(tmp_path):
    path = tmp_path / "todos.json"
    path.write_text("{ not valid json", encoding="utf-8")
    assert Store(str(path)).list() == []


# -- complete --------------------------------------------------------------
def test_complete_marks_done(store):
    todo = store.add(Todo(title="write tests"))
    result = store.complete(todo.id[:6])

    assert result is not None
    assert result.done is True
    assert store.list()[0].done is True


def test_complete_unknown_prefix_returns_none(store):
    store.add(Todo(title="something"))
    assert store.complete("zzzzzz") is None


def test_complete_ambiguous_prefix_raises(store):
    # Two todos that share an id prefix make the prefix ambiguous.
    store.add(Todo(title="one", id="abc111"))
    store.add(Todo(title="two", id="abc222"))
    with pytest.raises(ValueError):
        store.complete("abc")


# -- remove ----------------------------------------------------------------
def test_remove_deletes_todo(store):
    a = store.add(Todo(title="keep"))
    b = store.add(Todo(title="delete"))

    removed = store.remove(b.id[:8])
    assert removed is not None
    assert removed.id == b.id

    remaining = store.list()
    assert len(remaining) == 1
    assert remaining[0].id == a.id


def test_remove_unknown_prefix_returns_none(store):
    store.add(Todo(title="stay"))
    assert store.remove("ffffff") is None
    assert len(store.list()) == 1


def test_remove_empty_prefix_raises(store):
    with pytest.raises(ValueError):
        store.remove("")


# -- find_by_prefix --------------------------------------------------------
def test_find_by_prefix(store):
    todo = store.add(Todo(title="findable"))
    found = store.find_by_prefix(todo.id[:5])
    assert found is not None and found.id == todo.id


# -- model validation ------------------------------------------------------
def test_todo_rejects_empty_title():
    with pytest.raises(ValueError):
        Todo(title="   ")


def test_todo_rejects_bad_priority():
    with pytest.raises(ValueError):
        Todo(title="x", priority="urgent")


def test_todo_roundtrip_dict():
    t = Todo(title="roundtrip", priority="low", due_date="2030-01-01")
    restored = Todo.from_dict(t.to_dict())
    assert restored.id == t.id
    assert restored.title == t.title
    assert restored.priority == t.priority
    assert restored.due_date == t.due_date
    assert restored.created_at == t.created_at
