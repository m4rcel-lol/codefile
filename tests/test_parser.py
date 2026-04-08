"""
tests/test_parser.py — Unit tests for the Codefile parser.
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from codefile.lexer import Lexer
from codefile.parser import Parser, ParseError
from codefile.ast_nodes import (
    ProgramNode, TaskNode, AssignNode, IfNode, ForNode, WhileNode,
    BreakNode, ContinueNode, ReturnNode, ShellCommandNode, ShellBlockNode,
    ImportNode, BinaryOpNode, UnaryOpNode, FunctionCallNode, IdentifierNode,
    IntLiteralNode, FloatLiteralNode, StringLiteralNode, BoolLiteralNode, ListLiteralNode,
    ExpressionStatementNode,
)


def parse(source: str) -> ProgramNode:
    tokens = Lexer(source, "<test>").tokenize()
    return Parser(tokens, "<test>").parse()


def first_stmt(source: str):
    return parse(source).body[0]


# ---------------------------------------------------------------------------
# Top-level program
# ---------------------------------------------------------------------------

class TestProgram:
    def test_empty_program(self):
        prog = parse("")
        assert isinstance(prog, ProgramNode)
        assert prog.body == []

    def test_program_with_multiple_stmts(self):
        prog = parse("let x = 1\nlet y = 2\n")
        assert len(prog.body) == 2


# ---------------------------------------------------------------------------
# Variable assignment
# ---------------------------------------------------------------------------

class TestAssignment:
    def test_custom_bind_assignment(self):
        node = first_stmt("bind x = 42")
        assert isinstance(node, AssignNode)
        assert node.name == "x"
        assert isinstance(node.value, IntLiteralNode)

    def test_int_assignment(self):
        node = first_stmt("let x = 42")
        assert isinstance(node, AssignNode)
        assert node.name == "x"
        assert isinstance(node.value, IntLiteralNode)
        assert node.value.value == 42

    def test_string_assignment(self):
        node = first_stmt('let msg = "hello"')
        assert isinstance(node, AssignNode)
        assert node.name == "msg"
        assert isinstance(node.value, StringLiteralNode)
        assert node.value.raw == "hello"

    def test_bool_assignment(self):
        node = first_stmt("let flag = true")
        assert isinstance(node, AssignNode)
        assert isinstance(node.value, BoolLiteralNode)
        assert node.value.value is True

    def test_float_assignment(self):
        node = first_stmt("let ratio = 1.5")
        assert isinstance(node, AssignNode)
        assert isinstance(node.value, FloatLiteralNode)
        assert node.value.value == 1.5

    def test_list_assignment(self):
        node = first_stmt('let items = ["a", "b", 1]')
        assert isinstance(node, AssignNode)
        assert isinstance(node.value, ListLiteralNode)
        assert len(node.value.elements) == 3


# ---------------------------------------------------------------------------
# Task definition
# ---------------------------------------------------------------------------

class TestTaskDefinition:
    def test_custom_simple_job(self):
        src = "job hello =>\n    print(1)\n"
        node = first_stmt(src)
        assert isinstance(node, TaskNode)
        assert node.name == "hello"

    def test_custom_job_with_requires(self):
        src = "job build requires clean =>\n    print(1)\n"
        node = first_stmt(src)
        assert isinstance(node, TaskNode)
        assert node.dependencies == ["clean"]

    def test_simple_task(self):
        src = "task hello:\n    print(1)\n"
        node = first_stmt(src)
        assert isinstance(node, TaskNode)
        assert node.name == "hello"
        assert node.dependencies == []
        assert len(node.body) == 1

    def test_task_with_dependency(self):
        src = "task build needs clean:\n    print(1)\n"
        node = first_stmt(src)
        assert isinstance(node, TaskNode)
        assert node.dependencies == ["clean"]

    def test_task_with_multiple_dependencies(self):
        src = "task deploy needs build, test:\n    print(1)\n"
        node = first_stmt(src)
        assert isinstance(node, TaskNode)
        assert node.dependencies == ["build", "test"]

    def test_task_body_has_statements(self):
        src = 'task foo:\n    let x = 1\n    print(x)\n'
        node = first_stmt(src)
        assert isinstance(node, TaskNode)
        assert len(node.body) == 2


# ---------------------------------------------------------------------------
# If / elif / else
# ---------------------------------------------------------------------------

class TestIf:
    def test_custom_when_elsewhen_otherwise(self):
        src = (
            "when x > 10 =>\n    print(1)\n"
            "elsewhen x > 5 =>\n    print(2)\n"
            "otherwise =>\n    print(3)\n"
        )
        node = first_stmt(src)
        assert isinstance(node, IfNode)
        assert len(node.elif_clauses) == 1
        assert len(node.else_body) == 1

    def test_simple_if(self):
        src = "if x > 0:\n    print(x)\n"
        node = first_stmt(src)
        assert isinstance(node, IfNode)
        assert node.elif_clauses == []
        assert node.else_body == []

    def test_if_else(self):
        src = "if x:\n    print(1)\nelse:\n    print(0)\n"
        node = first_stmt(src)
        assert isinstance(node, IfNode)
        assert len(node.then_body) == 1
        assert len(node.else_body) == 1

    def test_if_elif_else(self):
        src = (
            "if x > 10:\n    print(1)\n"
            "elif x > 5:\n    print(2)\n"
            "else:\n    print(3)\n"
        )
        node = first_stmt(src)
        assert isinstance(node, IfNode)
        assert len(node.elif_clauses) == 1
        assert len(node.else_body) == 1


# ---------------------------------------------------------------------------
# For loop
# ---------------------------------------------------------------------------

class TestFor:
    def test_custom_each_over_loop(self):
        src = "each item over items =>\n    print(item)\n"
        node = first_stmt(src)
        assert isinstance(node, ForNode)
        assert node.variable == "item"

    def test_for_loop(self):
        src = "for item in items:\n    print(item)\n"
        node = first_stmt(src)
        assert isinstance(node, ForNode)
        assert node.variable == "item"
        assert isinstance(node.iterable, IdentifierNode)
        assert node.iterable.name == "items"

    def test_for_inline_list(self):
        src = "for n in [1, 2, 3]:\n    print(n)\n"
        node = first_stmt(src)
        assert isinstance(node, ForNode)
        assert isinstance(node.iterable, ListLiteralNode)


# ---------------------------------------------------------------------------
# While loop
# ---------------------------------------------------------------------------

class TestWhile:
    def test_custom_loop(self):
        src = "loop x > 0 =>\n    bind x = x - 1\n"
        node = first_stmt(src)
        assert isinstance(node, WhileNode)
        assert isinstance(node.condition, BinaryOpNode)

    def test_while_loop(self):
        src = "while x > 0:\n    let x = x - 1\n"
        node = first_stmt(src)
        assert isinstance(node, WhileNode)
        assert isinstance(node.condition, BinaryOpNode)


# ---------------------------------------------------------------------------
# Break / Continue / Return
# ---------------------------------------------------------------------------

class TestControlFlow:
    def test_custom_stop(self):
        src = "each x over items =>\n    stop\n"
        for_node = first_stmt(src)
        assert isinstance(for_node.body[0], BreakNode)

    def test_custom_skip(self):
        src = "each x over items =>\n    skip\n"
        for_node = first_stmt(src)
        assert isinstance(for_node.body[0], ContinueNode)

    def test_custom_give(self):
        src = "job foo =>\n    give 42\n"
        task = first_stmt(src)
        ret = task.body[0]
        assert isinstance(ret, ReturnNode)
        assert isinstance(ret.value, IntLiteralNode)

    def test_break(self):
        src = "for x in items:\n    break\n"
        for_node = first_stmt(src)
        assert isinstance(for_node.body[0], BreakNode)

    def test_continue(self):
        src = "for x in items:\n    continue\n"
        for_node = first_stmt(src)
        assert isinstance(for_node.body[0], ContinueNode)

    def test_return_no_value(self):
        src = "task foo:\n    return\n"
        task = first_stmt(src)
        ret = task.body[0]
        assert isinstance(ret, ReturnNode)
        assert ret.value is None

    def test_return_with_value(self):
        src = "task foo:\n    return 42\n"
        task = first_stmt(src)
        ret = task.body[0]
        assert isinstance(ret, ReturnNode)
        assert isinstance(ret.value, IntLiteralNode)


# ---------------------------------------------------------------------------
# Shell commands
# ---------------------------------------------------------------------------

class TestShell:
    def test_custom_exec_block(self):
        src = "job foo =>\n    exec =>\n        echo line1\n        echo line2\n"
        task = first_stmt(src)
        block = task.body[0]
        assert isinstance(block, ShellBlockNode)
        assert len(block.commands) == 2

    def test_shell_line(self):
        src = "task foo:\n    $ echo hello\n"
        task = first_stmt(src)
        shell = task.body[0]
        assert isinstance(shell, ShellCommandNode)
        assert "echo hello" in shell.command

    def test_shell_block(self):
        src = "task foo:\n    shell:\n        echo line1\n        echo line2\n"
        task = first_stmt(src)
        block = task.body[0]
        assert isinstance(block, ShellBlockNode)
        assert len(block.commands) == 2


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------

class TestImport:
    def test_custom_use_statement(self):
        src = 'use "other.codefile"'
        node = first_stmt(src)
        assert isinstance(node, ImportNode)
        assert node.path == "other.codefile"

    def test_import_statement(self):
        src = 'import "other.codefile"'
        node = first_stmt(src)
        assert isinstance(node, ImportNode)
        assert node.path == "other.codefile"


# ---------------------------------------------------------------------------
# Expressions
# ---------------------------------------------------------------------------

class TestExpressions:
    def test_binary_add(self):
        src = "task foo:\n    let x = 1 + 2\n"
        assign = first_stmt(src).body[0]
        assert isinstance(assign.value, BinaryOpNode)
        assert assign.value.op == "+"

    def test_binary_compare(self):
        src = "task foo:\n    let x = a == b\n"
        assign = first_stmt(src).body[0]
        assert isinstance(assign.value, BinaryOpNode)
        assert assign.value.op == "=="

    def test_unary_not(self):
        src = "task foo:\n    let x = not flag\n"
        assign = first_stmt(src).body[0]
        assert isinstance(assign.value, UnaryOpNode)
        assert assign.value.op == "not"

    def test_unary_minus(self):
        src = "task foo:\n    let x = -5\n"
        # -5 is tokenized as a single INT token
        assign = first_stmt(src).body[0]
        assert isinstance(assign.value, IntLiteralNode)
        assert assign.value.value == -5

    def test_function_call(self):
        src = "task foo:\n    print(42)\n"
        task = first_stmt(src)
        stmt = task.body[0]
        assert isinstance(stmt, ExpressionStatementNode)
        call = stmt.expr
        assert isinstance(call, FunctionCallNode)
        assert call.name == "print"
        assert len(call.args) == 1

    def test_function_call_no_args(self):
        src = "task foo:\n    let p = platform()\n"
        assign = first_stmt(src).body[0]
        call = assign.value
        assert isinstance(call, FunctionCallNode)
        assert call.name == "platform"
        assert call.args == []

    def test_logical_and_or(self):
        src = "task foo:\n    let r = a and b or c\n"
        assign = first_stmt(src).body[0]
        assert isinstance(assign.value, BinaryOpNode)

    def test_nested_list(self):
        src = 'let x = [1, "two", true]'
        node = first_stmt(src)
        elems = node.value.elements
        assert len(elems) == 3
        assert isinstance(elems[0], IntLiteralNode)
        assert isinstance(elems[1], StringLiteralNode)
        assert isinstance(elems[2], BoolLiteralNode)

    def test_operator_precedence_mul_before_add(self):
        src = "let x = 2 + 3 * 4"
        node = first_stmt(src)
        # Should parse as 2 + (3 * 4)
        top = node.value
        assert isinstance(top, BinaryOpNode)
        assert top.op == "+"
        assert isinstance(top.right, BinaryOpNode)
        assert top.right.op == "*"


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestParseErrors:
    def test_missing_colon_after_task(self):
        with pytest.raises(ParseError):
            parse("task foo\n    print(1)\n")

    def test_missing_colon_after_if(self):
        with pytest.raises(ParseError):
            parse("if x > 0\n    print(x)\n")
