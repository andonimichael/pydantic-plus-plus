# Dummy Models

`dummy` generates an instance of any Pydantic `BaseModel` populated with random data. This is useful for testing — round-trip serialization, factory fixtures, property-based tests — anywhere you need a valid model instance without hand-writing every field.

## Usage

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

## Seed for Reproducibility

Pass a `seed` for deterministic output — same seed, same instance every time:

```python
first = dummy(User, seed=42)
second = dummy(User, seed=42)
assert first.model_dump() == second.model_dump()  # always True
```

## Constraint Awareness

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

## Nested Models

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

## Using Defaults

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

## Setting None

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

## Supported Types

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
