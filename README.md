# Codefile

> A fully custom task programming language.

Codefile is a modern, human-readable programming language inspired by the philosophy of `Makefile` — but designed as a real, first-class language with its own surface syntax.

Every Codefile program lives in a `.codefile` file and is run with the `codefile` CLI.

---

## Language Identity (Custom-First)

Codefile is now custom-first. Primary syntax is:

- `job` (task definition)
- `requires` (dependency declaration)
- `bind` (variable declaration/reassignment)
- `when` / `elsewhen` / `otherwise` (conditionals)
- `each ... over ...` (for-style loop)
- `loop ...` (while-style loop)
- `use` (import)
- `give` (return)
- `stop` / `skip` (loop control)
- `exec` (shell block)
- `=>` (block introducer)

Legacy syntax remains accepted in compatibility mode aliases:
`task/needs/let/if/elif/else/for/in/while/import/return/break/continue/shell` and `:`.

---

## Installation

### Prebuilt Installers (No Python Required)

Download release assets from GitHub Releases:

- `install-codefile.sh` (standalone Linux installer script)
- `codefile-*.rpm` (Fedora/RHEL)
- `codefile-*.pkg.tar.zst` (Arch Linux)
- `codefile-setup.exe` (Windows installer)

Install with:

```bash
# Linux standalone installer (uses local `./codefile` next to script if present, otherwise downloads release binary)
bash install-codefile.sh

# Fedora/RHEL
sudo dnf install ./codefile-*.rpm

# Arch Linux
sudo pacman -U ./codefile-*.pkg.tar.zst
```

Run `codefile-setup.exe` from the release assets on Windows, then verify:

```powershell
# Windows
codefile version
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

Create `hello.codefile`:

```codefile
bind name = "World"

job default requires greet =>
    log("Running default job")

job greet =>
    print("Hello, ${name}!")
    $ echo "Shell says hello too"
```

Run it:

```bash
codefile run -f hello.codefile
```

---

## Syntax Cheat-Sheet

### Variables

```codefile
bind name = "Alice"
bind count = 42
bind ratio = 1.5
bind debug = true
bind items = ["a", "b", "c"]
```

### Jobs and dependencies

```codefile
job hello =>
    print("Hello!")

job build requires clean, compile =>
    log("Build complete")
```

### Shell

```codefile
$ echo "hello"

exec =>
    mkdir -p dist
    gcc main.c -o dist/app

bind result = run("git log --oneline -1")
print(result)
```

### Conditionals

```codefile
when platform() == "windows" =>
    $ del /Q dist
elsewhen platform() == "linux" =>
    $ rm -rf dist
otherwise =>
    fail("Unsupported platform")
```

### Loops

```codefile
each item over ["a", "b", "c"] =>
    print(item)

bind n = 5
loop n > 0 =>
    print(n)
    bind n = n - 1
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
| `float(value)`            | Convert to float                         |

### Imports

```codefile
use "tasks/deploy.codefile"
```

---

## CLI Reference

```text
codefile run [task] [-f FILE]   Run a job (default job if omitted)
codefile list [-f FILE]         List all jobs
codefile check [-f FILE]        Validate without running
codefile graph [-f FILE]        Print ASCII dependency graph
codefile version                Print version
```

---

## Migration Policy

- **Primary style**: custom-first syntax shown above.
- **Compatibility mode**: legacy keyword aliases and `:` block marker are still parsed.
- **Recommendation**: use custom syntax for all new `.codefile` files.

---

## Examples

See [`examples/`](examples/).

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests in `tests/`
4. Run tests: `pytest tests/ -v`
5. Open a pull request

---

## License

MIT — see [LICENSE](LICENSE) for details.
