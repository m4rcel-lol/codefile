"""
lexer.py — Lexer/Tokenizer for the Codefile Language

Converts raw .codefile source text into a stream of typed tokens.
Handles keywords, literals, operators, identifiers, shell commands,
indentation (INDENT/DEDENT), and comments.
"""

from __future__ import annotations
import re
from enum import Enum, auto
from typing import List, NamedTuple


# ---------------------------------------------------------------------------
# Token types
# ---------------------------------------------------------------------------

class TT(Enum):
    """Token Type enumeration."""
    # Literals
    INT         = auto()
    FLOAT       = auto()
    STRING      = auto()
    BOOL        = auto()

    # Identifiers and keywords
    IDENT       = auto()
    TASK        = auto()
    NEEDS       = auto()
    LET         = auto()
    IF          = auto()
    ELIF        = auto()
    ELSE        = auto()
    FOR         = auto()
    WHILE       = auto()
    IN          = auto()
    DO          = auto()
    BREAK       = auto()
    CONTINUE    = auto()
    RETURN      = auto()
    IMPORT      = auto()
    SHELL       = auto()    # the 'shell' keyword for shell blocks
    NOT         = auto()
    AND         = auto()
    OR          = auto()
    TRUE        = auto()
    FALSE       = auto()

    # Operators
    PLUS        = auto()   # +
    MINUS       = auto()   # -
    STAR        = auto()   # *
    SLASH       = auto()   # /
    EQ          = auto()   # =
    EQEQ        = auto()   # ==
    NEQ         = auto()   # !=
    LT          = auto()   # <
    GT          = auto()   # >
    LTE         = auto()   # <=
    GTE         = auto()   # >=

    # Punctuation
    LPAREN      = auto()   # (
    RPAREN      = auto()   # )
    LBRACKET    = auto()   # [
    RBRACKET    = auto()   # ]
    COMMA       = auto()   # ,
    COLON       = auto()   # :
    DOLLAR      = auto()   # $ (shell command prefix)

    # Structure
    NEWLINE     = auto()
    INDENT      = auto()
    DEDENT      = auto()
    EOF         = auto()

    # Shell line (everything after $)
    SHELL_LINE  = auto()
    FATARROW    = auto()   # =>


# Keywords mapping
KEYWORDS: dict[str, TT] = {
    # Custom-first surface syntax
    "job":      TT.TASK,
    "requires": TT.NEEDS,
    "bind":     TT.LET,
    "when":     TT.IF,
    "elsewhen": TT.ELIF,
    "otherwise": TT.ELSE,
    "each":     TT.FOR,
    "over":     TT.IN,
    "loop":     TT.WHILE,
    "use":      TT.IMPORT,
    "give":     TT.RETURN,
    "stop":     TT.BREAK,
    "skip":     TT.CONTINUE,
    "exec":     TT.SHELL,
    # Legacy compatibility aliases
    "task":     TT.TASK,
    "needs":    TT.NEEDS,
    "let":      TT.LET,
    "if":       TT.IF,
    "elif":     TT.ELIF,
    "else":     TT.ELSE,
    "for":      TT.FOR,
    "while":    TT.WHILE,
    "in":       TT.IN,
    "do":       TT.DO,
    "break":    TT.BREAK,
    "continue": TT.CONTINUE,
    "return":   TT.RETURN,
    "import":   TT.IMPORT,
    "shell":    TT.SHELL,
    "not":      TT.NOT,
    "and":      TT.AND,
    "or":       TT.OR,
    "true":     TT.TRUE,
    "false":    TT.FALSE,
}


# ---------------------------------------------------------------------------
# Token
# ---------------------------------------------------------------------------

class Token(NamedTuple):
    type: TT
    value: object      # str, int, bool, or None
    line: int
    col: int

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r}, {self.line}:{self.col})"


# ---------------------------------------------------------------------------
# Lexer error
# ---------------------------------------------------------------------------

class LexError(Exception):
    def __init__(self, msg: str, line: int, col: int, filename: str = "<input>"):
        self.msg = msg
        self.line = line
        self.col = col
        self.filename = filename
        super().__init__(f"LexError [{filename}:{line}:{col}]: {msg}")


# ---------------------------------------------------------------------------
# Lexer
# ---------------------------------------------------------------------------

class Lexer:
    """
    Tokenizes Codefile source code.

    The lexer works in two passes:
    1. Split source into logical lines, handling block comments and
       normalizing line endings.
    2. Scan each line for tokens, emitting INDENT/DEDENT tokens based
       on indentation changes.
    """

    def __init__(self, source: str, filename: str = "<input>"):
        # Normalize Windows line endings
        self.source = source.replace("\r\n", "\n").replace("\r", "\n")
        self.filename = filename
        self.tokens: List[Token] = []

    def tokenize(self) -> List[Token]:
        """Main entry point. Returns complete token list ending with EOF."""
        lines = self._preprocess_lines()
        indent_stack = [0]
        pending_indent_check = False

        line_num = 0
        for raw_line, original_lineno in lines:
            line_num = original_lineno

            # Measure indentation
            stripped = raw_line.lstrip()
            if not stripped or stripped.startswith("#"):
                # Blank or comment-only lines don't affect indentation
                continue

            indent = len(raw_line) - len(stripped)

            # Emit INDENT / DEDENT tokens
            if indent > indent_stack[-1]:
                indent_stack.append(indent)
                self.tokens.append(Token(TT.INDENT, None, original_lineno, 1))
            elif indent < indent_stack[-1]:
                while indent_stack and indent_stack[-1] > indent:
                    indent_stack.pop()
                    self.tokens.append(Token(TT.DEDENT, None, original_lineno, 1))
                if indent_stack[-1] != indent:
                    raise LexError(
                        "Indentation error — does not match any outer indentation level",
                        original_lineno, 1, self.filename
                    )

            # Tokenize the content of the line
            self._scan_line(stripped, original_lineno)
            self.tokens.append(Token(TT.NEWLINE, None, original_lineno, len(raw_line)))

        # Close any remaining indent levels
        while len(indent_stack) > 1:
            indent_stack.pop()
            self.tokens.append(Token(TT.DEDENT, None, line_num, 1))

        self.tokens.append(Token(TT.EOF, None, line_num + 1, 0))
        return self.tokens

    # ------------------------------------------------------------------
    # Preprocessing
    # ------------------------------------------------------------------

    def _preprocess_lines(self):
        """
        Yield (line_text, lineno) tuples, stripping block comments and
        handling continuation (not needed currently but reserved for future).
        """
        raw_lines = self.source.split("\n")
        in_block_comment = False
        result = []

        i = 0
        while i < len(raw_lines):
            line = raw_lines[i]
            lineno = i + 1

            if in_block_comment:
                if "###" in line:
                    in_block_comment = False
                i += 1
                continue

            # Check for block comment start
            stripped = line.strip()
            if stripped.startswith("###"):
                # Check if it closes on same line (e.g. ### text ###)
                rest = stripped[3:]
                if "###" in rest:
                    # Same-line block comment — treat as blank
                    pass
                else:
                    in_block_comment = True
                i += 1
                continue

            result.append((line, lineno))
            i += 1

        return result

    # ------------------------------------------------------------------
    # Line scanner
    # ------------------------------------------------------------------

    def _scan_line(self, line: str, lineno: int):
        """Scan a single line and append tokens."""
        pos = 0
        length = len(line)

        while pos < length:
            # Skip spaces/tabs (indentation already handled)
            if line[pos] in (' ', '\t'):
                pos += 1
                continue

            # Single-line comment
            if line[pos] == '#':
                break  # rest of line is a comment

            col = pos + 1  # 1-based column

            # Shell command: $ <rest of line>
            if line[pos] == '$':
                shell_content = line[pos + 1:].strip()
                self.tokens.append(Token(TT.SHELL_LINE, shell_content, lineno, col))
                return  # $ consumes the rest of the line

            # String literals
            if line[pos] in ('"', "'"):
                tok, pos = self._scan_string(line, pos, lineno)
                self.tokens.append(tok)
                continue

            # Numbers
            if line[pos].isdigit() or (line[pos] == '-' and pos + 1 < length and line[pos + 1].isdigit()):
                tok, pos = self._scan_number(line, pos, lineno)
                self.tokens.append(tok)
                continue

            # Identifiers and keywords
            if line[pos].isalpha() or line[pos] == '_':
                tok, pos = self._scan_ident(line, pos, lineno)
                self.tokens.append(tok)
                continue

            # Two-character operators
            two = line[pos:pos + 2]
            if two == '==':
                self.tokens.append(Token(TT.EQEQ, '==', lineno, col))
                pos += 2; continue
            if two == '=>':
                self.tokens.append(Token(TT.FATARROW, '=>', lineno, col))
                pos += 2; continue
            if two == '!=':
                self.tokens.append(Token(TT.NEQ, '!=', lineno, col))
                pos += 2; continue
            if two == '<=':
                self.tokens.append(Token(TT.LTE, '<=', lineno, col))
                pos += 2; continue
            if two == '>=':
                self.tokens.append(Token(TT.GTE, '>=', lineno, col))
                pos += 2; continue

            # Single-character tokens
            single = line[pos]
            simple_map = {
                '=': TT.EQ,
                '<': TT.LT,
                '>': TT.GT,
                '+': TT.PLUS,
                '-': TT.MINUS,
                '*': TT.STAR,
                '/': TT.SLASH,
                '(': TT.LPAREN,
                ')': TT.RPAREN,
                '[': TT.LBRACKET,
                ']': TT.RBRACKET,
                ',': TT.COMMA,
                ':': TT.COLON,
            }
            if single in simple_map:
                self.tokens.append(Token(simple_map[single], single, lineno, col))
                pos += 1
                continue

            raise LexError(f"Unexpected character: {single!r}", lineno, col, self.filename)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _scan_string(self, line: str, pos: int, lineno: int):
        """Scan a quoted string (single or double quotes)."""
        quote = line[pos]
        pos += 1
        start_col = pos
        buf = []
        length = len(line)
        while pos < length:
            ch = line[pos]
            if ch == '\\' and pos + 1 < length:
                nxt = line[pos + 1]
                escape_map = {'n': '\n', 't': '\t', '\\': '\\', '"': '"', "'": "'"}
                buf.append(escape_map.get(nxt, nxt))
                pos += 2
                continue
            if ch == quote:
                pos += 1
                return Token(TT.STRING, ''.join(buf), lineno, start_col), pos
            buf.append(ch)
            pos += 1
        raise LexError("Unterminated string literal", lineno, start_col, self.filename)

    def _scan_number(self, line: str, pos: int, lineno: int):
        """Scan an integer or float literal (optionally negative)."""
        start = pos
        col = pos + 1
        if line[pos] == '-':
            pos += 1
        while pos < len(line) and line[pos].isdigit():
            pos += 1

        is_float = False
        if pos < len(line) and line[pos] == '.' and pos + 1 < len(line) and line[pos + 1].isdigit():
            is_float = True
            pos += 1
            while pos < len(line) and line[pos].isdigit():
                pos += 1

        raw = line[start:pos]
        if is_float:
            return Token(TT.FLOAT, float(raw), lineno, col), pos
        return Token(TT.INT, int(raw), lineno, col), pos

    def _scan_ident(self, line: str, pos: int, lineno: int):
        """Scan an identifier or keyword."""
        start = pos
        col = pos + 1
        while pos < len(line) and (line[pos].isalnum() or line[pos] == '_'):
            pos += 1
        word = line[start:pos]
        tt = KEYWORDS.get(word, TT.IDENT)
        # Map true/false to BOOL type with Python bool value
        if tt == TT.TRUE:
            return Token(TT.BOOL, True, lineno, col), pos
        if tt == TT.FALSE:
            return Token(TT.BOOL, False, lineno, col), pos
        return Token(tt, word, lineno, col), pos
