"""
tests/test_interpreter.py — Unit tests for the Codefile interpreter.
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from codefile import load_file, Interpreter, RuntimeError_
from codefile.lexer import Lexer
from codefile.parser import Parser


def make_interp(source: str, filename: str = "<test>") -> Interpreter:
    tokens = Lexer(source, filename).tokenize()
    ast = Parser(tokens, filename).parse()
    interp = Interpreter(filename=filename)
    interp.load(ast)
    return interp


def run_task(source: str, task: str = "default") -> None:
    interp = make_interp(source)
    interp.run_task(task)


# ---------------------------------------------------------------------------
# Basic task execution
# ---------------------------------------------------------------------------

class TestTaskExecution:
    def test_custom_job_runs(self, capsys):
        src = 'job default =>\n    print("hello")\n'
        run_task(src)
        out = capsys.readouterr().out
        assert "hello" in out

    def test_custom_requires_runs(self, capsys):
        src = (
            'job setup =>\n    print("setup")\n'
            'job default requires setup =>\n    print("run")\n'
        )
        run_task(src)
        out = capsys.readouterr().out
        assert "setup" in out
        assert "run" in out

    def test_simple_task_runs(self, capsys):
        src = 'task default:\n    print("hello")\n'
        run_task(src)
        out = capsys.readouterr().out
        assert "hello" in out

    def test_task_not_found(self):
        src = 'task foo:\n    print("x")\n'
        interp = make_interp(src)
        with pytest.raises(RuntimeError_):
            interp.run_task("missing")

    def test_task_with_dep(self, capsys):
        src = (
            'task setup:\n    print("setup")\n'
            'task default needs setup:\n    print("run")\n'
        )
        run_task(src)
        out = capsys.readouterr().out
        assert "setup" in out
        assert "run" in out

    def test_dep_order(self, capsys):
        src = (
            'task a:\n    print("a")\n'
            'task b needs a:\n    print("b")\n'
            'task c needs b:\n    print("c")\n'
        )
        run_task(src, "c")
        out = capsys.readouterr().out
        assert out.index("a") < out.index("b") < out.index("c")

    def test_circular_dep_raises(self):
        src = (
            'task a needs b:\n    print("a")\n'
            'task b needs a:\n    print("b")\n'
        )
        interp = make_interp(src)
        with pytest.raises(RuntimeError_):
            interp.run_task("a")

    def test_dep_not_found_raises(self):
        src = 'task foo needs missing:\n    print("x")\n'
        interp = make_interp(src)
        with pytest.raises(RuntimeError_):
            interp.run_task("foo")


# ---------------------------------------------------------------------------
# Variables
# ---------------------------------------------------------------------------

class TestVariables:
    def test_custom_bind_variable(self, capsys):
        src = 'bind x = 42\njob default =>\n    print(x)\n'
        run_task(src)
        assert "42" in capsys.readouterr().out

    def test_int_variable(self, capsys):
        src = 'let x = 42\ntask default:\n    print(x)\n'
        run_task(src)
        assert "42" in capsys.readouterr().out

    def test_string_variable(self, capsys):
        src = 'let msg = "hi"\ntask default:\n    print(msg)\n'
        run_task(src)
        assert "hi" in capsys.readouterr().out

    def test_bool_variable(self, capsys):
        src = 'let flag = true\ntask default:\n    print(flag)\n'
        run_task(src)
        assert "true" in capsys.readouterr().out

    def test_string_interpolation(self, capsys):
        src = 'let name = "World"\ntask default:\n    print("Hello, ${name}!")\n'
        run_task(src)
        assert "Hello, World!" in capsys.readouterr().out

    def test_expression_interpolation(self, capsys):
        src = 'let x = 2\ntask default:\n    print("sum=${x + 3}")\n'
        run_task(src)
        assert "sum=5" in capsys.readouterr().out

    def test_undefined_variable_raises(self):
        src = 'task default:\n    print(undefined_var)\n'
        with pytest.raises(RuntimeError_):
            run_task(src)


# ---------------------------------------------------------------------------
# Arithmetic
# ---------------------------------------------------------------------------

class TestArithmetic:
    def test_addition(self, capsys):
        src = 'task default:\n    let x = 1 + 2\n    print(x)\n'
        run_task(src)
        assert "3" in capsys.readouterr().out

    def test_subtraction(self, capsys):
        src = 'task default:\n    let x = 10 - 3\n    print(x)\n'
        run_task(src)
        assert "7" in capsys.readouterr().out

    def test_multiplication(self, capsys):
        src = 'task default:\n    let x = 6 * 7\n    print(x)\n'
        run_task(src)
        assert "42" in capsys.readouterr().out

    def test_integer_division(self, capsys):
        src = 'task default:\n    let x = 10 / 2\n    print(x)\n'
        run_task(src)
        assert "5" in capsys.readouterr().out

    def test_division_by_zero(self):
        src = 'task default:\n    let x = 1 / 0\n    print(x)\n'
        with pytest.raises(RuntimeError_):
            run_task(src)

    def test_string_concat(self, capsys):
        src = 'task default:\n    let s = "hello" + " world"\n    print(s)\n'
        run_task(src)
        assert "hello world" in capsys.readouterr().out

    def test_float_arithmetic(self, capsys):
        src = 'task default:\n    let x = 1.5 + 2.5\n    print(x)\n'
        run_task(src)
        assert "4.0" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Comparisons and logical operators
# ---------------------------------------------------------------------------

class TestLogic:
    def test_eq_true(self, capsys):
        src = 'task default:\n    print(1 == 1)\n'
        run_task(src)
        assert "true" in capsys.readouterr().out

    def test_eq_false(self, capsys):
        src = 'task default:\n    print(1 == 2)\n'
        run_task(src)
        assert "false" in capsys.readouterr().out

    def test_not(self, capsys):
        src = 'task default:\n    print(not true)\n'
        run_task(src)
        assert "false" in capsys.readouterr().out

    def test_and(self, capsys):
        src = 'task default:\n    print(true and false)\n'
        run_task(src)
        assert "false" in capsys.readouterr().out

    def test_or(self, capsys):
        src = 'task default:\n    print(false or true)\n'
        run_task(src)
        assert "true" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# If / elif / else
# ---------------------------------------------------------------------------

class TestConditionals:
    def test_custom_when_taken(self, capsys):
        src = 'job default =>\n    when true =>\n        print("yes")\n'
        run_task(src)
        assert "yes" in capsys.readouterr().out

    def test_custom_elsewhen_otherwise(self, capsys):
        src = (
            'bind x = 5\n'
            'job default =>\n'
            '    when x > 10 =>\n'
            '        print("big")\n'
            '    elsewhen x > 3 =>\n'
            '        print("medium")\n'
            '    otherwise =>\n'
            '        print("small")\n'
        )
        run_task(src)
        assert "medium" in capsys.readouterr().out

    def test_if_taken(self, capsys):
        src = 'task default:\n    if true:\n        print("yes")\n'
        run_task(src)
        assert "yes" in capsys.readouterr().out

    def test_if_not_taken(self, capsys):
        src = 'task default:\n    if false:\n        print("yes")\n'
        run_task(src)
        assert "yes" not in capsys.readouterr().out

    def test_else_taken(self, capsys):
        src = 'task default:\n    if false:\n        print("yes")\n    else:\n        print("no")\n'
        run_task(src)
        assert "no" in capsys.readouterr().out

    def test_elif_taken(self, capsys):
        src = (
            'let x = 5\n'
            'task default:\n'
            '    if x > 10:\n'
            '        print("big")\n'
            '    elif x > 3:\n'
            '        print("medium")\n'
            '    else:\n'
            '        print("small")\n'
        )
        run_task(src)
        assert "medium" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# For loop
# ---------------------------------------------------------------------------

class TestForLoop:
    def test_custom_each_over(self, capsys):
        src = (
            'job default =>\n'
            '    each x over [1, 2, 3] =>\n'
            '        print(x)\n'
        )
        run_task(src)
        out = capsys.readouterr().out
        assert "1" in out
        assert "2" in out
        assert "3" in out

    def test_custom_stop_skip(self, capsys):
        src = (
            'job default =>\n'
            '    each x over [1, 2, 3] =>\n'
            '        when x == 2 =>\n'
            '            skip\n'
            '        when x == 3 =>\n'
            '            stop\n'
            '        print(x)\n'
        )
        run_task(src)
        out = capsys.readouterr().out
        assert "1" in out
        assert "2" not in out
        assert "3" not in out

    def test_for_over_list(self, capsys):
        src = (
            'task default:\n'
            '    for x in [1, 2, 3]:\n'
            '        print(x)\n'
        )
        run_task(src)
        out = capsys.readouterr().out
        assert "1" in out
        assert "2" in out
        assert "3" in out

    def test_for_break(self, capsys):
        src = (
            'task default:\n'
            '    for x in [1, 2, 3]:\n'
            '        if x == 2:\n'
            '            break\n'
            '        print(x)\n'
        )
        run_task(src)
        out = capsys.readouterr().out
        assert "1" in out
        assert "2" not in out

    def test_for_continue(self, capsys):
        src = (
            'task default:\n'
            '    for x in [1, 2, 3]:\n'
            '        if x == 2:\n'
            '            continue\n'
            '        print(x)\n'
        )
        run_task(src)
        out = capsys.readouterr().out
        assert "1" in out
        assert "2" not in out
        assert "3" in out


# ---------------------------------------------------------------------------
# While loop
# ---------------------------------------------------------------------------

class TestWhileLoop:
    def test_custom_loop(self, capsys):
        src = (
            'job default =>\n'
            '    bind n = 3\n'
            '    loop n > 0 =>\n'
            '        print(n)\n'
            '        bind n = n - 1\n'
        )
        run_task(src)
        out = capsys.readouterr().out
        assert "3" in out
        assert "2" in out
        assert "1" in out

    def test_while(self, capsys):
        src = (
            'task default:\n'
            '    let n = 3\n'
            '    while n > 0:\n'
            '        print(n)\n'
            '        let n = n - 1\n'
        )
        run_task(src)
        out = capsys.readouterr().out
        assert "3" in out
        assert "2" in out
        assert "1" in out


# ---------------------------------------------------------------------------
# Built-in functions
# ---------------------------------------------------------------------------

class TestBuiltins:
    def test_custom_exec_block(self, capsys):
        src = 'job default =>\n    exec =>\n        echo hello\n'
        run_task(src)
        _ = capsys.readouterr()

    def test_len_list(self, capsys):
        src = 'task default:\n    print(len([1, 2, 3]))\n'
        run_task(src)
        assert "3" in capsys.readouterr().out

    def test_len_string(self, capsys):
        src = 'task default:\n    print(len("hello"))\n'
        run_task(src)
        assert "5" in capsys.readouterr().out

    def test_str_int(self, capsys):
        src = 'task default:\n    print(str(42))\n'
        run_task(src)
        assert "42" in capsys.readouterr().out

    def test_int_str(self, capsys):
        src = 'task default:\n    print(int("42"))\n'
        run_task(src)
        assert "42" in capsys.readouterr().out

    def test_float_str(self, capsys):
        src = 'task default:\n    print(float("3.25"))\n'
        run_task(src)
        assert "3.25" in capsys.readouterr().out

    def test_platform(self, capsys):
        src = 'task default:\n    let p = platform()\n    print(p)\n'
        run_task(src)
        out = capsys.readouterr().out
        assert out.strip() in ("windows", "linux")

    def test_exists_true(self, capsys, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello")
        path = f.as_posix()
        src = f'task default:\n    print(exists("{path}"))\n'
        run_task(src)
        assert "true" in capsys.readouterr().out

    def test_exists_false(self, capsys):
        src = 'task default:\n    print(exists("/nonexistent/path/xyz"))\n'
        run_task(src)
        assert "false" in capsys.readouterr().out

    def test_env_default(self, capsys):
        src = 'task default:\n    print(env("NONEXISTENT_VAR_XYZ", "fallback"))\n'
        run_task(src)
        assert "fallback" in capsys.readouterr().out

    def test_log_prints(self, capsys):
        src = 'task default:\n    log("test message")\n'
        run_task(src)
        out = capsys.readouterr().out
        assert "test message" in out

    def test_run_returns_output(self, capsys):
        if os.name == 'nt':
            cmd = 'echo hello'
        else:
            cmd = 'echo hello'
        src = f'task default:\n    let r = run("{cmd}")\n    print(r)\n'
        run_task(src)
        assert "hello" in capsys.readouterr().out

    def test_read_write_file(self, capsys, tmp_path):
        f = tmp_path / "test.txt"
        path = f.as_posix()
        src = (
            f'task default:\n'
            f'    write_file("{path}", "content123")\n'
            f'    let c = read_file("{path}")\n'
            f'    print(c)\n'
        )
        run_task(src)
        assert "content123" in capsys.readouterr().out

    def test_fail_exits(self):
        src = 'task default:\n    fail("oh no")\n'
        with pytest.raises(SystemExit):
            run_task(src)


# ---------------------------------------------------------------------------
# Task inspection
# ---------------------------------------------------------------------------

class TestInspection:
    def test_list_tasks(self):
        src = 'task a:\n    print("a")\ntask b:\n    print("b")\n'
        interp = make_interp(src)
        tasks = interp.list_tasks()
        assert "a" in tasks
        assert "b" in tasks

    def test_task_graph(self):
        src = (
            'task a:\n    print("a")\n'
            'task b needs a:\n    print("b")\n'
        )
        interp = make_interp(src)
        graph = interp.task_graph()
        assert graph["a"] == []
        assert graph["b"] == ["a"]
