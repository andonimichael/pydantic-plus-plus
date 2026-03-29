# Pydantic++

[![CI](https://github.com/andonimichael/pydantic-plus-plus/actions/workflows/ci.yml/badge.svg)](https://github.com/andonimichael/pydantic-plus-plus/actions/workflows/ci.yml)
[![Release](https://github.com/andonimichael/pydantic-plus-plus/actions/workflows/release.yml/badge.svg)](https://github.com/andonimichael/pydantic-plus-plus/actions/workflows/release.yml)
[![PyPI version](https://img.shields.io/pypi/v/pydantic-plus-plus)](https://pypi.org/project/pydantic-plus-plus/)

Pydantic++ is a suite of utilities to improve upon the core [Pydantic](https://github.com/pydantic/pydantic) library. We stand on the shoulders of giants here. Huge kudos to the Pydantic team for all their hard work building an amazing product.

## Utilities

- [Partial Models](#partial-models) — type-safe "partial" Pydantic models where some or all fields are optional
- [Model Updater](#model-updates) — type-safe builder for updating model instances
- [Dummy Models](#dummy-models) — generate fake model instances with random data for testing
- [Model Registry](#model-registry) — discover all BaseModel subclasses in a module tree

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

### Selective Partials

Pass field names to `partial()` to make only those fields optional. Non-selected fields keep their original behavior:

```python
class User(BaseModel):
    name: str
    age: int
    email: str = "user@example.com"
    address: Address

PartialUser = partial(User, "name", "email")

patch = PartialUser(age=30, address=some_address)
patch.name   # None — selected, defaults to None
patch.age    # 30 — not selected, still required
patch.email  # None — selected, defaults to None (original default replaced)
```

Use dot-notation to target nested fields. The parent field stays required, but the nested model becomes a partial with only the specified fields optional:

```python
PartialUser = partial(User, "address.city")

patch = PartialUser(
    name="Alice",
    age=30,
    address={"street": "123 1st Ave", "state": "NY", "zip_code": "10001"},
)
patch.address.city    # None — selected, optional
patch.address.street  # "123 1st Ave" — not selected, still required
```

Use `"*"` as a wildcard to make all fields of a nested model optional:

```python
PartialUser = partial(User, "address.*")

patch = PartialUser(name="Alice", age=30, address={})
patch.address.city    # None
patch.address.street  # None
```

These options can be freely combined.

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

patch = PartialUser(address={"city": "New York City"})
```

Disable this with `recursive=False` to require complete nested models when provided:

```python
PartialUser = partial(User, recursive=False)

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

`.apply()` returns a new instance of the original model type. The original is never mutated. The field selection controls which fields are optional in the constructor — `.apply()` merges all explicitly-set fields regardless of the selection.

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

Partial classes are cached. Calling `partial()` with the same arguments returns the same class:

```python
partial(User) is partial(User)                          # True
partial(User, recursive=False) is partial(User)         # False
partial(User, "name") is partial(User, "name")          # True
partial(User, "name", "email") is partial(User, "email", "name")  # True (order independent)
partial(User, "name") is partial(User, "email")         # False
```

## Dummy Models

`dummy` generates an instance of any Pydantic `BaseModel` populated with random data. This is useful for testing — round-trip serialization, factory fixtures, property-based tests — anywhere you need a valid model instance without hand-writing every field.

### Usage

```python
from pydantic import BaseModel
from pydantic_plus_plus import dummy

class User(BaseModel):
    name: str
    age: int

user = dummy(User)
user.name   # "kR4tBx2m"
user.age    # 37
```

### Seed for Reproducibility

Pass a `seed` for deterministic output — same seed, same instance every time:

```python
first = dummy(User, seed=42)
second = dummy(User, seed=42)
assert first.model_dump() == second.model_dump()  # always True
```

### Constraint Awareness

Generated values respect field constraints. A field with `ge=0, le=100` will produce a value in that range; a string with `min_length=3` will never be shorter:

```python
class Config(BaseModel):
    name: str = Field(min_length=3, max_length=10)
    value: int = Field(ge=0, le=100)

config = dummy(Config, seed=1)
len(config.name)  # between 3 and 10
config.value      # between 0 and 100
```

Collection constraints (`min_length`, `max_length` on `list`, `set`, `dict`, `tuple`) are also respected.

### Nested Models

Nested `BaseModel` fields are recursively populated:

```python
class Address(BaseModel):
    street: str
    city: str

class User(BaseModel):
    name: str
    address: Address

user = dummy(User, seed=1)
user.address.street  # "xN7kLm2p"
user.address.city    # "Bq4RtYwS"
```

Self-referential models and circular references are handled automatically — collections return empty and optional fields return `None` at the recursion boundary.

### Using Defaults

By default, `dummy` generates fresh values for every field, ignoring defaults. Use `set_defaults` to keep defaults instead:

```python
class User(BaseModel):
    name: str
    role: str = "viewer"
    tags: list[str] = Field(default_factory=list)

user = dummy(User, set_defaults=True)
user.role  # "viewer"
user.tags  # []
```

Pass a set of field names to apply this selectively:

```python
user = dummy(User, set_defaults={"role"})
user.role  # "viewer" — uses default
user.tags  # ["kR4tBx2m", "Qp3nYwLs"] — generated
```

### Setting None

By default, `Optional` fields receive generated values. Use `set_nones` to set them to `None` instead:

```python
class Profile(BaseModel):
    name: str
    bio: Optional[str] = None
    avatar: Optional[str] = None

profile = dummy(Profile, set_nones=True)
profile.name    # "xN7kLm2p" — required, still generated
profile.bio     # None
profile.avatar  # None
```

Pass a set of field names to apply this selectively:

```python
profile = dummy(Profile, set_nones={"bio"})
profile.bio     # None
profile.avatar  # "Bq4RtYwS" — generated
```

When both `set_nones` and `set_defaults` target the same field, `set_nones` takes precedence.

### Supported Types

`dummy` handles the full range of common Pydantic field types:

| Type | Generation |
|---|---|
| `str` | Random alphanumeric string (respects `min_length`, `max_length`) |
| `int`, `float`, `Decimal` | Random number (respects `ge`, `gt`, `le`, `lt`, `multiple_of`) |
| `bool` | Random `True` or `False` |
| `bytes` | Random bytes |
| `datetime`, `date`, `time` | Random value in a reasonable range |
| `UUID` | Random UUID |
| `Enum` | Random member |
| `Literal["a", "b"]` | Random choice from the literal values |
| `list[T]`, `set[T]`, `frozenset[T]` | 1–3 generated elements (respects `min_length`, `max_length`) |
| `dict[K, V]` | 1–3 generated entries (respects `min_length`, `max_length`) |
| `tuple[T, U, V]` | Each position generated |
| `tuple[T, ...]` | 1–3 generated elements (respects `min_length`, `max_length`) |
| `Optional[T]` | Generated `T` value (non-`None` by default) |
| `Union[A, B]` | Random choice of member, then generated |
| `BaseModel` | Recursive generation |

## Model Registry

`ModelRegistry` scans one or more Python modules (and all submodules) and collects every `BaseModel` subclass it finds. This is useful when you have a base class — say `BasePrompt`, `AgentConfig`, or `BaseEvent` — and you need to discover all concrete implementations at runtime for dispatching, serialization, CLI tooling, or documentation generation.

### Usage

```python
from pydantic import BaseModel
from pydantic_plus_plus import ModelRegistry

class BasePrompt(BaseModel):
    text: str

class SystemPrompt(BasePrompt):
    system_instruction: str

class UserPrompt(BasePrompt):
    user_name: str
```

```python
# Scan a module for all BaseModel subclasses
registry = ModelRegistry("myapp.models")

# Scan for a specific base type
registry = ModelRegistry("myapp.prompts", base=BasePrompt)

# Scan multiple modules
registry = ModelRegistry("myapp.models", "myapp.schemas")

# Pass an already-imported module object
import myapp.models
registry = ModelRegistry(myapp.models)
```

### Lookup

Retrieve model classes by short name or fully-qualified name:

```python
registry["SystemPrompt"]
# <class 'myapp.prompts.SystemPrompt'>

registry["myapp.prompts.SystemPrompt"]
# <class 'myapp.prompts.SystemPrompt'>

registry.get("SystemPrompt")
# <class 'myapp.prompts.SystemPrompt'>

registry.get("Nonexistent")
# None
```

If two models in different modules share the same class name, lookup by short name raises `AmbiguousModelError`. Use the fully-qualified name to disambiguate:

```python
registry["SharedName"]
# AmbiguousModelError: 'SharedName' matches multiple models: ...

registry["myapp.v1.models.SharedName"]
# <class 'myapp.v1.models.SharedName'>
```

### Collection Interface

`ModelRegistry` supports `len`, `in`, and iteration:

```python
len(registry)              # 2
"SystemPrompt" in registry # True
SystemPrompt in registry   # True (by class)

for model in registry:
    print(model.__name__)
```

### Filtering

Use `.filter()` to create a new registry with a subset of models. The predicate receives each model class:

```python
system_only = registry.filter(lambda module: "System" in m.__name__)
```

### Options

| Parameter | Type | Default | Description |
|---|---|---|---|
| `*modules` | `str \| ModuleType` | *(required)* | Root modules to scan (recursively) |
| `base` | `type[T]` | `BaseModel` | Only collect subclasses of this type |
| `include_base` | `bool` | `False` | Whether to include `base` itself in results |
| `include_abstract` | `bool` | `False` | Whether to include abstract classes (`inspect.isabstract`) |

### Immutability

The registry is immutable. The scan runs once at construction time, and the resulting set of models never changes. `.filter()` returns a new `ModelRegistry` instance rather than modifying the original.

## Model Updater

`update` provides a type-safe, immutable builder for updating Pydantic model instances. Pydantic's built-in `model_copy(update={"field": value})` takes a `dict[str, Any]` — you lose all type safety, typos are invisible, and nested updates are painful. `update` fixes all of this.

### Usage

```python
from pydantic import BaseModel
from pydantic_plus_plus import update

class User(BaseModel):
    name: str
    age: int
    email: str

user = User(name="Ali", age=30, email="alice@example.com")
updated = update(user).set(name="Alison", age=31).apply()
```

The `update()` function returns a `ModelUpdater[User]`. Every method returns a **new** updater — the original is never mutated. Call `.apply()` at the end to produce a new model instance.

### Nested Models

For `BaseModel` fields, `.set()` accepts dicts that are deep-merged with the current value — only the keys you provide are overwritten:

```python
class Address(BaseModel):
    street: str
    city: str
    state: str

class User(BaseModel):
    name: str
    address: Address

user = User(name="Alice", address=Address(street="123 1st Ave", city="New York", state="NY"))
updated = update(user).set(address={"city": "New York City"}).apply()

updated.address.city    # "New York City" — updated
updated.address.street  # "123 1st Ave" — preserved
```

You can also pass a nested `ModelUpdater` for fully typed nested updates:

```python
updated = (
    update(user)
    .set(address=update(user.address).set(city="New York City"))
    .apply()
)
```

### Collection Operations

`ModelUpdater` provides dedicated methods for working with `list`, `set`, `frozenset`, and `dict` fields:

```python
class User(BaseModel):
    tags: list[str]
    scores: set[int]
    metadata: dict[str, str]

user = User(tags=["a"], scores={1}, metadata={"role": "viewer"})

updated = (
    update(user)
    .append(tags="b")                       # tags: ["a", "b"]
    .extend(scores=[2, 3])                  # scores: {1, 2, 3}
    .set_item(metadata={"tier": "premium"}) # metadata: {"role": "viewer", "tier": "premium"}
    .remove(tags="a")                       # tags: ["b"]
    .remove(metadata="role")                # metadata: {"tier": "premium"}
    .apply()
)
```

| Method | Works on | Accepts |
|---|---|---|
| `.append()` | `list`, `set`, `frozenset` | Single element |
| `.extend()` | `list`, `set`, `frozenset` | Multiple elements |
| `.remove()` | `list`, `set`, `frozenset`, `dict` | Element (sequences) or key (dicts) |
| `.set_item()` | `dict` | A `dict` to merge into the field |

### Dot-Path Escape Hatch

For deeply nested updates where you don't need static type checking, use `.set_path()`:

```python
updated = update(user).set_path("address.geo.lat", 40.7).apply()
```

No validation happens at call time — Pydantic validates the final structure at `.apply()` time.

### Immutability

Every method returns a new `ModelUpdater`. You can safely fork chains:

```python
base = update(user)
with_name = base.set(name="Bob")
with_age = base.set(age=31)

# base, with_name, and with_age are independent
```

`.apply()` always returns a new model instance — the original is never mutated.

### Operation Ordering

Operations replay in the order they were added. This means you can overwrite a field and then modify it:

```python
updated = update(user).set(tags=[]).append(tags="fresh").apply()
# tags: ["fresh"]
```

### Strict Mode

By default, removing a non-existent element or dict key is a silent no-op. Pass `raise_on_missing=True` to raise instead:

```python
update(user, raise_on_missing=True).remove(tags="nonexistent").apply()
# raises FieldNotFoundError
```

### Subclass Preservation

`.apply()` preserves the exact type of the input model, including subclasses:

```python
class AdminUser(User):
    role: str

admin = AdminUser(name="Alice", age=30, role="admin")
updated = update(admin).set(name="Bob").apply()
isinstance(updated, AdminUser)  # True
```

## Mypy Plugin

Pydantic++ ships a mypy plugin that gives partial models and model updates full type safety. Without it, mypy sees `partial(User)` as returning a generic type and can't validate field access or constructor arguments. Similarly, `ModelUpdater` methods like `.set()` and `.append()` would accept any keyword argument without type checking.

With the plugin enabled:

- Partial models get field-level type checking, constructor validation, and IDE autocompletion.
- `ModelUpdater` methods get typed keyword arguments — mypy validates field names, value types, and restricts operations to applicable fields (e.g., `.append()` only accepts sequence fields).

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

This is a well known limitation of `pydantic-partial`, which their README calls out as "a massive amount of work while being kind of a bad hack." Pydantic++ ships a mypy plugin that synthesizes full `TypeInfo` objects, giving users field-level type checking, constructor validation, and IDE autocompletion with zero `# type: ignore` comments.

#### `.apply()` deep merge

pydantic-partial creates partial models but has no built-in way to merge a partial back into an existing instance. Pydantic++ provides `.apply()` which recursively merges only explicitly-set fields, preserving untouched nested data.

## License

MIT
