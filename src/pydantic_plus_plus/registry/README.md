# Model Registry

`ModelRegistry` scans one or more Python modules (and all submodules) and collects every `BaseModel` subclass it finds. This is useful when you have a base class — say `BasePrompt`, `AgentConfig`, or `BaseEvent` — and you need to discover all concrete implementations at runtime for dispatching, serialization, CLI tooling, or documentation generation.

## Usage

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

## Lookup

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

## Collection Interface

`ModelRegistry` supports `len`, `in`, and iteration:

```python
len(registry)              # 2
"SystemPrompt" in registry # True
SystemPrompt in registry   # True (by class)

for model in registry:
    print(model.__name__)
```

## Filtering

Use `.filter()` to create a new registry with a subset of models. The predicate receives each model class:

```python
system_only = registry.filter(lambda module: "System" in m.__name__)
```

## Options

| Parameter | Type | Default | Description |
|---|---|---|---|
| `*modules` | `str \| ModuleType` | *(required)* | Root modules to scan (recursively) |
| `base` | `type[T]` | `BaseModel` | Only collect subclasses of this type |
| `include_base` | `bool` | `False` | Whether to include `base` itself in results |
| `include_abstract` | `bool` | `False` | Whether to include abstract classes (`inspect.isabstract`) |

## Immutability

The registry is immutable. The scan runs once at construction time, and the resulting set of models never changes. `.filter()` returns a new `ModelRegistry` instance rather than modifying the original.
