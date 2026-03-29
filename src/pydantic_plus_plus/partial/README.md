# Partial Models

`partial` creates a `PartialBaseModel`, a variant of the given Pydantic `BaseModel` where every field is `Optional` with a default of `None`. This is the type-safe way to represent partial updates (PATCH payloads, upsert data, sparse sync records) without manually duplicating each model with every field made optional.

## Usage

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

## Selective Partials

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

## Recursive Partials

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

## Applying Partials

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

## What Partials Preserve

- **Field metadata** — descriptions, constraints (`min_length`, `ge`, etc.), and aliases are carried over. Constraints are enforced when a non-`None` value is provided.
- **Serialization** — custom type serializers defined via `Annotated` (e.g., UUID-to-string) work as expected.
- **JSON Schema** — `model_json_schema()` produces a valid schema with all properties defaulting to `null`.
- **Validation** — `model_validate()`, `model_validate_json()`, and `model_dump_json()` all work.

## What Partials Don't Inherit

Partial models are standalone classes that subclass `PartialBaseModel`, not the original model. This means:

- `@field_validator` and `@model_validator` decorators on the original are **not** inherited. This is intentional — validators that enforce required-field invariants would reject the partial data.
- `isinstance(patch, User)` is `False`. Use `isinstance(patch, PartialBaseModel)` instead.

## Alternative Syntax

You can also use the class method:

```python
PartialUser = PartialBaseModel.from_model(User)
```

Both syntaxes return the same cached class.

## Caching

Partial classes are cached. Calling `partial()` with the same arguments returns the same class:

```python
partial(User) is partial(User)                          # True
partial(User, recursive=False) is partial(User)         # False
partial(User, "name") is partial(User, "name")          # True
partial(User, "name", "email") is partial(User, "email", "name")  # True (order independent)
partial(User, "name") is partial(User, "email")         # False
```
