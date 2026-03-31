from __future__ import annotations

from collections import defaultdict
from types import ModuleType
from typing import Callable, Generic, Iterator, TypeVar, Union, overload

from pydantic import BaseModel

from pydantic_plus_plus.registry._scanner import scan_modules
from pydantic_plus_plus.registry.errors import AmbiguousModelError, ModelNotFoundError

T = TypeVar("T", bound=BaseModel)


class ModelRegistry(Generic[T]):
    """An immutable registry of Pydantic ``BaseModel`` subclasses discovered by scanning Python modules.

    Recursively imports the given modules and collects every class that is a
    subclass of *base*.  The registry is built once at construction time and
    provides O(1) lookup by class name or fully-qualified name.

    Parameters
    ----------
    *modules:
        One or more importable module paths (``"myapp.models"``) or already-imported
        module objects.  Each module — and all of its submodules — is scanned.
    base:
        Only collect subclasses of this type.  Defaults to ``BaseModel``.
    include_base:
        When ``True``, include *base* itself in the results.  Defaults to ``False``.
    include_abstract:
        When ``True``, include classes with unimplemented abstract methods
        (``inspect.isabstract``).  Defaults to ``False``.
    """

    @overload
    def __init__(
        self,
        *modules: Union[str, ModuleType],
        include_base: bool = ...,
        include_abstract: bool = ...,
    ) -> None: ...

    @overload
    def __init__(
        self,
        *modules: Union[str, ModuleType],
        base: type[T],
        include_base: bool = ...,
        include_abstract: bool = ...,
    ) -> None: ...

    def __init__(
        self,
        *modules: Union[str, ModuleType],
        base: type[T] = BaseModel,  # type: ignore[assignment]
        include_base: bool = False,
        include_abstract: bool = False,
        _models: frozenset[type[T]] | None = None,
    ) -> None:
        self._modules = modules
        self._base = base
        if _models is not None:
            self._models = _models
        else:
            self._models = scan_modules(modules, base, include_base=include_base, include_abstract=include_abstract)
        self._short_name_index: dict[str, list[type[T]]] = defaultdict(list)
        self._qualified_name_index: dict[str, type[T]] = {}
        self._build_indexes()

    def _build_indexes(self) -> None:
        for model in self._models:
            short_name = model.__name__
            qualified_name = f"{model.__module__}.{model.__qualname__}"
            self._short_name_index[short_name].append(model)
            self._qualified_name_index[qualified_name] = model

    @property
    def models(self) -> frozenset[type[T]]:
        """All discovered model classes."""
        return self._models

    @property
    def base(self) -> type[T]:
        """The base type used to filter discovered classes."""
        return self._base

    @property
    def modules(self) -> tuple[Union[str, ModuleType], ...]:
        """The root modules that were scanned."""
        return self._modules

    def __getitem__(self, name: str) -> type[T]:
        """Look up a model by short class name or fully-qualified name.

        Raises
        ------
        ModelNotFoundError
            If no model matches *name*.
        AmbiguousModelError
            If *name* is a short name that matches multiple models.  Use the
            fully-qualified name (``"myapp.models.MyModel"``) to disambiguate.
        """
        if name in self._qualified_name_index:
            return self._qualified_name_index[name]

        candidates = self._short_name_index.get(name)
        if candidates is None:
            raise ModelNotFoundError(name)

        if len(candidates) > 1:
            qualified_names = [f"{cls.__module__}.{cls.__qualname__}" for cls in candidates]
            raise AmbiguousModelError(f"'{name}' matches multiple models: {', '.join(sorted(qualified_names))}")
        return candidates[0]

    def get(self, name: str) -> type[T] | None:
        """Look up a model by name, returning ``None`` if not found."""
        try:
            return self[name]
        except ModelNotFoundError:
            return None

    def __len__(self) -> int:
        return len(self._models)

    def __iter__(self) -> Iterator[type[T]]:
        return iter(self._models)

    def __contains__(self, item: object) -> bool:
        if isinstance(item, str):
            if item in self._qualified_name_index:
                return True
            candidates = self._short_name_index.get(item)
            if candidates is None:
                return False
            if len(candidates) > 1:
                qualified_names = [f"{cls.__module__}.{cls.__qualname__}" for cls in candidates]
                raise AmbiguousModelError(f"'{item}' matches multiple models: {', '.join(sorted(qualified_names))}")
            return True
        if isinstance(item, type):
            return item in self._models
        return False

    def filter(self, predicate: Callable[[type[T]], bool]) -> ModelRegistry[T]:
        """Return a new registry containing only models that satisfy *predicate*."""
        filtered = frozenset(model for model in self._models if predicate(model))
        return ModelRegistry(base=self._base, _models=filtered)  # type: ignore[call-overload, no-any-return]
