# Codefile Language Specification

**Version**: 1.0.0  
**File Extension**: `.codefile`

---

## 1. Overview

Codefile is a task-oriented scripting language inspired by the philosophy of `Makefile` but designed as a proper, modern, first-class programming language. It combines the dependency-graph model of Make with real control flow, variables, and shell integration.

### Design Philosophy

- Tasks are **first-class citizens**, not special targets
- Dependencies form a **DAG** (Directed Acyclic Graph), automatically resolved
- Real **control flow**: conditions, loops, functions
- **Shell integration** is first-class, not an afterthought
- **Human-readable** syntax with minimal ceremony
- **Indentation-based blocks** (like Python) — no braces needed, reducing visual noise

### Why Indentation-Based?

Codefile uses indentation (4 spaces or 1 tab per level) rather than braces `{}` because:
1. Task bodies are visually obvious at a glance — the same reason Python adopted indentation
2. Build scripts are typically short-to-medium length, not the kind of dense code where brace matching is needed
3. Consistency with shell script culture (indentation already used conventionally)
4. Eliminates "brace wars" and formatting debates

---

## 2. File Extension

All Codefile programs must use the `.codefile` extension.

---

## 3. Comments

```codefile
# Single-line comment

### 
This is a multi-line
block comment
###
```

---

## 4. Keywords and Reserved Words

```
task    needs   let     if      elif    else    for     while
in      do      break   continue return  true    false   and
or      not     import
```

---

## 5. Data Types

| Type     | Literal Examples                    |
|----------|-------------------------------------|
| `string` | `"hello"`, `"world"`, `"foo ${x}"` |
| `int`    | `42`, `0`, `-7`                     |
| `bool`   | `true`, `false`                     |
| `list`   | `["a", "b", 1, true]`              |

### String Interpolation

Strings support `${}` interpolation:

```codefile
let name = "World"
print("Hello, ${name}!")
```

---

## 6. Variables

Variables are declared with `let`:

```codefile
let x = 42
let msg = "hello"
let items = ["a", "b", "c"]
let flag = true
```

Variable reassignment uses the same syntax:

```codefile
let x = x + 1
```

---

## 7. Operators

### Arithmetic
`+`, `-`, `*`, `/`

### Comparison
`==`, `!=`, `<`, `>`, `<=`, `>=`

### Logical
`and`, `or`, `not`

### String Concatenation
`+` concatenates strings

---

## 8. Task Definition

```ebnf
task_def ::= "task" identifier ["needs" identifier ("," identifier)*] ":"
             INDENT statement+ DEDENT
```

Example:

```codefile
task clean:
    $ rm -rf dist
    log("Cleaned")

task compile needs clean:
    $ gcc main.c -o dist/app

task test needs compile:
    $ ./dist/app --test
```

The `default` task is executed when no task name is given to `codefile run`.

---

## 9. Task Dependencies

```codefile
task deploy needs build, test:
    $ scp dist/app user@server:/app
```

Dependencies are resolved topologically. Circular dependencies are detected and reported as errors.

---

## 10. Shell Command Execution

### Inline (single line)

```codefile
$ echo "hello"
$ rm -rf dist
```

### Block (multi-line)

```codefile
shell:
    echo "line 1"
    echo "line 2"
    ls -la
```

### Capturing Output

```codefile
let output = run("git log --oneline -1")
print(output)
```

Shell commands inherit the current environment plus any `let` variables exported to the environment.

---

## 11. Conditionals

```ebnf
if_stmt ::= "if" expr ":"
            INDENT statement+ DEDENT
            ["elif" expr ":" INDENT statement+ DEDENT]*
            ["else" ":" INDENT statement+ DEDENT]
```

Example:

```codefile
if x > 10:
    print("big")
elif x == 10:
    print("ten")
else:
    print("small")
```

---

## 12. Loops

### For Loop

```codefile
for item in items:
    print(item)

for i in [1, 2, 3]:
    print(i)
```

### While Loop

```codefile
while x > 0:
    let x = x - 1
    print(x)
```

`break` and `continue` are supported inside loops.

---

## 13. Built-in Functions

| Function                    | Description                                      |
|-----------------------------|--------------------------------------------------|
| `print(value)`              | Print to stdout                                  |
| `log(message)`              | Print with `[HH:MM:SS]` timestamp prefix        |
| `run(command)`              | Execute shell command, return stdout as string   |
| `env(name)`                 | Get environment variable value (string or `""`) |
| `env(name, default)`        | Get env var with fallback default                |
| `exists(path)`              | Return `true` if file/directory exists           |
| `fail(message)`             | Abort with error message and non-zero exit code  |
| `read_file(path)`           | Return file contents as string                   |
| `write_file(path, content)` | Write string content to file                     |
| `platform()`                | Return `"windows"` or `"linux"`                  |
| `len(value)`                | Return length of string or list                  |
| `str(value)`                | Convert value to string                          |
| `int(value)`                | Convert value to integer                         |

---

## 14. Import / Include

```codefile
import "other.codefile"
import "tasks/deploy.codefile"
```

Imports are processed before task execution. All tasks and variables from the imported file become available. Circular imports are detected and reported.

---

## 15. Error Handling

Runtime errors produce a clear message including file name, line number, and column:

```
Error [hello.codefile:5:3]: Undefined variable 'nme'
```

### Error Types

- `LexError` — invalid token
- `ParseError` — syntax error
- `RuntimeError` — execution error (undefined var, type mismatch, etc.)
- `TaskError` — task dependency or execution failure

---

## 16. Full EBNF Grammar

```ebnf
program     ::= statement*

statement   ::= task_def
              | var_decl
              | if_stmt
              | for_stmt
              | while_stmt
              | shell_cmd
              | shell_block
              | expr_stmt
              | import_stmt
              | break_stmt
              | continue_stmt
              | return_stmt

task_def    ::= "task" IDENT ["needs" IDENT ("," IDENT)*] ":" block

var_decl    ::= "let" IDENT "=" expr NEWLINE

if_stmt     ::= "if" expr ":" block
                ("elif" expr ":" block)*
                ["else" ":" block]

for_stmt    ::= "for" IDENT "in" expr ":" block

while_stmt  ::= "while" expr ":" block

shell_cmd   ::= "$" rest_of_line NEWLINE

shell_block ::= "shell" ":" INDENT raw_line+ DEDENT

expr_stmt   ::= expr NEWLINE

import_stmt ::= "import" STRING NEWLINE

break_stmt  ::= "break" NEWLINE

continue_stmt ::= "continue" NEWLINE

return_stmt ::= "return" [expr] NEWLINE

block       ::= NEWLINE INDENT statement+ DEDENT

expr        ::= or_expr

or_expr     ::= and_expr ("or" and_expr)*

and_expr    ::= not_expr ("and" not_expr)*

not_expr    ::= "not" not_expr | compare_expr

compare_expr ::= add_expr (("==" | "!=" | "<" | ">" | "<=" | ">=") add_expr)*

add_expr    ::= mul_expr (("+" | "-") mul_expr)*

mul_expr    ::= unary_expr (("*" | "/") unary_expr)*

unary_expr  ::= "-" unary_expr | primary

primary     ::= INT | STRING | BOOL | IDENT | list_lit | func_call | "(" expr ")"

list_lit    ::= "[" [expr ("," expr)*] "]"

func_call   ::= IDENT "(" [expr ("," expr)*] ")"
```

---

## 17. Execution Model

1. The source file is lexed into tokens
2. Tokens are parsed into an AST
3. Imports are resolved (depth-first, with cycle detection)
4. The interpreter walks the AST:
   - Top-level `let` statements are evaluated first
   - The requested task is resolved with its full dependency chain (topological sort)
   - Tasks are executed in dependency order
5. Shell commands run via `subprocess.run` with `shell=True`
   - On Linux: `/bin/sh` (or `$SHELL`)
   - On Windows: `cmd.exe`

---

## 18. Platform Support

Codefile supports **Windows** and **Linux** only.

Use the `platform()` built-in to write platform-conditional logic:

```codefile
task clean:
    if platform() == "windows":
        $ del /Q /S dist
    else:
        $ rm -rf dist
```
