# Pydantic++

[![CI](https://github.com/andonimichael/pydantic-plus-plus/actions/workflows/ci.yml/badge.svg)](https://github.com/andonimichael/pydantic-plus-plus/actions/workflows/ci.yml)
[![Release](https://github.com/andonimichael/pydantic-plus-plus/actions/workflows/release.yml/badge.svg)](https://github.com/andonimichael/pydantic-plus-plus/actions/workflows/release.yml)
[![PyPI version](https://img.shields.io/pypi/v/pydantic-plus-plus)](https://pypi.org/project/pydantic-plus-plus/)

Pydantic++ is a suite of utilities to improve upon the core [Pydantic](https://github.com/pydantic/pydantic) library. We stand on the shoulders of giants here. Huge kudos to the Pydantic team for all their hard work building an amazing product.

## Utilities

- [Partial Models](src/pydantic_plus_plus/partial/README.md) — type-safe "partial" Pydantic models where some or all fields are optional
- [Model Updater](src/pydantic_plus_plus/update/README.md) — type-safe immutable builder for updating model instances
- [Model Registry](src/pydantic_plus_plus/registry/README.md) — discover all BaseModel subclasses in a module tree
- [Dummy Models](src/pydantic_plus_plus/dummy/README.md) — generate dummy model instances with random data for testing
- [Mypy Plugin](src/pydantic_plus_plus/mypy/README.md) — full `mypy` integration for partial models and model updates

## Installation

```bash
pip install pydantic-plus-plus
```

Requires Python 3.10+ and Pydantic 2.0+.

If you use [mypy](https://github.com/python/mypy) for type checking, please also add our plugin to your `mypy` configuration.

```toml
[tool.mypy]
plugins = ["pydantic.mypy", "pydantic_plus_plus.mypy"]
```

## Partial Models

`partial` creates a `PartialBaseModel`, a variant of the given Pydantic `BaseModel` where every field is `Optional` with a default of `None`. This is the type-safe way to represent partial updates (PATCH payloads, upsert data, sparse sync records) without manually duplicating each model with every field made optional.

## Model Updater

`update` provides a type-safe, immutable builder for updating Pydantic model instances. Pydantic's built-in `model_copy(update={"field": value})` takes a `dict[str, Any]` — you lose all type safety, typos are invisible, and nested updates are painful. `update` fixes all of this.

## Model Registry

`ModelRegistry` scans one or more Python modules (and all submodules) and collects every `BaseModel` subclass it finds. This is useful when you have a base class — say `BasePrompt`, `AgentConfig`, or `BaseEvent` — and you need to discover all concrete implementations at runtime for dispatching, serialization, CLI tooling, or documentation generation.

## Dummy Models

`dummy` generates an instance of any Pydantic `BaseModel` populated with random data. This is useful for testing — round-trip serialization, factory fixtures, property-based tests — anywhere you need a valid model instance without hand-writing every field.

## Mypy Plugin

Pydantic++ ships a mypy plugin that gives partial models and model updates full type safety. Without it, mypy sees `partial(User)` as returning a generic type and can't validate field access or constructor arguments. Similarly, `ModelUpdater` methods like `.set()` and `.append()` would accept any keyword argument without type checking.

With the plugin enabled:

- Partial models get field-level type checking, constructor validation, and IDE autocompletion.
- `ModelUpdater` methods get typed keyword arguments — mypy validates field names, value types, and restricts operations to applicable fields (e.g., `.append()` only accepts sequence fields).

## Comparable Packages

### Why Pydantic++ over pydantic-partial?

Pydantic++ offers a similar feature set, but takes a different philosophical approach than [pydantic-partial](https://github.com/team23/pydantic-partial) that is more aligned with SOLID Object Oriented design principles.

Here's how the two differ:

| | Pydantic++ | pydantic-partial |
|---|---|---|
| Partial models | All fields optional | All fields optional |
| Selective fields | Yes | Yes |
| Dot-notation nesting | Yes | Yes |
| Wildcard nesting | Yes | Yes |
| Field metadata preservation | Yes | Yes |
| Caching | Yes | Yes |
| Recursive by default | Yes | No (opt-in) |
| Mypy plugin | Yes | No |
| `.apply()` deep merge | Yes | No |
| Standalone partial classes | Yes — partials don't subclass the original | No — partials subclass the original |

#### Philosophical Differences

`pydantic-partial`'s partials subclass the original model, so `isinstance(patch, User)` is `True`. This violates the Liskov Substitution Principle — a partial `User` weakens the preconditions of the original (required fields become optional), meaning code that expects a complete `User` can silently receive one with `None` fields. In addition to breaking LSP, this also causes problems for type checkers because the subclass relationship tells type checkers the partial *is* a `User`.

Pydantic++ takes a different philosophical approach, where partials are standalone classes. This preserves LSP. Additionally, because `isinstance(patch, User)` is `False`, the type checker can enforce the boundary between partial and complete data. Users must go through `.apply()` to produce a real `User`, making the conversion explicit and safe.

#### Mypy plugin

This is a well known limitation of `pydantic-partial`. Pydantic++ ships a mypy plugin that synthesizes full `TypeInfo` objects, giving users field-level type checking and constructor validation with zero `# type: ignore` comments.

#### `.apply()` deep merge

pydantic-partial creates partial models but has no built-in way to merge a partial back into an existing instance. Pydantic++ provides `.apply()` which recursively merges only explicitly-set fields, preserving untouched nested data.

## License

MIT
