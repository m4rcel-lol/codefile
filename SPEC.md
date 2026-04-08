# Codefile Language Specification

**Version**: 2.1.0  
**File Extension**: `.codefile`

---

## 1. Overview

Codefile is a custom task programming language with first-class dependency execution, control flow, expressions, and optional shell integration.

### Design Principles

- Language-defined execution model
- Custom-first syntax and keywords
- Tasks/jobs as first-class declarations
- Predictable dependency DAG execution
- Shell integration is optional, not the language core

---

## 2. Canonical Keywords

```text
job requires bind when elsewhen otherwise each over loop stop skip give use exec
true false and or not
```

### Compatibility Aliases (Migration)

The parser accepts legacy aliases for migration:

```text
task->job, needs->requires, let->bind, if->when, elif->elsewhen, else->otherwise,
for->each, in->over, while->loop, import->use, return->give,
break->stop, continue->skip, shell->exec
```

Both `=>` (canonical) and `:` (compatibility) are accepted as block introducers.

---

## 3. Core Syntax

### 3.1 Variable binding

```codefile
bind x = 42
bind msg = "hello"
bind x = x + 1
```

### 3.2 Job declaration

```codefile
job build requires clean, test =>
    log("building")
```

### 3.3 Conditionals

```codefile
when x > 10 =>
    print("big")
elsewhen x > 5 =>
    print("medium")
otherwise =>
    print("small")
```

### 3.4 Loops

```codefile
each item over [1, 2, 3] =>
    print(item)

loop n > 0 =>
    bind n = n - 1
```

### 3.5 Loop control

```codefile
stop
skip
give 42
```

### 3.6 Imports/modules

```codefile
use "tasks/deploy.codefile"
```

### 3.7 Shell integration

```codefile
$ echo "inline"

exec =>
    echo "line1"
    echo "line2"
```

---

## 4. Data Types

- `int`
- `float`
- `string`
- `bool`
- `list`

Strings support interpolation with `${name}` and `${expression}`.

---

## 5. Expressions and operators

- Arithmetic: `+ - * /`
- Comparison: `== != < > <= >=`
- Logical: `and or not`
- Parentheses and precedence supported
- Function calls: `name(arg1, arg2)`

---

## 6. Execution Semantics

1. Source is tokenized and parsed to AST.
2. Imports are resolved.
3. Top-level bindings are evaluated.
4. Requested job dependency graph is topologically resolved.
5. Jobs execute in dependency order.
6. Runtime errors include file/line/column.

---

## 7. Built-ins

- `print`, `log`, `run`
- `env`, `exists`, `fail`
- `read_file`, `write_file`
- `platform`, `len`, `str`, `int`, `float`

---

## 8. Error Model

- `LexError`
- `ParseError`
- `RuntimeError`

All runtime/user-facing errors should report location and message.

---

## 9. Platform Support

- Linux and Windows
- `platform()` returns `"linux"` or `"windows"`

---

## 10. Migration Guidance

- New programs should use canonical custom syntax.
- Existing programs may keep legacy syntax under compatibility aliases.
- Tooling/tests/examples should prioritize canonical syntax.
