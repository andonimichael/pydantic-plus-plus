from __future__ import annotations


from pydantic import BaseModel

from pydantic_plus_plus.reflection import get_field_annotation, is_dict_type, is_collection_type
from pydantic_plus_plus.update.errors import FieldNotFoundError, InvalidOperationError


def validate_field_exists(model: BaseModel, field: str) -> None:
    model_type = type(model)
    if field not in model_type.model_fields:
        raise FieldNotFoundError(f"'{field}' is not a field on {model_type.__name__}")


def validate_sequence_field(model: BaseModel, field: str) -> None:
    validate_field_exists(model, field)
    model_type = type(model)
    annotation = get_field_annotation(model_type, field)
    if not is_collection_type(annotation):
        raise InvalidOperationError(f"'{field}' is not a sequence type on {model_type.__name__}")


def validate_dict_field(model: BaseModel, field: str) -> None:
    validate_field_exists(model, field)
    model_type = type(model)
    annotation = get_field_annotation(model_type, field)
    if not is_dict_type(annotation):
        raise InvalidOperationError(f"'{field}' is not a dict type on {model_type.__name__}")


def validate_removable_field(model: BaseModel, field: str) -> None:
    validate_field_exists(model, field)
    model_type = type(model)
    annotation = get_field_annotation(model_type, field)
    if not is_collection_type(annotation) and not is_dict_type(annotation):
        raise InvalidOperationError(f"'{field}' is not a sequence or dict type on {model_type.__name__}")
