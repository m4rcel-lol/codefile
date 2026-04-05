# Codefile

> A task-oriented scripting language for humans.

Codefile is a modern, human-readable programming language inspired by the philosophy of `Makefile` — but designed as a real, first-class language. Define **tasks**, declare **dependencies**, write **real logic**, and run **shell commands** — all in one clean, indented syntax.

Every Codefile program lives in a `.codefile` file and is run with the `codefile` CLI.

---

## Why Codefile?

| Feature              | Makefile | Bash | Python Script | **Codefile** |
|----------------------|----------|------|---------------|--------------|
| Task dependencies    | ✅       | ❌   | ❌            | ✅           |
| Real control flow    | ❌       | ✅   | ✅            | ✅           |
| Readable syntax      | ❌       | 🟡   | ✅            | ✅           |
| Shell integration    | ✅       | ✅   | 🟡            | ✅           |
| Cross-platform       | 🟡       | ❌   | ✅            | ✅           |
| No runtime required  | ✅       | ✅   | ❌            | ✅ (binary)  |
| Dependency graph CLI | ❌       | ❌   | ❌            | ✅           |

---

## Installation

### Linux (standalone binary)

```bash
chmod +x codefile
sudo mv codefile /usr/local/bin/
codefile version
```

### Linux (.deb package)

```bash
sudo dpkg -i codefile_1.0.0_amd64.deb
codefile version
```

### Windows

Unzip `codefile-windows.zip` and add the extracted folder to your `PATH`:

```powershell
.\codefile.exe version
```

### From Source (Python 3.10+)

```bash
git clone https://github.com/m4rcel-lol/codefile
cd codefile
pip install -r requirements.txt
python cli.py version
```

---

## Quick Start

Create a file called `hello.codefile`:

```codefile
# hello.codefile

let name = "World"

task default needs greet:
    log("Running default task")

task greet:
    print("Hello, ${name}!")
    $ echo "Shell says hello too"
```

Run it:

```bash
codefile run -f hello.codefile
```

Output:
```
Hello, World!
Shell says hello too
[12:34:56] Running default task
```

---

## Syntax Cheat-Sheet

### Variables

```codefile
let name = "Alice"
let count = 42
let debug = true
let items = ["a", "b", "c"]
```

### Tasks

```codefile
task hello:
    print("Hello!")

task build needs clean, compile:
    log("Build complete")
```

### Shell Commands

```codefile
# Inline
$ echo "hello"
$ rm -rf dist

# Block
shell:
    mkdir -p dist
    gcc main.c -o dist/app

# Capture output
let result = run("git log --oneline -1")
print(result)
```

### Conditionals

```codefile
if platform() == "windows":
    $ del /Q dist
elif platform() == "linux":
    $ rm -rf dist
else:
    fail("Unsupported platform")
```

### Loops

```codefile
for item in ["a", "b", "c"]:
    print(item)

let n = 5
while n > 0:
    print(n)
    let n = n - 1
```

### Built-in Functions

| Function                  | Description                              |
|---------------------------|------------------------------------------|
| `print(value)`            | Print to stdout                          |
| `log(msg)`                | Print with timestamp                     |
| `run(cmd)`                | Run shell command, return stdout         |
| `env(name[, default])`    | Get environment variable                 |
| `exists(path)`            | Check if file/directory exists           |
| `fail(msg)`               | Abort with error                         |
| `read_file(path)`         | Read file contents                       |
| `write_file(path, text)`  | Write file contents                      |
| `platform()`              | Returns `"windows"` or `"linux"`         |
| `len(value)`              | Length of string or list                 |
| `str(value)`              | Convert to string                        |
| `int(value)`              | Convert to integer                       |

### Comments

```codefile
# Single-line comment

###
This is a
multi-line block comment
###
```

### Imports

```codefile
import "tasks/deploy.codefile"
```

---

## CLI Reference

```
codefile run [task] [-f FILE]   Run a task (default task if omitted)
codefile list [-f FILE]         List all tasks
codefile check [-f FILE]        Validate without running
codefile graph [-f FILE]        Print ASCII dependency graph
codefile version                Print version
```

**Options:**

- `-f FILE` / `--file FILE` — path to `.codefile` (auto-detected if omitted)

**Examples:**

```bash
# Run default task in current directory
codefile run

# Run a specific task
codefile run build -f myproject.codefile

# List tasks
codefile list -f build.codefile

# Check syntax
codefile check -f myproject.codefile

# Print dependency graph
codefile graph -f build.codefile
```

---

## Platform Support

Codefile supports **Windows** and **Linux** only. Use `platform()` to write cross-platform tasks:

```codefile
task clean:
    if platform() == "windows":
        $ del /Q /S dist
    else:
        $ rm -rf dist
```

Shell commands use:
- **Linux**: `$SHELL` or `/bin/sh`
- **Windows**: `cmd.exe`

---

## Examples

See the [`examples/`](examples/) directory:

| File | Description |
|------|-------------|
| `hello.codefile` | Hello World |
| `build.codefile` | Build pipeline (compile → test → package → deploy) |
| `vars.codefile` | Variables, types, expressions |
| `loops.codefile` | For and while loops |
| `shell.codefile` | Shell command execution |
| `conditional.codefile` | Conditionals with env checks |
| `systemd-example.codefile` | Linux systemd service context |

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Make your changes with tests in `tests/`
4. Run tests: `pytest tests/ -v`
5. Open a pull request

Please follow the existing code style and add docstrings to all new modules and functions.

---

## License

MIT — see [LICENSE](LICENSE) for details.
