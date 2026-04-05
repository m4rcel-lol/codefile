"""
parser.py — Recursive-Descent Parser for the Codefile Language

Takes a token stream (from lexer.py) and produces an Abstract Syntax Tree
(AST) whose node types are defined in ast_nodes.py.

Grammar overview: see SPEC.md section 16.
"""

from __future__ import annotations
from typing import List, Optional

from .lexer import Token, TT, LexError
from .ast_nodes import (
    Node, ProgramNode, AssignNode, TaskNode, IfNode, ForNode, WhileNode,
    BreakNode, ContinueNode, ReturnNode, ShellCommandNode, ShellBlockNode,
    ImportNode, BinaryOpNode, UnaryOpNode, FunctionCallNode, IdentifierNode,
    IntLiteralNode, StringLiteralNode, BoolLiteralNode, ListLiteralNode,
    ExpressionStatementNode,
)


# ---------------------------------------------------------------------------
# Parser error
# ---------------------------------------------------------------------------

class ParseError(Exception):
    def __init__(self, msg: str, line: int, col: int, filename: str = "<input>"):
        self.msg = msg
        self.line = line
        self.col = col
        self.filename = filename
        super().__init__(f"ParseError [{filename}:{line}:{col}]: {msg}")


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class Parser:
    """
    Recursive-descent parser for Codefile.

    The parser consumes a flat token list and builds a nested AST.
    Indentation structure is already encoded as INDENT/DEDENT tokens
    by the lexer, so the parser does not need to track column positions
    for block detection.
    """

    def __init__(self, tokens: List[Token], filename: str = "<input>"):
        self.tokens = tokens
        self.pos = 0
        self.filename = filename

    # ------------------------------------------------------------------
    # Token stream helpers
    # ------------------------------------------------------------------

    @property
    def current(self) -> Token:
        return self.tokens[self.pos]

    def peek(self, offset: int = 1) -> Token:
        idx = self.pos + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return self.tokens[-1]  # EOF

    def advance(self) -> Token:
        tok = self.tokens[self.pos]
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return tok

    def expect(self, tt: TT) -> Token:
        tok = self.current
        if tok.type != tt:
            raise ParseError(
                f"Expected {tt.name}, got {tok.type.name} ({tok.value!r})",
                tok.line, tok.col, self.filename
            )
        return self.advance()

    def match(self, *types: TT) -> bool:
        return self.current.type in types

    def skip_newlines(self):
        while self.current.type == TT.NEWLINE:
            self.advance()

    # ------------------------------------------------------------------
    # Top-level
    # ------------------------------------------------------------------

    def parse(self) -> ProgramNode:
        """Parse the entire program and return the root ProgramNode."""
        body = []
        self.skip_newlines()
        while not self.match(TT.EOF):
            stmt = self._parse_statement()
            if stmt is not None:
                body.append(stmt)
            self.skip_newlines()
        return ProgramNode(body=body, line=1, col=1)

    # ------------------------------------------------------------------
    # Statements
    # ------------------------------------------------------------------

    def _parse_statement(self) -> Optional[Node]:
        """Dispatch to the appropriate statement parser."""
        tok = self.current

        if tok.type == TT.TASK:
            return self._parse_task()
        if tok.type == TT.LET:
            return self._parse_assignment()
        if tok.type == TT.IF:
            return self._parse_if()
        if tok.type == TT.FOR:
            return self._parse_for()
        if tok.type == TT.WHILE:
            return self._parse_while()
        if tok.type == TT.BREAK:
            self.advance()
            self._consume_newline()
            return BreakNode(line=tok.line, col=tok.col)
        if tok.type == TT.CONTINUE:
            self.advance()
            self._consume_newline()
            return ContinueNode(line=tok.line, col=tok.col)
        if tok.type == TT.RETURN:
            return self._parse_return()
        if tok.type == TT.SHELL_LINE:
            return self._parse_shell_line()
        if tok.type == TT.SHELL:
            return self._parse_shell_block()
        if tok.type == TT.IMPORT:
            return self._parse_import()
        if tok.type in (TT.NEWLINE, TT.DEDENT, TT.INDENT):
            self.advance()
            return None

        # Fallback: expression statement (e.g. bare function call)
        return self._parse_expr_stmt()

    def _consume_newline(self):
        """Consume optional trailing NEWLINE."""
        if self.current.type == TT.NEWLINE:
            self.advance()

    def _parse_block(self) -> List[Node]:
        """Parse an indented block of statements."""
        self.expect(TT.INDENT)
        stmts = []
        self.skip_newlines()
        while not self.match(TT.DEDENT, TT.EOF):
            stmt = self._parse_statement()
            if stmt is not None:
                stmts.append(stmt)
            self.skip_newlines()
        if self.current.type == TT.DEDENT:
            self.advance()
        return stmts

    # ------------------------------------------------------------------
    # Task
    # ------------------------------------------------------------------

    def _parse_task(self) -> TaskNode:
        tok = self.expect(TT.TASK)
        name_tok = self.expect(TT.IDENT)
        deps = []
        if self.current.type == TT.NEEDS:
            self.advance()
            deps.append(self.expect(TT.IDENT).value)
            while self.current.type == TT.COMMA:
                self.advance()
                deps.append(self.expect(TT.IDENT).value)
        if self.current.type in (TT.COLON, TT.FATARROW):
            self.advance()
        else:
            self.expect(TT.COLON)
        self._consume_newline()
        body = self._parse_block()
        return TaskNode(name=name_tok.value, dependencies=deps, body=body,
                        line=tok.line, col=tok.col)

    # ------------------------------------------------------------------
    # Variable assignment
    # ------------------------------------------------------------------

    def _parse_assignment(self) -> AssignNode:
        tok = self.expect(TT.LET)
        name_tok = self.expect(TT.IDENT)
        self.expect(TT.EQ)
        value = self._parse_expr()
        self._consume_newline()
        return AssignNode(name=name_tok.value, value=value,
                          line=tok.line, col=tok.col)

    # ------------------------------------------------------------------
    # If / elif / else
    # ------------------------------------------------------------------

    def _parse_if(self) -> IfNode:
        tok = self.expect(TT.IF)
        cond = self._parse_expr()
        if self.current.type in (TT.COLON, TT.FATARROW):
            self.advance()
        else:
            self.expect(TT.COLON)
        self._consume_newline()
        then_body = self._parse_block()

        elif_clauses = []
        while self.current.type == TT.ELIF:
            self.advance()
            elif_cond = self._parse_expr()
            if self.current.type in (TT.COLON, TT.FATARROW):
                self.advance()
            else:
                self.expect(TT.COLON)
            self._consume_newline()
            elif_body = self._parse_block()
            elif_clauses.append((elif_cond, elif_body))

        else_body = []
        if self.current.type == TT.ELSE:
            self.advance()
            if self.current.type in (TT.COLON, TT.FATARROW):
                self.advance()
            else:
                self.expect(TT.COLON)
            self._consume_newline()
            else_body = self._parse_block()

        return IfNode(condition=cond, then_body=then_body,
                      elif_clauses=elif_clauses, else_body=else_body,
                      line=tok.line, col=tok.col)

    # ------------------------------------------------------------------
    # For loop
    # ------------------------------------------------------------------

    def _parse_for(self) -> ForNode:
        tok = self.expect(TT.FOR)
        var_tok = self.expect(TT.IDENT)
        self.expect(TT.IN)
        iterable = self._parse_expr()
        if self.current.type in (TT.COLON, TT.FATARROW):
            self.advance()
        else:
            self.expect(TT.COLON)
        self._consume_newline()
        body = self._parse_block()
        return ForNode(variable=var_tok.value, iterable=iterable, body=body,
                       line=tok.line, col=tok.col)

    # ------------------------------------------------------------------
    # While loop
    # ------------------------------------------------------------------

    def _parse_while(self) -> WhileNode:
        tok = self.expect(TT.WHILE)
        cond = self._parse_expr()
        if self.current.type in (TT.COLON, TT.FATARROW):
            self.advance()
        else:
            self.expect(TT.COLON)
        self._consume_newline()
        body = self._parse_block()
        return WhileNode(condition=cond, body=body, line=tok.line, col=tok.col)

    # ------------------------------------------------------------------
    # Return
    # ------------------------------------------------------------------

    def _parse_return(self) -> ReturnNode:
        tok = self.expect(TT.RETURN)
        value = None
        if not self.match(TT.NEWLINE, TT.EOF):
            value = self._parse_expr()
        self._consume_newline()
        return ReturnNode(value=value, line=tok.line, col=tok.col)

    # ------------------------------------------------------------------
    # Shell commands
    # ------------------------------------------------------------------

    def _parse_shell_line(self) -> ShellCommandNode:
        tok = self.advance()  # SHELL_LINE token
        self._consume_newline()
        return ShellCommandNode(command=tok.value, line=tok.line, col=tok.col)

    def _parse_shell_block(self) -> ShellBlockNode:
        tok = self.expect(TT.SHELL)
        if self.current.type in (TT.COLON, TT.FATARROW):
            self.advance()
        else:
            self.expect(TT.COLON)
        self._consume_newline()
        self.expect(TT.INDENT)
        commands = []
        while not self.match(TT.DEDENT, TT.EOF):
            if self.current.type == TT.SHELL_LINE:
                commands.append(self.advance().value)
            elif self.current.type == TT.NEWLINE:
                self.advance()
            else:
                # Treat any identifier/string token line as a raw shell line
                # by collecting everything until NEWLINE
                parts = []
                while not self.match(TT.NEWLINE, TT.DEDENT, TT.EOF):
                    parts.append(str(self.advance().value))
                commands.append(' '.join(parts))
                self._consume_newline()
        if self.current.type == TT.DEDENT:
            self.advance()
        return ShellBlockNode(commands=commands, line=tok.line, col=tok.col)

    # ------------------------------------------------------------------
    # Import
    # ------------------------------------------------------------------

    def _parse_import(self) -> ImportNode:
        tok = self.expect(TT.IMPORT)
        path_tok = self.expect(TT.STRING)
        self._consume_newline()
        return ImportNode(path=path_tok.value, line=tok.line, col=tok.col)

    # ------------------------------------------------------------------
    # Expression statement
    # ------------------------------------------------------------------

    def _parse_expr_stmt(self) -> ExpressionStatementNode:
        tok = self.current
        expr = self._parse_expr()
        self._consume_newline()
        return ExpressionStatementNode(expr=expr, line=tok.line, col=tok.col)

    # ------------------------------------------------------------------
    # Expressions — precedence climbing
    # ------------------------------------------------------------------

    def _parse_expr(self) -> Node:
        return self._parse_or()

    def _parse_or(self) -> Node:
        left = self._parse_and()
        while self.current.type == TT.OR:
            op_tok = self.advance()
            right = self._parse_and()
            left = BinaryOpNode(op='or', left=left, right=right,
                                line=op_tok.line, col=op_tok.col)
        return left

    def _parse_and(self) -> Node:
        left = self._parse_not()
        while self.current.type == TT.AND:
            op_tok = self.advance()
            right = self._parse_not()
            left = BinaryOpNode(op='and', left=left, right=right,
                                line=op_tok.line, col=op_tok.col)
        return left

    def _parse_not(self) -> Node:
        if self.current.type == TT.NOT:
            op_tok = self.advance()
            operand = self._parse_not()
            return UnaryOpNode(op='not', operand=operand,
                               line=op_tok.line, col=op_tok.col)
        return self._parse_compare()

    def _parse_compare(self) -> Node:
        left = self._parse_add()
        cmp_ops = {TT.EQEQ: '==', TT.NEQ: '!=', TT.LT: '<',
                   TT.GT: '>', TT.LTE: '<=', TT.GTE: '>='}
        while self.current.type in cmp_ops:
            op_tok = self.advance()
            right = self._parse_add()
            left = BinaryOpNode(op=cmp_ops[op_tok.type], left=left, right=right,
                                line=op_tok.line, col=op_tok.col)
        return left

    def _parse_add(self) -> Node:
        left = self._parse_mul()
        while self.current.type in (TT.PLUS, TT.MINUS):
            op_tok = self.advance()
            right = self._parse_mul()
            left = BinaryOpNode(op=op_tok.value, left=left, right=right,
                                line=op_tok.line, col=op_tok.col)
        return left

    def _parse_mul(self) -> Node:
        left = self._parse_unary()
        while self.current.type in (TT.STAR, TT.SLASH):
            op_tok = self.advance()
            right = self._parse_unary()
            left = BinaryOpNode(op=op_tok.value, left=left, right=right,
                                line=op_tok.line, col=op_tok.col)
        return left

    def _parse_unary(self) -> Node:
        if self.current.type == TT.MINUS:
            op_tok = self.advance()
            operand = self._parse_unary()
            return UnaryOpNode(op='-', operand=operand,
                               line=op_tok.line, col=op_tok.col)
        return self._parse_primary()

    def _parse_primary(self) -> Node:
        tok = self.current

        # Integer literal
        if tok.type == TT.INT:
            self.advance()
            return IntLiteralNode(value=tok.value, line=tok.line, col=tok.col)

        # String literal
        if tok.type == TT.STRING:
            self.advance()
            return StringLiteralNode(raw=tok.value, line=tok.line, col=tok.col)

        # Boolean literal
        if tok.type == TT.BOOL:
            self.advance()
            return BoolLiteralNode(value=tok.value, line=tok.line, col=tok.col)

        # true / false keywords (mapped to BOOL in lexer, but keep here as safety)
        if tok.type in (TT.TRUE, TT.FALSE):
            self.advance()
            return BoolLiteralNode(value=(tok.type == TT.TRUE),
                                   line=tok.line, col=tok.col)

        # List literal
        if tok.type == TT.LBRACKET:
            return self._parse_list()

        # Parenthesised expression
        if tok.type == TT.LPAREN:
            self.advance()
            expr = self._parse_expr()
            self.expect(TT.RPAREN)
            return expr

        # Identifier or function call
        if tok.type == TT.IDENT:
            self.advance()
            if self.current.type == TT.LPAREN:
                return self._parse_call(tok)
            return IdentifierNode(name=tok.value, line=tok.line, col=tok.col)

        raise ParseError(
            f"Unexpected token {tok.type.name} ({tok.value!r}) in expression",
            tok.line, tok.col, self.filename
        )

    def _parse_list(self) -> ListLiteralNode:
        tok = self.expect(TT.LBRACKET)
        elements = []
        if self.current.type != TT.RBRACKET:
            elements.append(self._parse_expr())
            while self.current.type == TT.COMMA:
                self.advance()
                if self.current.type == TT.RBRACKET:
                    break
                elements.append(self._parse_expr())
        self.expect(TT.RBRACKET)
        return ListLiteralNode(elements=elements, line=tok.line, col=tok.col)

    def _parse_call(self, name_tok: Token) -> FunctionCallNode:
        self.expect(TT.LPAREN)
        args = []
        if self.current.type != TT.RPAREN:
            args.append(self._parse_expr())
            while self.current.type == TT.COMMA:
                self.advance()
                if self.current.type == TT.RPAREN:
                    break
                args.append(self._parse_expr())
        self.expect(TT.RPAREN)
        return FunctionCallNode(name=name_tok.value, args=args,
                                line=name_tok.line, col=name_tok.col)
