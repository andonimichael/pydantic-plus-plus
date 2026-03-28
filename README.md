# Pydantic++

Pydantic++ is a suite of utilities to improve upon the core [Pydantic](https://github.com/pydantic/pydantic) library. We stand on the shoulders of giants here. Huge kudos to the Pydantic team for all their hard work building an amazing product.

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

`partial` creates a `PartialBaseModel`, a variant of the given Pydantic `BaseModel` where every field is `Optional` with a default of `None`. This is the type-safe way to represent partial updates (PATCH payloads, upsert data, sparse sync records) without manually duplicating your model with every field made optional.

### Usage

```python
from pydantic import BaseModel
from pydantic_plus_plus import partial

class User(BaseModel):
    name: str
    age: int
    email: str

PartialUser = partial(User)
```

The resulting `PartialUser` class accepts any subset of fields:

```python
patch = PartialUser(name="Alice")
patch.name   # "Alice"
patch.age    # None
patch.email  # None
```

Use `model_dump(exclude_unset=True)` to get only the fields that were explicitly provided — the standard pattern for database partial updates:

```python
patch = PartialUser(name="Alice", age=31)
patch.model_dump(exclude_unset=True)
# {"name": "Alice", "age": 31}
```

### Recursive Partials

By default, nested `BaseModel` fields are also partialized. This means you can provide incomplete nested data:

```python
class Address(BaseModel):
    street: str
    city: str
    state: str
    zip_code: str

class User(BaseModel):
    name: str
    address: Address

PartialUser = partial(User)

# Only update the city — street, state, zip_code are not required
patch = PartialUser(address={"city": "New York City"})
```

Disable this with `recursive=False` to require complete nested models when provided:

```python
PartialUser = partial(User, recursive=False)

# This now requires all Address fields
patch = PartialUser(address=Address(
    street="123 1st Ave",
    city="New York",
    state="NY",
    zip_code="10001",
))
```

Recursive partialization handles `list[Model]`, `dict[str, Model]`, `Optional[Model]`, and self-referencing models.

### Applying Partials

Use `.apply()` to deep-merge a partial into an existing model instance. Only explicitly-set fields are merged; everything else is preserved:

```python
user = User(
    name="Alice",
    age=30,
    email="alice@example.com",
    address=Address(street="123 1st Ave", city="New York", state="NY", zip_code="10001"),
)

patch = PartialUser(age=31, address={"city": "New York City"})
updated = patch.apply(user)

updated.name             # "Alice" — preserved
updated.age              # 31 — updated
updated.address.street   # "123 1st Ave" — preserved
updated.address.city     # "New York City" — updated
```

`.apply()` returns a new instance of the original model type. The original is never mutated.

### What Partials Preserve

- **Field metadata** — descriptions, constraints (`min_length`, `ge`, etc.), and aliases are carried over. Constraints are enforced when a non-`None` value is provided.
- **Serialization** — custom type serializers defined via `Annotated` (e.g., UUID-to-string) work as expected.
- **JSON Schema** — `model_json_schema()` produces a valid schema with all properties defaulting to `null`.
- **Validation** — `model_validate()`, `model_validate_json()`, and `model_dump_json()` all work.

### What Partials Don't Inherit

Partial models are standalone classes that subclass `PartialBaseModel`, not the original model. This means:

- `@field_validator` and `@model_validator` decorators on the original are **not** inherited. This is intentional — validators that enforce required-field invariants would reject the partial data.
- `isinstance(patch, User)` is `False`. Use `isinstance(patch, PartialBaseModel)` instead.

### Alternative Syntax

You can also use the class method:

```python
PartialUser = PartialBaseModel.from_model(User)
```

Both syntaxes return the same cached class.

### Caching

Partial classes are cached by (model, recursive) pair. Calling `partial(User)` multiple times returns the same class:

```python
partial(User) is partial(User)           # True
partial(User, recursive=False) is partial(User, recursive=True)  # False
```

## Mypy Plugin

Pydantic++ ships a mypy plugin that gives partial models full type safety. Without it, mypy sees `partial(User)` as returning a generic type and can't validate field access or constructor arguments.

With the plugin enabled, mypy understands that `PartialUser` has `name: str | None`, `age: int | None`, etc., and will type-check constructor calls and attribute access accordingly.

### Setup

Add the plugin to your mypy configuration:

```toml
# pyproject.toml
[tool.mypy]
plugins = ["pydantic.mypy", "pydantic_plus_plus.mypy"]
```

The plugin works alongside the standard Pydantic mypy plugin. Order does not matter.

### What the Plugin Enables

Without the plugin:

```python
PartialUser = partial(User)

def update(p: PartialUser) -> None:  # mypy error: not valid as a type
    p.model_dump()                   # mypy error: has no attribute "model_dump"
```

With the plugin, both lines type-check cleanly — no `# type: ignore` needed.

## License

MIT
