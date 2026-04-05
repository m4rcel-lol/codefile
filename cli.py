"""
cli.py — Codefile CLI Entry Point

Thin wrapper that imports and runs the main CLI from the codefile package.
Run with: python cli.py <command> [options]
"""
from codefile.cli import main

if __name__ == "__main__":
    main()
