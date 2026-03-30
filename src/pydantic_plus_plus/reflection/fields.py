from __future__ import annotations

import copy
from typing import Any, Callable, cast

from pydantic import BaseModel
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined


def get_field_annotation(model_type: type[BaseModel], field_name: str) -> Any:
    field_info = model_type.model_fields.get(field_name)
    if field_info is None:
        raise KeyError(f"Field '{field_name}' not found on model '{model_type.__name__}'")
    return field_info.annotation


def has_default_value(field_info: FieldInfo) -> bool:
    return field_info.default is not PydanticUndefined or field_info.default_factory is not None


def get_default_value(field_info: FieldInfo) -> Any:
    if field_info.default_factory is not None:
        factory = cast(Callable[[], Any], field_info.default_factory)
        return factory()
    else:
        return field_info.default


def make_optional_field_info(field_info: FieldInfo) -> FieldInfo:
    new_field_info = copy.copy(field_info)
    new_field_info.default = None
    new_field_info.default_factory = None
    return new_field_info
