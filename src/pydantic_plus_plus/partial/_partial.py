from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any, Union, get_args

from pydantic import BaseModel, ConfigDict, create_model

from pydantic_plus_plus.reflection import (
    is_base_model_type,
    is_dict_type,
    make_optional,
    make_optional_field_info,
    is_list_type,
    is_union_type,
)
from pydantic_plus_plus.partial._field_selection import FieldSelection

if TYPE_CHECKING:
    from pydantic_plus_plus.partial.api import PartialBaseModel


class PartialModelConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    model: type[BaseModel]
    recursive: bool = True
    field_specs: frozenset[str] = frozenset()


_partial_model_cache: dict[PartialModelConfig, type] = {}


def create_partial(
    model: type[BaseModel],
    *,
    recursive: bool = True,
    field_selection: FieldSelection | None = None,
    _cache: dict[type, type] | None = None,
) -> type[PartialBaseModel[Any]]:
    config = PartialModelConfig(
        model=model,
        recursive=recursive if field_selection is None else True,
        field_specs=field_selection.original_specs if field_selection else frozenset(),
    )

    if config in _partial_model_cache:
        return _partial_model_cache[config]  # type: ignore[return-value]

    if _cache is None:
        _cache = {}

    if model in _cache:
        return _cache[model]  # type: ignore[return-value]
    else:
        _cache[model] = model  # circular reference guard

    field_definitions: dict[str, Any] = {}
    for field_name, field_info in model.model_fields.items():
        annotation = field_info.annotation

        if field_selection is None:
            new_annotation = _resolve_partial_annotation(annotation, recursive=recursive, _cache=_cache)
            new_annotation = make_optional(new_annotation)
            new_field_info = make_optional_field_info(field_info)
            field_definitions[field_name] = (new_annotation, new_field_info)
        else:
            nested = field_selection.nested_selection_for(field_name)
            should_be_optional = field_selection.should_make_optional(field_name)
            if nested is not None:
                new_annotation = _resolve_selective_annotation(annotation, nested, _cache=_cache)
                if should_be_optional:
                    new_annotation = make_optional(new_annotation)
                    new_field_info = make_optional_field_info(field_info)
                else:
                    new_field_info = copy.copy(field_info)
            else:
                if should_be_optional:
                    new_annotation = make_optional(annotation)
                    new_field_info = make_optional_field_info(field_info)
                else:
                    new_annotation = field_info.annotation
                    new_field_info = copy.copy(field_info)

            field_definitions[field_name] = (new_annotation, new_field_info)

    partial_cls = create_model(
        f"Partial{model.__name__}",
        __base__=_get_partial_base_class(),
        **field_definitions,
    )
    partial_cls._original_model = model  # type: ignore[attr-defined]

    _cache[model] = partial_cls
    _partial_model_cache[config] = partial_cls
    return partial_cls  # type: ignore[return-value]


def _resolve_partial_annotation(
    annotation: Any,
    *,
    recursive: bool,
    _cache: dict[type, type],
) -> Any:
    if not recursive:
        return annotation

    if is_base_model_type(annotation):
        return create_partial(annotation, recursive=True, _cache=_cache)

    args = get_args(annotation)

    # ``list[Model]`` → ``list[PartialModel]``
    if is_list_type(annotation) and args:
        inner = args[0]
        if isinstance(inner, type) and issubclass(inner, BaseModel):
            p = create_partial(inner, recursive=True, _cache=_cache)
            return list[p]  # type: ignore[valid-type]
        return annotation

    # ``dict[K, Model]`` → ``dict[K, PartialModel]``
    if is_dict_type(annotation) and len(args) == 2:
        key_type, val_type = args
        if isinstance(val_type, type) and issubclass(val_type, BaseModel):
            p = create_partial(val_type, recursive=True, _cache=_cache)
            return dict[key_type, p]  # type: ignore[valid-type]
        return annotation

    # ``Union[Model, Model2]`` / ``Union[PartialModel, PartialModel2]``
    if is_union_type(annotation, unwrap=False):
        new_args = []
        for arg in args:
            if isinstance(arg, type) and issubclass(arg, BaseModel):
                p = create_partial(arg, recursive=True, _cache=_cache)
                new_args.append(p)
            else:
                new_args.append(arg)
        return Union[tuple(new_args)]

    return annotation


def _resolve_selective_annotation(
    annotation: Any,
    nested_selection: FieldSelection,
    *,
    _cache: dict[type, type],
) -> Any:
    if is_base_model_type(annotation):
        if nested_selection.is_wildcard_only:
            return create_partial(annotation, recursive=True, _cache=_cache)
        else:
            return create_partial(annotation, field_selection=nested_selection, _cache=_cache)

    args = get_args(annotation)

    if is_union_type(annotation, unwrap=False):
        new_args = []
        for arg in args:
            if isinstance(arg, type) and issubclass(arg, BaseModel):
                ann = _resolve_selective_annotation(arg, nested_selection, _cache=_cache)
                new_args.append(ann)
            else:
                new_args.append(arg)
        return Union[tuple(new_args)]

    return annotation


def _get_partial_base_class() -> type[BaseModel]:
    from pydantic_plus_plus.partial.api import PartialBaseModel

    return PartialBaseModel
