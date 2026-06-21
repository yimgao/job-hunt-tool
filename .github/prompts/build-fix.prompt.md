---
agent: agent
description: Systematically diagnose and fix build errors, type errors, or failing CI
---

# Build Error Resolution

Work through the error systematically. Fix root causes — do not suppress warnings or skip checks.

## Process

### 1. Capture the full error
Paste or describe the complete error output. Include:
- Error message and stack trace
- File and line number if shown
- Build tool and command that failed

### 2. Categorize the error

| Category | Signals |
|----------|---------|
| **Import/module** | `ModuleNotFoundError`, `ImportError` |
| **Syntax** | `SyntaxError`, `IndentationError` |
| **Type** | `TypeError`, Mypy/Pyright type errors |
| **Dependency** | `version conflict`, `missing package` |
| **Environment** | `command not found`, `ENOENT`, missing env var |
| **Test failure** | `AssertionError`, `FAILED` |
| **Lint** | ruff, black, isort failures |

### 3. Fix strategy

- **Import errors** — verify the export exists; check for circular dependencies; check `PYTHONPATH` and package installation
- **Type errors** — fix the type annotation; do not cast to `Any` unless truly unavoidable
- **Dependency errors** — update lockfile (`uv lock`), reconcile version conflicts
- **Test failures** — fix the implementation if behavior is wrong; fix the test only if the test itself is incorrect
- **Lint errors** — run `ruff check --fix .` and `ruff format .`

### 4. Verify the fix
After applying a fix, run the test/command again. Confirm the specific error is resolved and no new errors were introduced.

### 5. Check for related issues
A single root cause often produces multiple error messages. After fixing, scan for similar patterns elsewhere in the codebase.

## Rules
- Never suppress errors with `# type: ignore` without a comment explaining why
- Never delete lock files without understanding why they are conflicting
- Fix the root cause, not the symptom
