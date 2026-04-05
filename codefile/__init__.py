"""
__init__.py — Codefile Language Package

Exposes the high-level API for tokenizing, parsing, and interpreting
.codefile programs.
"""

from .lexer import Lexer, LexError
from .parser import Parser, ParseError
from .interpreter import Interpreter, RuntimeError_
from .ast_nodes import ProgramNode


def load_file(path: str) -> "Interpreter":
    """
    Convenience function: read a .codefile, lex + parse + load it,
    and return a ready-to-use Interpreter.
    """
    from pathlib import Path
    source = Path(path).read_text(encoding='utf-8')
    tokens = Lexer(source, path).tokenize()
    ast = Parser(tokens, path).parse()
    interp = Interpreter(filename=path)
    interp.load(ast)
    return interp


__all__ = [
    "Lexer", "LexError",
    "Parser", "ParseError",
    "Interpreter", "RuntimeError_",
    "ProgramNode",
    "load_file",
]
