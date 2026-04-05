"""
stdlib.py — Standard Library for the Codefile Language

Provides built-in functions available in all .codefile programs.
All functions are implemented as plain Python callables and registered
into the interpreter's global environment at startup.
"""

from __future__ import annotations
import os
import sys
import datetime
import subprocess
from pathlib import Path
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _as_str(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


# ---------------------------------------------------------------------------
# Built-in implementations
# ---------------------------------------------------------------------------

def builtin_print(value: Any) -> None:
    """print(value) — Print value to stdout."""
    print(_as_str(value))


def builtin_log(message: Any) -> None:
    """log(message) — Print message with [HH:MM:SS] timestamp prefix."""
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {_as_str(message)}")


def builtin_run(command: Any) -> str:
    """run(command) — Execute shell command, return stdout as string."""
    cmd = _as_str(command)
    if os.name == 'nt':
        shell_exec = True
    else:
        shell_exec = True

    result = subprocess.run(
        cmd,
        shell=shell_exec,
        capture_output=True,
        text=True,
        executable=None if os.name == 'nt' else os.environ.get('SHELL', '/bin/sh'),
    )
    return result.stdout.rstrip('\n')


def builtin_env(name: Any, default: Any = "") -> str:
    """env(name[, default]) — Get environment variable value."""
    return os.environ.get(_as_str(name), _as_str(default))


def builtin_exists(path: Any) -> bool:
    """exists(path) — Return true if file/directory exists."""
    return Path(_as_str(path)).exists()


def builtin_fail(message: Any) -> None:
    """fail(message) — Abort execution with error message."""
    print(f"FAIL: {_as_str(message)}", file=sys.stderr)
    raise SystemExit(1)


def builtin_read_file(path: Any) -> str:
    """read_file(path) — Return file contents as string."""
    p = Path(_as_str(path))
    if not p.exists():
        raise RuntimeError(f"read_file: file not found: {p}")
    return p.read_text(encoding='utf-8')


def builtin_write_file(path: Any, content: Any) -> None:
    """write_file(path, content) — Write string content to file."""
    p = Path(_as_str(path))
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(_as_str(content), encoding='utf-8')


def builtin_platform() -> str:
    """platform() — Return 'windows' or 'linux'."""
    if os.name == 'nt':
        return "windows"
    return "linux"


def builtin_len(value: Any) -> int:
    """len(value) — Return length of string or list."""
    if isinstance(value, (str, list)):
        return len(value)
    raise TypeError(f"len() expects string or list, got {type(value).__name__}")


def builtin_str(value: Any) -> str:
    """str(value) — Convert value to string."""
    return _as_str(value)


def builtin_int(value: Any) -> int:
    """int(value) — Convert value to integer."""
    try:
        return int(value)
    except (ValueError, TypeError) as exc:
        raise TypeError(f"int() cannot convert {value!r}: {exc}") from exc


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

BUILTINS: dict[str, Any] = {
    "print":      builtin_print,
    "log":        builtin_log,
    "run":        builtin_run,
    "env":        builtin_env,
    "exists":     builtin_exists,
    "fail":       builtin_fail,
    "read_file":  builtin_read_file,
    "write_file": builtin_write_file,
    "platform":   builtin_platform,
    "len":        builtin_len,
    "str":        builtin_str,
    "int":        builtin_int,
}
