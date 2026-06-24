"""Tests for filtering, sorting, search and statistics.

Covers the pure helpers in :mod:`filters` as well as their integration with
the :mod:`cli` ``list``, ``search`` and ``stats`` subcommands.
"""

import io
import os
import sys
from contextlib import redirect_stdout
from datetime import date

import pytest

# Make the project root importable when tests are run from the tests/ dir.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cli  # noqa: E402
from filters import (  # noqa: E402
    bar,
    compute_stats,
    filter_todos,
    is_overdue,
    search_todos,
    sort_todos,
)
from store import Store  # noqa: E402
from todo import Todo  # noqa: E402


# -- fixtures --------------------------------------------------------------
@pytest.fixture
def sample():
    """A representative mix of todos: priorities, done flags, due dates."""
    return [
        Todo(title="Buy groceries", priority="high", due_date="2020-01-01",
             id="aaa001"),
        Todo(title="Write REPORT", priority="medium", due_date="2099-12-31",
             id="bbb002"),
        Todo(title="Call dentist", priority="low", done=True, id="ccc003"),
        Todo(title="Pay rent", priority="high", due_date="2099-01-01",
             id="ddd004"),
        Todo(title="Read book", priority="low", id="eee005"),
    ]


@pytest.fixture
def store(tmp_path, sample):
    s = Store(str(tmp_path / "todos.json"))
    for t in sample:
        s.add(t)
    return s


# -- filter by status ------------------------------------------------------
def test_filter_done(sample):
    result = filter_todos(sample, status="done")
    assert [t.title for t in result] == ["Call dentist"]
    assert all(t.done for t in result)


def test_filter_pending(sample):
    result = filter_todos(sample, status="pending")
    assert all(not t.done for t in result)
    assert "Call dentist" not in [t.title for t in result]
    assert len(result) == 4


def test_filter_all_is_identity(sample):
    assert filter_todos(sample, status="all") == sample


def test_filter_invalid_status_raises(sample):
    with pytest.raises(ValueError):
        filter_todos(sample, status="bogus")


def test_filter_does_not_mutate_input(sample):
    original = list(sample)
    filter_todos(sample, status="done")
    assert sample == original


# -- filter by priority ----------------------------------------------------
def test_filter_priority_high(sample):
    result = filter_todos(sample, priority="high")
    assert {t.title for t in result} == {"Buy groceries", "Pay rent"}


def test_filter_priority_and_status_combined(sample):
    # high + pending excludes the done low-priority dentist todo.
    result = filter_todos(sample, status="pending", priority="high")
    assert {t.title for t in result} == {"Buy groceries", "Pay rent"}


def test_filter_invalid_priority_raises(sample):
    with pytest.raises(ValueError):
        filter_todos(sample, priority="urgent")


# -- sorting ---------------------------------------------------------------
def test_sort_by_priority_high_first(sample):
    result = sort_todos(sample, "priority")
    priorities = [t.priority for t in result]
    assert priorities == ["high", "high", "medium", "low", "low"]


def test_sort_by_due_soonest_first_no_date_last(sample):
    result = sort_todos(sample, "due")
    dues = [t.due_date for t in result]
    # Soonest dated first, ascending; the two with no due date come last.
    assert dues[:3] == ["2020-01-01", "2099-01-01", "2099-12-31"]
    assert dues[3:] == [None, None]


def test_sort_by_created(sample):
    result = sort_todos(sample, "created")
    # created_at is monotonically assigned in fixture order here.
    assert [t.created_at for t in result] == sorted(
        t.created_at for t in sample
    )


def test_sort_invalid_key_raises(sample):
    with pytest.raises(ValueError):
        sort_todos(sample, "color")


def test_sort_does_not_mutate_input(sample):
    original = list(sample)
    sort_todos(sample, "priority")
    assert sample == original


# -- search ----------------------------------------------------------------
def test_search_case_insensitive(sample):
    assert [t.title for t in search_todos(sample, "report")] == ["Write REPORT"]
    assert [t.title for t in search_todos(sample, "REPORT")] == ["Write REPORT"]


def test_search_substring(sample):
    result = search_todos(sample, "e")
    titles = {t.title for t in result}
    # "Buy groceries", "Write REPORT", "Call dentist", "Read book" contain 'e'
    assert "Pay rent" in titles  # has 'e' in rent
    assert "Read book" in titles


def test_search_no_match(sample):
    assert search_todos(sample, "xyzzy") == []


def test_search_empty_query_returns_all(sample):
    assert search_todos(sample, "   ") == sample


# -- overdue ---------------------------------------------------------------
def test_is_overdue_past_due_and_pending():
    t = Todo(title="late", due_date="2000-01-01")
    assert is_overdue(t, today=date(2024, 1, 1)) is True


def test_is_overdue_future_not_overdue():
    t = Todo(title="future", due_date="2099-01-01")
    assert is_overdue(t, today=date(2024, 1, 1)) is False


def test_is_overdue_done_never_overdue():
    t = Todo(title="done late", due_date="2000-01-01", done=True)
    assert is_overdue(t, today=date(2024, 1, 1)) is False


def test_is_overdue_no_due_date():
    t = Todo(title="someday")
    assert is_overdue(t, today=date(2024, 1, 1)) is False


# -- stats -----------------------------------------------------------------
def test_compute_stats(sample):
    stats = compute_stats(sample, today=date(2024, 1, 1))
    assert stats["total"] == 5
    assert stats["done"] == 1
    assert stats["pending"] == 4
    assert stats["overdue"] == 1  # only "Buy groceries" (2020-01-01) is overdue
    assert stats["by_priority"] == {"high": 2, "medium": 1, "low": 2}


def test_compute_stats_empty():
    stats = compute_stats([])
    assert stats["total"] == 0
    assert stats["done"] == 0
    assert stats["pending"] == 0
    assert stats["overdue"] == 0
    assert stats["by_priority"] == {"high": 0, "medium": 0, "low": 0}


# -- bar chart -------------------------------------------------------------
def test_bar_uses_unicode_blocks():
    out = bar(1, 2, width=10)
    assert len(out) == 10
    assert "█" in out and "░" in out


def test_bar_full_and_empty():
    assert bar(2, 2, width=8) == "█" * 8
    assert bar(0, 2, width=8) == "░" * 8


def test_bar_zero_total_is_empty():
    assert bar(0, 0, width=5) == "░" * 5


def test_bar_nonzero_count_shows_at_least_one_block():
    out = bar(1, 1000, width=20)
    assert out.startswith("█")


# -- CLI integration -------------------------------------------------------
def _run(store, *argv):
    """Run a cli subcommand against ``store`` and capture stdout."""
    buf = io.StringIO()
    argv = ["--file", store.path, *argv]
    with redirect_stdout(buf):
        code = cli.main(argv)
    return code, buf.getvalue()


def test_cli_list_filter_done(store):
    code, out = _run(store, "list", "--filter", "done")
    assert code == 0
    assert "Call dentist" in out
    assert "Buy groceries" not in out


def test_cli_list_filter_pending(store):
    code, out = _run(store, "list", "--filter", "pending")
    assert code == 0
    assert "Call dentist" not in out
    assert "Buy groceries" in out


def test_cli_list_priority_high(store):
    code, out = _run(store, "list", "--priority", "high")
    assert code == 0
    assert "Buy groceries" in out
    assert "Pay rent" in out
    assert "Call dentist" not in out


def test_cli_list_sort_priority(store):
    code, out = _run(store, "list", "--sort", "priority")
    assert code == 0
    body = "\n".join(out.splitlines()[1:])  # drop header
    # Both high-priority todos must appear before any lower-priority ones.
    last_high = max(body.index("Buy groceries"), body.index("Pay rent"))
    first_lower = min(
        body.index("Write REPORT"),  # medium
        body.index("Call dentist"),  # low
        body.index("Read book"),     # low
    )
    assert last_high < first_lower


def test_cli_list_sort_due(store):
    code, out = _run(store, "list", "--sort", "due")
    assert code == 0
    body = "\n".join(out.splitlines()[1:])
    assert body.index("Buy groceries") < body.index("Pay rent")
    assert body.index("Pay rent") < body.index("Write REPORT")


def test_cli_search(store):
    code, out = _run(store, "search", "report")
    assert code == 0
    assert "Write REPORT" in out
    assert "1 match" in out


def test_cli_search_no_match(store):
    code, out = _run(store, "search", "zzzznope")
    assert code == 0
    assert "No todos match" in out


def test_cli_stats(store):
    code, out = _run(store, "stats")
    assert code == 0
    assert "Total:" in out
    assert "Done:" in out
    assert "Pending:" in out
    assert "Overdue:" in out
    assert "high" in out and "medium" in out and "low" in out
    assert "█" in out or "░" in out  # bar chart present
