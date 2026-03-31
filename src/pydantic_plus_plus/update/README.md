# Model Updater

`update` provides a type-safe, immutable builder for updating Pydantic model instances. Pydantic's built-in `model_copy(update={"field": value})` takes a `dict[str, Any]` — you lose all type safety, typos are invisible, and nested updates are painful. `update` fixes all of this.

## Usage

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

## Nested Models

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

## Collection Operations

`ModelUpdater` provides dedicated methods for working with `list`, `set`, `frozenset`, and `dict` fields:

```python
class User(BaseModel):
    tags: list[str]
    scores: set[int]
    metadata: dict[str, str]

user = User(tags=["a"], scores={1}, metadata={"role": "viewer"})

updated = (
    update(user)
    .append(tags="b")                          # tags: ["a", "b"]
    .extend(scores=[2, 3])                     # scores: {1, 2, 3}
    .merge_items(metadata={"tier": "premium"}) # metadata: {"role": "viewer", "tier": "premium"}
    .remove(tags="a")                          # tags: ["b"]
    .remove(metadata="role")                   # metadata: {"tier": "premium"}
    .apply()
)
```

| Method | Works on | Accepts |
|---|---|---|
| `.append()` | `list`, `set`, `frozenset` | Single element |
| `.extend()` | `list`, `set`, `frozenset` | Multiple elements |
| `.remove()` | `list`, `set`, `frozenset`, `dict` | Element (sequences) or key (dicts) |
| `.merge_items()` | `dict` | A `dict` to merge into the field |

## Dot-Path Escape Hatch

For deeply nested updates where you don't need static type checking, use `.set_path()`:

```python
updated = update(user).set_path("address.geo.lat", 40.7).apply()
```

No validation happens at call time — Pydantic validates the final structure at `.apply()` time.

## Immutability

Every method returns a new `ModelUpdater`. You can safely fork chains:

```python
base = update(user)
with_name = base.set(name="Bob")
with_age = base.set(age=31)

# base, with_name, and with_age are independent
```

`.apply()` always returns a new model instance — the original is never mutated.

## Operation Ordering

Operations replay in the order they were added. This means you can overwrite a field and then modify it:

```python
updated = update(user).set(tags=[]).append(tags="fresh").apply()
# tags: ["fresh"]
```

## Strict Mode

By default, removing a non-existent element or dict key is a silent no-op. Pass `raise_on_missing=True` to raise instead:

```python
update(user, raise_on_missing=True).remove(tags="nonexistent").apply()
# raises FieldNotFoundError
```

## Subclass Preservation

`.apply()` preserves the exact type of the input model, including subclasses:

```python
class AdminUser(User):
    role: str

admin = AdminUser(name="Alice", age=30, role="admin")
updated = update(admin).set(name="Bob").apply()
isinstance(updated, AdminUser)  # True
```
