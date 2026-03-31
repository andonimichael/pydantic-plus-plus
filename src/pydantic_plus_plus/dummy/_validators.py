from __future__ import annotations


from pydantic import BaseModel

from pydantic_plus_plus.reflection import has_default_value, is_optional
from pydantic_plus_plus.dummy.errors import InvalidFieldError


def validate_optional_fields(model: type[BaseModel], field_names: set[str]) -> None:
    for field_name in field_names:
        if field_name not in model.model_fields:
            raise InvalidFieldError(f"Field '{field_name}' does not exist on {model.__name__}")

        field_info = model.model_fields[field_name]
        if not is_optional(field_info.annotation):
            raise InvalidFieldError(f"Field '{field_name}' on {model.__name__} is not Optional")


def validate_defaultable_fields(model: type[BaseModel], field_names: set[str]) -> None:
    for field_name in field_names:
        if field_name not in model.model_fields:
            raise InvalidFieldError(f"Field '{field_name}' does not exist on {model.__name__}")

        field_info = model.model_fields[field_name]
        if not has_default_value(field_info):
            raise InvalidFieldError(f"Field '{field_name}' on {model.__name__} has no default value")
