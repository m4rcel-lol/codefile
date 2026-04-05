"""
interpreter.py — Tree-Walking Interpreter for the Codefile Language

Evaluates an AST produced by parser.py. Responsibilities:
  - Resolve and execute task dependency graphs (topological sort + cycle detection)
  - Evaluate all expressions and statements
  - Execute shell commands via subprocess, streaming output live
  - Manage a scoped variable environment
  - Handle runtime errors with file/line/column info
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .ast_nodes import (
    Node, ProgramNode, AssignNode, TaskNode, IfNode, ForNode, WhileNode,
    BreakNode, ContinueNode, ReturnNode, ShellCommandNode, ShellBlockNode,
    ImportNode, BinaryOpNode, UnaryOpNode, FunctionCallNode, IdentifierNode,
    IntLiteralNode, StringLiteralNode, BoolLiteralNode, ListLiteralNode,
    ExpressionStatementNode,
)
from .stdlib import BUILTINS


# ---------------------------------------------------------------------------
# Runtime exceptions (used for control flow)
# ---------------------------------------------------------------------------

class _BreakSignal(Exception):
    pass

class _ContinueSignal(Exception):
    pass

class _ReturnSignal(Exception):
    def __init__(self, value: Any):
        self.value = value


# ---------------------------------------------------------------------------
# Public error class
# ---------------------------------------------------------------------------

class RuntimeError_(Exception):
    """Runtime error with location info."""
    def __init__(self, msg: str, line: int = 0, col: int = 0,
                 filename: str = "<input>"):
        self.msg = msg
        self.line = line
        self.col = col
        self.filename = filename
        super().__init__(f"Error [{filename}:{line}:{col}]: {msg}")


# ---------------------------------------------------------------------------
# Environment (scoped variable store)
# ---------------------------------------------------------------------------

class Environment:
    """Hierarchical variable scope."""

    def __init__(self, parent: Optional[Environment] = None):
        self._vars: Dict[str, Any] = {}
        self.parent = parent

    def get(self, name: str) -> Any:
        if name in self._vars:
            return self._vars[name]
        if self.parent:
            return self.parent.get(name)
        raise KeyError(name)

    def set(self, name: str, value: Any):
        """Set in the nearest scope that already owns the name, else here."""
        if name in self._vars or self.parent is None:
            self._vars[name] = value
        else:
            # Check if parent chain has it
            scope = self.parent
            while scope is not None:
                if name in scope._vars:
                    scope._vars[name] = value
                    return
                scope = scope.parent
            # Not found anywhere — create in current scope
            self._vars[name] = value

    def define(self, name: str, value: Any):
        """Always define in the current scope (let)."""
        self._vars[name] = value

    def child(self) -> Environment:
        return Environment(parent=self)


# ---------------------------------------------------------------------------
# Interpreter
# ---------------------------------------------------------------------------

class Interpreter:
    """
    Tree-walking interpreter for the Codefile language.

    Usage:
        interp = Interpreter(filename="hello.codefile")
        interp.load(ast)            # load and index top-level declarations
        interp.run_task("default")  # execute a task by name
    """

    def __init__(self, filename: str = "<input>"):
        self.filename = filename
        self.global_env = Environment()
        # Register built-in functions
        for name, fn in BUILTINS.items():
            self.global_env.define(name, fn)

        self.tasks: Dict[str, TaskNode] = {}
        self._imported_files: Set[str] = set()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load(self, program: ProgramNode):
        """
        First pass: collect all task definitions and evaluate top-level
        variable assignments and imports.
        """
        for node in program.body:
            if isinstance(node, ImportNode):
                self._handle_import(node)
            elif isinstance(node, TaskNode):
                self.tasks[node.name] = node
            elif isinstance(node, AssignNode):
                value = self._eval(node.value, self.global_env)
                self.global_env.define(node.name, value)

    def _handle_import(self, node: ImportNode):
        """Load and merge another .codefile."""
        import_path = Path(self.filename).parent / node.path
        abs_path = str(import_path.resolve())
        if abs_path in self._imported_files:
            return  # already imported
        self._imported_files.add(abs_path)

        if not import_path.exists():
            raise RuntimeError_(
                f"import: file not found: {node.path}",
                node.line, node.col, self.filename
            )

        source = import_path.read_text(encoding='utf-8')
        from .lexer import Lexer
        from .parser import Parser
        tokens = Lexer(source, str(import_path)).tokenize()
        sub_ast = Parser(tokens, str(import_path)).parse()

        # Temporarily switch filename context
        old_filename = self.filename
        self.filename = str(import_path)
        self.load(sub_ast)
        self.filename = old_filename

    # ------------------------------------------------------------------
    # Task execution
    # ------------------------------------------------------------------

    def run_task(self, task_name: str):
        """Execute a task and all its dependencies in topological order."""
        if task_name not in self.tasks:
            available = ', '.join(self.tasks.keys()) or '(none)'
            raise RuntimeError_(
                f"Task '{task_name}' not found. Available tasks: {available}",
                0, 0, self.filename
            )

        order = self._resolve_dependencies(task_name)
        for name in order:
            task = self.tasks[name]
            self._exec_task(task)

    def _resolve_dependencies(self, start: str) -> List[str]:
        """
        Topological sort of the dependency graph starting from `start`.
        Raises RuntimeError_ on circular dependencies.
        """
        order: List[str] = []
        visited: Set[str] = set()
        in_stack: Set[str] = set()

        def visit(name: str):
            if name in in_stack:
                cycle = ' -> '.join(list(in_stack) + [name])
                raise RuntimeError_(
                    f"Circular task dependency detected: {cycle}",
                    0, 0, self.filename
                )
            if name in visited:
                return
            if name not in self.tasks:
                raise RuntimeError_(
                    f"Unknown task dependency: '{name}'",
                    0, 0, self.filename
                )
            in_stack.add(name)
            for dep in self.tasks[name].dependencies:
                visit(dep)
            in_stack.discard(name)
            visited.add(name)
            order.append(name)

        visit(start)
        return order

    def _exec_task(self, task: TaskNode):
        """Execute the body of a single task."""
        env = self.global_env.child()
        try:
            self._exec_block(task.body, env)
        except _ReturnSignal:
            pass  # return from task body is fine

    # ------------------------------------------------------------------
    # Block / statement execution
    # ------------------------------------------------------------------

    def _exec_block(self, stmts: List[Node], env: Environment):
        for stmt in stmts:
            self._exec_stmt(stmt, env)

    def _exec_stmt(self, node: Node, env: Environment):
        """Dispatch to the appropriate execution method."""
        if isinstance(node, AssignNode):
            value = self._eval(node.value, env)
            # Use set() so that re-assigning an existing variable updates it
            # in the nearest enclosing scope that already owns it (like Python).
            # If no scope owns it yet, set() creates it in the current scope.
            env.set(node.name, value)

        elif isinstance(node, IfNode):
            self._exec_if(node, env)

        elif isinstance(node, ForNode):
            self._exec_for(node, env)

        elif isinstance(node, WhileNode):
            self._exec_while(node, env)

        elif isinstance(node, ShellCommandNode):
            self._exec_shell(node.command, env, node.line)

        elif isinstance(node, ShellBlockNode):
            for cmd in node.commands:
                self._exec_shell(cmd, env, node.line)

        elif isinstance(node, BreakNode):
            raise _BreakSignal()

        elif isinstance(node, ContinueNode):
            raise _ContinueSignal()

        elif isinstance(node, ReturnNode):
            value = self._eval(node.value, env) if node.value else None
            raise _ReturnSignal(value)

        elif isinstance(node, ExpressionStatementNode):
            self._eval(node.expr, env)

        elif isinstance(node, TaskNode):
            # Nested task definition during execution — just register it
            self.tasks[node.name] = node

        elif isinstance(node, ImportNode):
            self._handle_import(node)

        # Ignore None nodes silently

    def _exec_if(self, node: IfNode, env: Environment):
        if self._truthy(self._eval(node.condition, env)):
            self._exec_block(node.then_body, env.child())
            return
        for elif_cond, elif_body in node.elif_clauses:
            if self._truthy(self._eval(elif_cond, env)):
                self._exec_block(elif_body, env.child())
                return
        if node.else_body:
            self._exec_block(node.else_body, env.child())

    def _exec_for(self, node: ForNode, env: Environment):
        iterable = self._eval(node.iterable, env)
        if not isinstance(iterable, (list, str)):
            raise RuntimeError_(
                f"'for' loop requires a list or string, got {type(iterable).__name__}",
                node.line, node.col, self.filename
            )
        for item in iterable:
            loop_env = env.child()
            loop_env.define(node.variable, item)
            try:
                self._exec_block(node.body, loop_env)
            except _BreakSignal:
                break
            except _ContinueSignal:
                continue

    def _exec_while(self, node: WhileNode, env: Environment):
        while self._truthy(self._eval(node.condition, env)):
            loop_env = env.child()
            try:
                self._exec_block(node.body, loop_env)
            except _BreakSignal:
                break
            except _ContinueSignal:
                continue

    # ------------------------------------------------------------------
    # Shell execution
    # ------------------------------------------------------------------

    def _exec_shell(self, command: str, env: Environment, line: int = 0):
        """Execute a shell command, streaming output live."""
        interpolated = self._interpolate(command, env)

        if os.name == 'nt':
            # Windows: use cmd.exe
            proc = subprocess.run(
                interpolated,
                shell=True,
            )
        else:
            # Linux/Unix: use $SHELL or /bin/sh
            shell_bin = os.environ.get('SHELL', '/bin/sh')
            proc = subprocess.run(
                interpolated,
                shell=True,
                executable=shell_bin,
            )

        if proc.returncode != 0:
            raise RuntimeError_(
                f"Shell command failed (exit {proc.returncode}): {interpolated}",
                line, 0, self.filename
            )

    # ------------------------------------------------------------------
    # Expression evaluation
    # ------------------------------------------------------------------

    def _eval(self, node: Node, env: Environment) -> Any:
        """Evaluate an expression node and return its Python value."""

        if isinstance(node, IntLiteralNode):
            return node.value

        if isinstance(node, BoolLiteralNode):
            return node.value

        if isinstance(node, StringLiteralNode):
            return self._interpolate(node.raw, env)

        if isinstance(node, ListLiteralNode):
            return [self._eval(e, env) for e in node.elements]

        if isinstance(node, IdentifierNode):
            try:
                return env.get(node.name)
            except KeyError:
                raise RuntimeError_(
                    f"Undefined variable '{node.name}'",
                    node.line, node.col, self.filename
                )

        if isinstance(node, FunctionCallNode):
            return self._call_function(node, env)

        if isinstance(node, BinaryOpNode):
            return self._eval_binary(node, env)

        if isinstance(node, UnaryOpNode):
            return self._eval_unary(node, env)

        raise RuntimeError_(
            f"Cannot evaluate node type {type(node).__name__}",
            getattr(node, 'line', 0), getattr(node, 'col', 0), self.filename
        )

    def _eval_binary(self, node: BinaryOpNode, env: Environment) -> Any:
        # Short-circuit for 'and' / 'or'
        if node.op == 'and':
            left = self._eval(node.left, env)
            return left if not self._truthy(left) else self._eval(node.right, env)
        if node.op == 'or':
            left = self._eval(node.left, env)
            return left if self._truthy(left) else self._eval(node.right, env)

        left = self._eval(node.left, env)
        right = self._eval(node.right, env)

        try:
            if node.op == '+':
                if isinstance(left, str) or isinstance(right, str):
                    return self._to_str(left) + self._to_str(right)
                if isinstance(left, list):
                    return left + (right if isinstance(right, list) else [right])
                return left + right
            if node.op == '-':  return left - right
            if node.op == '*':  return left * right
            if node.op == '/':
                if right == 0:
                    raise RuntimeError_(
                        "Division by zero", node.line, node.col, self.filename
                    )
                return left // right if isinstance(left, int) else left / right
            if node.op == '==': return left == right
            if node.op == '!=': return left != right
            if node.op == '<':  return left < right
            if node.op == '>':  return left > right
            if node.op == '<=': return left <= right
            if node.op == '>=': return left >= right
        except TypeError as exc:
            raise RuntimeError_(
                f"Type error in '{node.op}': {exc}",
                node.line, node.col, self.filename
            ) from exc

        raise RuntimeError_(
            f"Unknown operator: {node.op}", node.line, node.col, self.filename
        )

    def _eval_unary(self, node: UnaryOpNode, env: Environment) -> Any:
        operand = self._eval(node.operand, env)
        if node.op == '-':
            return -operand
        if node.op == 'not':
            return not self._truthy(operand)
        raise RuntimeError_(
            f"Unknown unary operator: {node.op}", node.line, node.col, self.filename
        )

    def _call_function(self, node: FunctionCallNode, env: Environment) -> Any:
        """Look up and call a built-in or user-defined function."""
        try:
            fn = env.get(node.name)
        except KeyError:
            raise RuntimeError_(
                f"Undefined function '{node.name}'",
                node.line, node.col, self.filename
            )

        if not callable(fn):
            raise RuntimeError_(
                f"'{node.name}' is not a function",
                node.line, node.col, self.filename
            )

        args = [self._eval(a, env) for a in node.args]
        try:
            return fn(*args)
        except SystemExit:
            raise
        except TypeError as exc:
            raise RuntimeError_(
                f"Wrong arguments for '{node.name}': {exc}",
                node.line, node.col, self.filename
            ) from exc
        except Exception as exc:
            raise RuntimeError_(
                f"Error in '{node.name}': {exc}",
                node.line, node.col, self.filename
            ) from exc

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _truthy(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        if isinstance(value, str):
            return len(value) > 0
        if isinstance(value, list):
            return len(value) > 0
        if value is None:
            return False
        return True

    @staticmethod
    def _to_str(value: Any) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)

    def _interpolate(self, template: str, env: Environment) -> str:
        """
        Perform ${variable} and ${expression} interpolation in strings and
        shell commands.  Only simple identifier lookups are supported inside
        ${...}.
        """
        def replace_match(m):
            key = m.group(1).strip()
            try:
                val = env.get(key)
                return self._to_str(val)
            except KeyError:
                # Leave unresolved references as empty string rather than crashing
                return ''

        return re.sub(r'\$\{([^}]+)\}', replace_match, template)

    # ------------------------------------------------------------------
    # Inspection helpers (for CLI commands)
    # ------------------------------------------------------------------

    def list_tasks(self) -> List[str]:
        """Return sorted list of task names."""
        return sorted(self.tasks.keys())

    def task_graph(self) -> Dict[str, List[str]]:
        """Return {task_name: [deps]} mapping."""
        return {name: list(t.dependencies) for name, t in self.tasks.items()}
