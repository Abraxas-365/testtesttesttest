"""Tests for categories, tags and export functionality.

Covers:
- The extended :class:`~todo.Todo` model (``category`` and ``tags`` fields).
- The pure helpers ``filter_by_category``, ``filter_by_tag`` and
  ``category_counts`` in :mod:`filters`.
- The CSV and Markdown exporters in :mod:`export`.
- Integration with the :mod:`cli` ``add``, ``list``, ``categories`` and
  ``export`` subcommands.
"""

import csv
import io
import os
import sys
from contextlib import redirect_stdout

import pytest

# Make the project root importable when tests are run from the tests/ dir.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cli  # noqa: E402
from export import to_csv, to_markdown  # noqa: E402
from filters import (  # noqa: E402
    category_counts,
    filter_by_category,
    filter_by_tag,
)
from store import Store  # noqa: E402
from todo import Todo  # noqa: E402


# -- fixtures --------------------------------------------------------------
@pytest.fixture
def sample():
    """A representative mix of todos spanning categories and tags."""
    return [
        Todo(title="Read book", category="personal",
             tags=["reading", "evening"], id="aaa001"),
        Todo(title="Finish report", category="work", priority="high",
             tags=["urgent", "office"], id="bbb002"),
        Todo(title="Email boss", category="work", tags=["urgent"],
             done=True, id="ccc003"),
        Todo(title="Loose task", id="ddd004"),
    ]


@pytest.fixture
def store(tmp_path):
    """A Store backed by a temp todos.json file."""
    return Store(str(tmp_path / "todos.json"))


def _run(store, argv):
    """Invoke cli.main against ``store``'s file and capture stdout."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = cli.main(["--file", store.path, *argv])
    return code, buf.getvalue()


# -- model -----------------------------------------------------------------
def test_todo_defaults_category_and_tags():
    t = Todo(title="x")
    assert t.category == ""
    assert t.tags == []


def test_todo_tags_normalized_and_deduped():
    t = Todo(title="x", category="  Work  ", tags=[" a ", "a", "", "b"])
    assert t.category == "Work"
    assert t.tags == ["a", "b"]


def test_todo_roundtrip_preserves_category_and_tags():
    t = Todo(title="x", category="home", tags=["chore"], id="z1")
    restored = Todo.from_dict(t.to_dict())
    assert restored.category == "home"
    assert restored.tags == ["chore"]


def test_from_dict_missing_fields_defaults():
    restored = Todo.from_dict({"id": "z2", "title": "legacy"})
    assert restored.category == ""
    assert restored.tags == []


def test_store_persists_category_and_tags(store):
    store.add(Todo(title="x", category="work", tags=["a", "b"]))
    loaded = store.list()
    assert loaded[0].category == "work"
    assert loaded[0].tags == ["a", "b"]


# -- category filtering ----------------------------------------------------
def test_filter_by_category(sample):
    result = filter_by_category(sample, "work")
    assert [t.id for t in result] == ["bbb002", "ccc003"]


def test_filter_by_category_is_case_insensitive(sample):
    assert len(filter_by_category(sample, "WORK")) == 2
    assert len(filter_by_category(sample, "Personal")) == 1


def test_filter_by_category_empty_returns_all(sample):
    assert filter_by_category(sample, "") == sample


def test_filter_by_category_no_match(sample):
    assert filter_by_category(sample, "missing") == []


def test_filter_by_category_does_not_mutate(sample):
    original = list(sample)
    filter_by_category(sample, "work")
    assert sample == original


# -- tag filtering ---------------------------------------------------------
def test_filter_by_tag(sample):
    result = filter_by_tag(sample, "urgent")
    assert [t.id for t in result] == ["bbb002", "ccc003"]


def test_filter_by_tag_is_case_insensitive(sample):
    assert len(filter_by_tag(sample, "URGENT")) == 2


def test_filter_by_tag_single_match(sample):
    result = filter_by_tag(sample, "reading")
    assert [t.id for t in result] == ["aaa001"]


def test_filter_by_tag_no_match(sample):
    assert filter_by_tag(sample, "nope") == []


def test_filter_by_tag_empty_returns_all(sample):
    assert filter_by_tag(sample, "") == sample


# -- category counts -------------------------------------------------------
def test_category_counts(sample):
    counts = category_counts(sample)
    assert counts == [("personal", 1), ("work", 2), ("(none)", 1)]


def test_category_counts_none_sorts_last_and_empty():
    assert category_counts([]) == []
    only_none = [Todo(title="a"), Todo(title="b")]
    assert category_counts(only_none) == [("(none)", 2)]


def test_category_counts_case_insensitive_grouping():
    todos = [
        Todo(title="a", category="Work"),
        Todo(title="b", category="work"),
    ]
    counts = category_counts(todos)
    # Grouped together, first-seen casing used for display.
    assert counts == [("Work", 2)]


# -- CSV export ------------------------------------------------------------
def test_export_csv_has_header_and_rows(sample):
    out = to_csv(sample)
    rows = list(csv.reader(io.StringIO(out)))
    assert rows[0] == [
        "id", "title", "done", "priority", "category",
        "tags", "due_date", "created_at",
    ]
    assert len(rows) == 1 + len(sample)


def test_export_csv_is_valid_and_joins_tags(sample):
    out = to_csv(sample)
    reader = csv.DictReader(io.StringIO(out))
    rows = list(reader)
    by_id = {r["id"]: r for r in rows}
    assert by_id["aaa001"]["tags"] == "reading,evening"
    assert by_id["aaa001"]["category"] == "personal"
    assert by_id["ccc003"]["done"] == "true"
    assert by_id["ddd004"]["tags"] == ""
    assert by_id["ddd004"]["category"] == ""


def test_export_csv_escapes_special_chars():
    todos = [Todo(title='Has, comma "and" quote', category="x", id="e1")]
    out = to_csv(todos)
    rows = list(csv.reader(io.StringIO(out)))
    # The stdlib csv reader round-trips the tricky title intact.
    assert rows[1][1] == 'Has, comma "and" quote'


# -- Markdown export -------------------------------------------------------
def test_export_markdown_groups_by_category(sample):
    out = to_markdown(sample)
    assert "## personal" in out
    assert "## work" in out
    # Todos without a category grouped under Uncategorized, rendered last.
    assert "## Uncategorized" in out
    assert out.index("## work") < out.index("## Uncategorized")


def test_export_markdown_is_a_checklist(sample):
    out = to_markdown(sample)
    assert "- [ ] Read book" in out
    # Done todos use a checked box.
    assert "- [x] Email boss" in out


def test_export_markdown_empty():
    out = to_markdown([])
    assert "_No todos._" in out


# -- CLI integration -------------------------------------------------------
def test_cli_add_with_category_and_tags(store):
    code, _ = _run(store, ["add", "Read book", "--category", "personal",
                           "--tags", "reading,evening"])
    assert code == 0
    todo = store.list()[0]
    assert todo.category == "personal"
    assert todo.tags == ["reading", "evening"]


def test_cli_list_filter_by_category(store):
    _run(store, ["add", "A", "--category", "work"])
    _run(store, ["add", "B", "--category", "home"])
    code, out = _run(store, ["list", "--category", "work"])
    assert code == 0
    assert "A" in out
    assert "B" not in out


def test_cli_list_filter_by_tag(store):
    _run(store, ["add", "A", "--tags", "urgent,office"])
    _run(store, ["add", "B", "--tags", "later"])
    code, out = _run(store, ["list", "--tag", "urgent"])
    assert code == 0
    assert "A" in out
    assert "B" not in out


def test_cli_categories_lists_counts(store):
    _run(store, ["add", "A", "--category", "work"])
    _run(store, ["add", "B", "--category", "work"])
    _run(store, ["add", "C", "--category", "home"])
    _run(store, ["add", "D"])
    code, out = _run(store, ["categories"])
    assert code == 0
    assert "@work" in out and "2" in out
    assert "@home" in out
    assert "(none)" in out


def test_cli_export_csv(store):
    _run(store, ["add", "Task one", "--category", "work", "--tags", "a,b"])
    code, out = _run(store, ["export", "--format", "csv"])
    assert code == 0
    rows = list(csv.DictReader(io.StringIO(out)))
    assert rows[0]["title"] == "Task one"
    assert rows[0]["tags"] == "a,b"


def test_cli_export_markdown(store):
    _run(store, ["add", "Task one", "--category", "work"])
    code, out = _run(store, ["export", "--format", "markdown"])
    assert code == 0
    assert "## work" in out
    assert "- [ ] Task one" in out
