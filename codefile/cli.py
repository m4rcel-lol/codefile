"""
cli.py — Command-Line Interface for the Codefile Language Runner

Entry point for the `codefile` command. Supports:
    codefile run [task]  — Execute a task (default: "default")
    codefile list        — List all defined tasks
    codefile check       — Parse/validate without running
    codefile graph       — Print ASCII dependency graph
    codefile version     — Print version string
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

__version__ = "2.1.0"

DEFAULT_CODEFILE = "Codefile.codefile"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_codefile(explicit: str | None) -> Path:
    """Return the Path to the .codefile to use."""
    if explicit:
        p = Path(explicit)
        if not p.exists():
            print(f"Error: file not found: {explicit}", file=sys.stderr)
            sys.exit(1)
        return p

    # Auto-detect
    for candidate in (DEFAULT_CODEFILE, "codefile.codefile"):
        p = Path(candidate)
        if p.exists():
            return p

    print(
        "Error: no .codefile found in current directory. "
        "Use -f <file> to specify one.",
        file=sys.stderr,
    )
    sys.exit(1)


def _load(path: Path):
    """Lex + parse + load a .codefile. Returns the Interpreter."""
    from codefile import load_file, LexError, ParseError, RuntimeError_
    try:
        return load_file(str(path))
    except LexError as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)
    except ParseError as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)
    except RuntimeError_ as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)


def _print_graph(graph: dict, root: str, prefix: str = "", visited: set = None):
    """Recursively print ASCII dependency tree."""
    if visited is None:
        visited = set()
    print(prefix + root)
    if root in visited:
        return
    visited.add(root)
    deps = graph.get(root, [])
    for i, dep in enumerate(deps):
        connector = "└── " if i == len(deps) - 1 else "├── "
        child_prefix = prefix + ("    " if i == len(deps) - 1 else "│   ")
        _print_graph(graph, dep, prefix + connector, visited)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_run(args):
    path = _find_codefile(args.file)
    interp = _load(path)

    task_name = args.task or "default"

    from codefile import RuntimeError_
    try:
        interp.run_task(task_name)
    except RuntimeError_ as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)
    except SystemExit:
        raise
    except Exception as exc:
        print(f"Unexpected error: {exc}", file=sys.stderr)
        sys.exit(1)


def cmd_list(args):
    path = _find_codefile(args.file)
    interp = _load(path)
    tasks = interp.list_tasks()
    if not tasks:
        print("No tasks defined.")
        return
    print(f"Tasks in {path}:")
    for name in tasks:
        task = interp.tasks[name]
        deps = ", ".join(task.dependencies)
        dep_str = f"  needs: {deps}" if deps else ""
        print(f"  {name}{dep_str}")


def cmd_check(args):
    path = _find_codefile(args.file)
    _load(path)  # raises on parse/lex errors
    print(f"OK: {path} is valid.")


def cmd_graph(args):
    path = _find_codefile(args.file)
    interp = _load(path)
    graph = interp.task_graph()
    tasks = interp.list_tasks()

    if not tasks:
        print("No tasks defined.")
        return

    # Print the full graph starting from each root task
    # (tasks with no dependents)
    all_deps: set = set()
    for deps in graph.values():
        all_deps.update(deps)
    roots = [t for t in tasks if t not in all_deps]

    if not roots:
        roots = tasks  # fallback if everything is depended-upon (unlikely)

    print(f"Dependency graph for {path}:")
    for root in roots:
        _print_graph(graph, root)


def cmd_version(_args):
    print(f"codefile {__version__}")


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def _add_file_arg(p: argparse.ArgumentParser):
    """Add the common -f/--file argument to a subparser."""
    p.add_argument(
        "-f", "--file",
        metavar="FILE",
        default=None,
        help="Path to .codefile (default: auto-detect)",
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="codefile",
        description="Codefile — a task-oriented scripting language.",
    )

    sub = p.add_subparsers(dest="command", metavar="command")

    # run
    run_p = sub.add_parser("run", help="Run a task")
    run_p.add_argument("task", nargs="?", default=None,
                       help="Task name (default: 'default')")
    _add_file_arg(run_p)

    # list
    list_p = sub.add_parser("list", help="List all tasks")
    _add_file_arg(list_p)

    # check
    check_p = sub.add_parser("check", help="Validate without running")
    _add_file_arg(check_p)

    # graph
    graph_p = sub.add_parser("graph", help="Print dependency graph")
    _add_file_arg(graph_p)

    # version
    sub.add_parser("version", help="Print version")

    return p


def main():
    parser = build_parser()
    args = parser.parse_args()

    dispatch = {
        "run":     cmd_run,
        "list":    cmd_list,
        "check":   cmd_check,
        "graph":   cmd_graph,
        "version": cmd_version,
    }

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(1)

    handler(args)


if __name__ == "__main__":
    main()
