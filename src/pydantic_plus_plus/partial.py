from __future__ import annotations

from typing import Any, ClassVar, Generic, Optional, TypeVar, Union, cast, get_args, get_origin

from pydantic import BaseModel, create_model

T = TypeVar("T", bound=BaseModel)

_partial_model_cache: dict[tuple[type, bool], type] = {}


class PartialBaseModel(BaseModel, Generic[T]):
    """Base class for partial Pydantic BaseModels.

    All model fields become ``Optional[T]`` with a default of ``None``.

    Provides :meth:`apply` for deep-merging a partial into an existing
    model instance, and :meth:`from_model` for creating partial classes::

        PartialUser = PartialBaseModel.from_model(User)
        PartialUser = partial(User)  # equivalent
    """

    _original_model: ClassVar[type[BaseModel]]

    @classmethod
    def from_model(cls, model: type[T], *, recursive: bool = True) -> type[PartialBaseModel[T]]:
        """Create a standalone partial class from *model*."""
        return _create_partial(model, recursive=recursive)

    def apply(self, instance: T) -> T:
        """Deep-merge this partial's set fields into *instance* and return a
        new Pydantic model.

        Only fields that were explicitly provided when constructing the partial
        are merged. Nested models (and collections of models) are merged
        recursively so that untouched nested fields are preserved.
        """
        original_model = self.__class__._original_model
        base_data = instance.model_dump()
        update_data = self.model_dump(exclude_unset=True)
        merged = _deep_merge(base_data, update_data)
        return cast(T, original_model.model_validate(merged))


def partial(model: type[T], *, recursive: bool = True) -> type[PartialBaseModel[T]]:
    """Create a standalone partial class from a Pydantic model.

    All fields become ``Optional[T]`` with a default of ``None``::

        PartialUser = partial(User)
    """
    return _create_partial(model, recursive=recursive)


def _deep_merge(base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge *update* into *base*, returning a new dict."""
    merged = dict(base)
    for key, value in update.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _is_optional(annotation: Any) -> bool:
    origin = get_origin(annotation)
    if origin is Union:
        return type(None) in get_args(annotation)
    return annotation is type(None)


def _make_optional(annotation: Any) -> Any:
    if _is_optional(annotation):
        return annotation
    return Optional[annotation]


def _resolve_partial_annotation(
    annotation: Any,
    *,
    recursive: bool,
    _cache: dict[type, type],
) -> Any:
    if not recursive:
        return annotation

    # Direct BaseModel subclass field.
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return _create_partial(annotation, recursive=True, _cache=_cache)

    origin = get_origin(annotation)
    args = get_args(annotation)

    # ``list[Model]`` → ``list[PartialModel]``
    if origin is list and args:
        inner = args[0]
        if isinstance(inner, type) and issubclass(inner, BaseModel):
            p = _create_partial(inner, recursive=True, _cache=_cache)
            return list[p]  # type: ignore[valid-type]
        return annotation

    # ``dict[K, Model]`` → ``dict[K, PartialModel]``
    if origin is dict and len(args) == 2:
        key_type, val_type = args
        if isinstance(val_type, type) and issubclass(val_type, BaseModel):
            p = _create_partial(val_type, recursive=True, _cache=_cache)
            return dict[key_type, p]  # type: ignore[valid-type]
        return annotation

    # ``Optional[Model]`` / ``Union[Model, None]``
    if origin is Union:
        new_args = []
        for arg in args:
            if isinstance(arg, type) and issubclass(arg, BaseModel):
                new_args.append(_create_partial(arg, recursive=True, _cache=_cache))
            else:
                new_args.append(arg)
        return Union[tuple(new_args)]

    return annotation


def _create_partial(
    model: type[BaseModel],
    *,
    recursive: bool = True,
    _cache: dict[type, type] | None = None,
) -> type[PartialBaseModel[Any]]:
    cache_key = (model, recursive)
    if cache_key in _partial_model_cache:
        return _partial_model_cache[cache_key]  # type: ignore[return-value]

    if _cache is None:
        _cache = {}
    if model in _cache:
        return _cache[model]  # type: ignore[return-value]

    _cache[model] = model  # circular reference guard

    field_definitions: dict[str, Any] = {}
    for field_name, field_info in model.model_fields.items():
        annotation = field_info.annotation
        annotation = _resolve_partial_annotation(annotation, recursive=recursive, _cache=_cache)
        optional_annotation = _make_optional(annotation)

        new_field_info = field_info._copy()
        new_field_info.default = None
        new_field_info.default_factory = None
        field_definitions[field_name] = (optional_annotation, new_field_info)

    partial_cls = create_model(
        f"Partial{model.__name__}",
        __base__=PartialBaseModel,
        **field_definitions,
    )
    partial_cls._original_model = model  # type: ignore[attr-defined]

    _cache[model] = partial_cls
    _partial_model_cache[cache_key] = partial_cls
    return partial_cls  # type: ignore[return-value]
