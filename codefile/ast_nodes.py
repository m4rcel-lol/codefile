"""
ast_nodes.py — AST Node Definitions for the Codefile Language

This module defines all Abstract Syntax Tree (AST) node types used by the
Codefile parser and interpreter. Each node is a simple dataclass with typed
fields that map directly to language constructs.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Any


# ---------------------------------------------------------------------------
# Base node
# ---------------------------------------------------------------------------

@dataclass
class Node:
    """Base class for all AST nodes. Stores source location."""
    line: int = 0
    col: int = 0


# ---------------------------------------------------------------------------
# Program / top-level
# ---------------------------------------------------------------------------

@dataclass
class ProgramNode(Node):
    """Root node — the entire source file."""
    body: List[Node] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Declarations
# ---------------------------------------------------------------------------

@dataclass
class AssignNode(Node):
    """Variable declaration/assignment: let name = value"""
    name: str = ""
    value: Optional[Node] = None


@dataclass
class TaskNode(Node):
    """Task definition: task name needs dep1, dep2: body"""
    name: str = ""
    dependencies: List[str] = field(default_factory=list)
    body: List[Node] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Control flow
# ---------------------------------------------------------------------------

@dataclass
class IfNode(Node):
    """
    if condition: then_body
    elif condition: elif_body ...
    else: else_body
    """
    condition: Optional[Node] = None
    then_body: List[Node] = field(default_factory=list)
    elif_clauses: List[tuple] = field(default_factory=list)  # list of (condition, body)
    else_body: List[Node] = field(default_factory=list)


@dataclass
class ForNode(Node):
    """for variable in iterable: body"""
    variable: str = ""
    iterable: Optional[Node] = None
    body: List[Node] = field(default_factory=list)


@dataclass
class WhileNode(Node):
    """while condition: body"""
    condition: Optional[Node] = None
    body: List[Node] = field(default_factory=list)


@dataclass
class BreakNode(Node):
    """break statement inside a loop."""
    pass


@dataclass
class ContinueNode(Node):
    """continue statement inside a loop."""
    pass


@dataclass
class ReturnNode(Node):
    """return [value] statement."""
    value: Optional[Node] = None


# ---------------------------------------------------------------------------
# Shell execution
# ---------------------------------------------------------------------------

@dataclass
class ShellCommandNode(Node):
    """Inline shell command: $ echo hello"""
    command: str = ""


@dataclass
class ShellBlockNode(Node):
    """
    Multi-line shell block:
        shell:
            echo line1
            echo line2
    """
    commands: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------

@dataclass
class ImportNode(Node):
    """import "other.codefile" """
    path: str = ""


# ---------------------------------------------------------------------------
# Expressions
# ---------------------------------------------------------------------------

@dataclass
class BinaryOpNode(Node):
    """Binary operation: left op right (e.g. x + 1, a == b)"""
    op: str = ""
    left: Optional[Node] = None
    right: Optional[Node] = None


@dataclass
class UnaryOpNode(Node):
    """Unary operation: -x, not x"""
    op: str = ""
    operand: Optional[Node] = None


@dataclass
class FunctionCallNode(Node):
    """Function/built-in call: name(arg1, arg2)"""
    name: str = ""
    args: List[Node] = field(default_factory=list)


@dataclass
class IdentifierNode(Node):
    """Variable reference: name"""
    name: str = ""


@dataclass
class IntLiteralNode(Node):
    """Integer literal: 42"""
    value: int = 0


@dataclass
class FloatLiteralNode(Node):
    """Float literal: 3.14"""
    value: float = 0.0


@dataclass
class StringLiteralNode(Node):
    """String literal with optional interpolation: "hello ${name}" """
    raw: str = ""          # raw string value (not yet interpolated)


@dataclass
class BoolLiteralNode(Node):
    """Boolean literal: true / false"""
    value: bool = False


@dataclass
class ListLiteralNode(Node):
    """List literal: [1, "two", true]"""
    elements: List[Node] = field(default_factory=list)


@dataclass
class ExpressionStatementNode(Node):
    """A standalone expression used as a statement (e.g. a bare function call)."""
    expr: Optional[Node] = None
