# AGENTIC CODING GUIDE

For coding agents working on Pydantic++, follow the below instructions.

## Project Overview

Pydantic++ (or pydantic-plus-plus) is a suite of utilities built ontop of
Pydantic v2. They are meant to add to the base library and extend its
functionality, not to replace it.

If you need to, read the @README.md for an overview of the project, the set of
utilities, and how to use them.

## Coding Standards

### General

- **Full variable names** — `result` not `res` or `r`.
- **Upper camel case for abbreviations** — `HttpRestClient` not
  `HTTPSRESTClient`.
- **Self-documenting code** — Code should be self-documenting. Names should
  explain intent. You should be extremely judicious with code comments. They
  should add clarity and explain reasoning where it is not self-evident in the
  code itself.
- **No comment clutter** — Remove all section comments or comments that
  re-iterate what the code is doing. Keep the code clean of comment clutter.
- **DRY / SOLID** — Extract shared logic, but don't over-abstract. Three
  similar lines > premature abstraction. And maintain object oriented best
  practices. Keep your classes SOLID. Prefer immutability over state. And
  prefer smaller readable helper methods of giant monoliths.
- **No over-engineering** — Only build what's needed now. Don't over-engineer
  for a hypothetical future.
- **Design for Extensibility** — Think about the coupling of your code and
  design for future extensibility and maintainability.
- **Testing is a First Class Citizen** - Think about tests as a necessary part
  of every change. Test driven development is the best, but even if testing
  comes after implementation, it should be a first class part of every plan,
  commit, and review.
- **Think deeply about your public API** - We are a public library. Think
  deeply about the interface we expose and guarantee for all library users.
  Any non-public module should be prefixed with an underscore. Even in our
  non-public modules you should think about what is "package private" and what
  is truly private to just that module (again, prefixed with an underscore).

### Python

- Use `uv` for all package and build management.
- Use `mypy` for type checking. We run mypy in strict mode with
  `disallow_untyped_defs = true`.
- Use `ruff` for linting (120 line length)
- Use `pytest` for testing.
- Run `pre-commit` locally over your files before considering a task complete.
  Pre-commit calls ruff with `--fix`, so it may make changes to your files.
- We support Python 3.10. Make sure your code is compatible.

## Project Structure

```
src/pydantic_plus_plus/
  __init__.py       # Public exports: PartialBaseModel, partial, dummy, errors
  partial/
    __init__.py     # Re-exports from api.py
    api.py          # Public API: PartialBaseModel, partial()
  dummy/
    __init__.py     # Re-exports from api.py and errors.py
    api.py          # Public API: dummy()
  mypy/
    plugin.py       # Mypy plugin for type-safe partial() calls
tests/
examples/
pyproject.toml
```

## Setup

```bash
uv sync --group dev
```

## Testing

- Tests live in `tests/`, mirroring the source structure.
- Use `uv run pytest` to run the full suite.
- Mypy plugin tests use YAML format via `pytest-mypy-plugins`.
- Partial model tests should call `_clear_cache()` in fixtures to reset the
  model cache between tests.

## Mypy Plugin

The mypy plugin (`src/pydantic_plus_plus/mypy/plugin.py`) provides type safety
for `partial()` and `PartialBaseModel.from_model()`. Changes to the public API
or partial model construction almost always require corresponding plugin
updates. Run the mypy plugin tests after any change:

```bash
uv run pytest tests/mypy/
```
