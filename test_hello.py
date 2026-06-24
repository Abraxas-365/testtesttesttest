import subprocess
import sys

from hello import main


def test_main_prints_hello_world(capsys):
    """Test that main() prints 'Hello, World!' to stdout."""
    main()
    captured = capsys.readouterr()
    assert captured.out == "Hello, World!\n"


def test_script_runs_directly():
    """Test that running 'python3 hello.py' prints 'Hello, World!' to stdout."""
    result = subprocess.run(
        [sys.executable, "hello.py"],
        capture_output=True,
        text=True,
        cwd="/workspace/repo",
    )
    assert result.returncode == 0
    assert result.stdout == "Hello, World!\n"


def test_script_has_name_guard():
    """Test that importing hello does not produce output (name guard works)."""
    result = subprocess.run(
        [sys.executable, "-c", "import hello"],
        capture_output=True,
        text=True,
        cwd="/workspace/repo",
    )
    assert result.returncode == 0
    assert result.stdout == "", "Importing hello should not produce output"
