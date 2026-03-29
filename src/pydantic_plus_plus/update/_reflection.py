from __future__ import annotations

from typing import Any, Union, get_args, get_origin

from pydantic import BaseModel


def unwrap_optional(annotation: Any) -> Any:
    origin = get_origin(annotation)
    if origin is Union:
        args = get_args(annotation)
        non_none = [arg for arg in args if arg is not type(None)]
        if len(non_none) == 1:
            return non_none[0]
    return annotation


def is_sequence_type(annotation: Any) -> bool:
    unwrapped = unwrap_optional(annotation)
    origin = get_origin(unwrapped)
    return origin in (list, set, frozenset)


def is_dict_type(annotation: Any) -> bool:
    unwrapped = unwrap_optional(annotation)
    origin = get_origin(unwrapped)
    return origin is dict


def is_base_model_type(annotation: Any) -> bool:
    unwrapped = unwrap_optional(annotation)
    return isinstance(unwrapped, type) and issubclass(unwrapped, BaseModel)


def get_field_annotation(model_type: type[BaseModel], field_name: str) -> Any:
    field_info = model_type.model_fields.get(field_name)
    if field_info is None:
        return None
    return field_info.annotation
