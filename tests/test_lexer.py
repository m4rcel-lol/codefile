"""
tests/test_lexer.py — Unit tests for the Codefile lexer.
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from codefile.lexer import Lexer, TT, LexError


def tokenize(source: str):
    return Lexer(source, "<test>").tokenize()


def token_types(source: str):
    return [t.type for t in tokenize(source)]


def token_values(source: str):
    return [(t.type, t.value) for t in tokenize(source) if t.type != TT.EOF]


# ---------------------------------------------------------------------------
# Basic tokens
# ---------------------------------------------------------------------------

class TestLiterals:
    def test_integer(self):
        toks = tokenize("42")
        assert toks[0].type == TT.INT
        assert toks[0].value == 42

    def test_negative_integer(self):
        toks = tokenize("-7")
        assert toks[0].type == TT.INT
        assert toks[0].value == -7

    def test_double_quoted_string(self):
        toks = tokenize('"hello"')
        assert toks[0].type == TT.STRING
        assert toks[0].value == "hello"

    def test_single_quoted_string(self):
        toks = tokenize("'world'")
        assert toks[0].type == TT.STRING
        assert toks[0].value == "world"

    def test_string_with_interpolation_marker(self):
        # Interpolation is NOT resolved at lex time — just stored raw
        toks = tokenize('"Hello, ${name}!"')
        assert toks[0].type == TT.STRING
        assert "${name}" in toks[0].value

    def test_string_preserves_unknown_backslash_escapes(self):
        toks = tokenize(r'"C:\Users\runneradmin\file.txt"')
        assert toks[0].type == TT.STRING
        assert toks[0].value == r"C:\Users\runneradmin\file.txt"

    def test_bool_true(self):
        toks = tokenize("true")
        assert toks[0].type == TT.BOOL
        assert toks[0].value is True

    def test_bool_false(self):
        toks = tokenize("false")
        assert toks[0].type == TT.BOOL
        assert toks[0].value is False


class TestKeywords:
    def test_custom_primary_keywords(self):
        types = [t.type for t in tokenize("job requires bind when elsewhen otherwise each over loop use give stop skip exec")]
        assert TT.TASK in types
        assert TT.NEEDS in types
        assert TT.LET in types
        assert TT.IF in types
        assert TT.ELIF in types
        assert TT.ELSE in types
        assert TT.FOR in types
        assert TT.IN in types
        assert TT.WHILE in types
        assert TT.IMPORT in types
        assert TT.RETURN in types
        assert TT.BREAK in types
        assert TT.CONTINUE in types
        assert TT.SHELL in types

    def test_task_keyword(self):
        toks = tokenize("task")
        assert toks[0].type == TT.TASK

    def test_needs_keyword(self):
        toks = tokenize("needs")
        assert toks[0].type == TT.NEEDS

    def test_let_keyword(self):
        toks = tokenize("let")
        assert toks[0].type == TT.LET

    def test_if_elif_else(self):
        types = [t.type for t in tokenize("if elif else")]
        assert TT.IF in types
        assert TT.ELIF in types
        assert TT.ELSE in types

    def test_for_in(self):
        types = [t.type for t in tokenize("for in")]
        assert TT.FOR in types
        assert TT.IN in types

    def test_while(self):
        types = [t.type for t in tokenize("while")]
        assert TT.WHILE in types

    def test_break_continue(self):
        types = [t.type for t in tokenize("break continue")]
        assert TT.BREAK in types
        assert TT.CONTINUE in types

    def test_import(self):
        toks = tokenize("import")
        assert toks[0].type == TT.IMPORT

    def test_not_and_or(self):
        types = [t.type for t in tokenize("not and or")]
        assert TT.NOT in types
        assert TT.AND in types
        assert TT.OR in types


class TestOperators:
    def test_fatarrow(self):
        toks = tokenize("=>")
        assert toks[0].type == TT.FATARROW

    def test_eq(self):
        toks = tokenize("=")
        assert toks[0].type == TT.EQ

    def test_eqeq(self):
        toks = tokenize("==")
        assert toks[0].type == TT.EQEQ

    def test_neq(self):
        toks = tokenize("!=")
        assert toks[0].type == TT.NEQ

    def test_lt_gt(self):
        types = [t.type for t in tokenize("< >")]
        assert TT.LT in types
        assert TT.GT in types

    def test_lte_gte(self):
        types = [t.type for t in tokenize("<= >=")]
        assert TT.LTE in types
        assert TT.GTE in types

    def test_plus_minus(self):
        types = [t.type for t in tokenize("+ -")]
        assert TT.PLUS in types
        assert TT.MINUS in types

    def test_star_slash(self):
        types = [t.type for t in tokenize("* /")]
        assert TT.STAR in types
        assert TT.SLASH in types


class TestPunctuation:
    def test_parens(self):
        types = [t.type for t in tokenize("()")]
        assert TT.LPAREN in types
        assert TT.RPAREN in types

    def test_brackets(self):
        types = [t.type for t in tokenize("[]")]
        assert TT.LBRACKET in types
        assert TT.RBRACKET in types

    def test_comma_colon(self):
        types = [t.type for t in tokenize(",  :")]
        assert TT.COMMA in types
        assert TT.COLON in types


class TestShellLine:
    def test_shell_line_dollar(self):
        toks = tokenize("$ echo hello")
        assert toks[0].type == TT.SHELL_LINE
        assert toks[0].value == "echo hello"

    def test_shell_line_empty(self):
        toks = tokenize("$")
        assert toks[0].type == TT.SHELL_LINE
        assert toks[0].value == ""


class TestComments:
    def test_single_line_comment_ignored(self):
        toks = tokenize("# this is a comment")
        # Only EOF should remain
        types = [t.type for t in toks if t.type != TT.EOF]
        assert types == []

    def test_block_comment_ignored(self):
        source = "###\nThis is a block comment\n###\nlet x = 1"
        toks = tokenize(source)
        types = [t.type for t in toks if t.type not in (TT.EOF, TT.NEWLINE)]
        assert TT.LET in types
        assert TT.IDENT in types

    def test_inline_comment(self):
        toks = tokenize("let x = 1 # assign x")
        types = [t.type for t in toks if t.type not in (TT.NEWLINE, TT.EOF)]
        assert TT.LET in types
        assert TT.IDENT in types
        assert TT.EQ in types
        assert TT.INT in types


class TestIndentation:
    def test_indent_dedent(self):
        source = "task foo:\n    print(1)\n"
        types = [t.type for t in tokenize(source)]
        assert TT.INDENT in types
        assert TT.DEDENT in types

    def test_no_indent_no_dedent_for_flat(self):
        source = "let x = 1\nlet y = 2\n"
        types = [t.type for t in tokenize(source)]
        assert TT.INDENT not in types
        assert TT.DEDENT not in types

    def test_windows_line_endings(self):
        source = "let x = 1\r\nlet y = 2\r\n"
        toks = tokenize(source)
        # Should not raise; INT tokens should be present
        assert any(t.type == TT.INT for t in toks)


class TestErrors:
    def test_unterminated_string(self):
        with pytest.raises(LexError):
            tokenize('"unterminated')

    def test_unexpected_character(self):
        with pytest.raises(LexError):
            tokenize("@")
