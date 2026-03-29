# Mypy Plugin

Pydantic++ ships a mypy plugin that gives partial models and model updates full type safety. Without it, mypy sees `partial(User)` as returning a generic type and can't validate field access or constructor arguments. Similarly, `ModelUpdater` methods like `.set()` and `.append()` would accept any keyword argument without type checking.

With the plugin enabled:

- Partial models get field-level type checking, constructor validation, and IDE autocompletion.
- `ModelUpdater` methods get typed keyword arguments — mypy validates field names, value types, and restricts operations to applicable fields (e.g., `.append()` only accepts sequence fields).

## Setup

Add the plugin to your mypy configuration:

```toml
# pyproject.toml
[tool.mypy]
plugins = ["pydantic.mypy", "pydantic_plus_plus.mypy"]
```

The plugin works alongside the standard Pydantic mypy plugin. Order does not matter.

## What the Plugin Enables

Without the plugin:

```python
PartialUser = partial(User)

def update(p: PartialUser) -> None:  # mypy error: not valid as a type
    p.model_dump()                   # mypy error: has no attribute "model_dump"
```

With the plugin, both lines type-check cleanly — no `# type: ignore` needed.
