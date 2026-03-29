"""Pydantic utilities that improve on the core library."""

from pydantic_plus_plus.dummy import InvalidFieldError, UnsupportedTypeError, dummy
from pydantic_plus_plus.partial import PartialBaseModel, partial
from pydantic_plus_plus.registry import AmbiguousModelError, ModelNotFoundError, ModelRegistry
from pydantic_plus_plus.update import FieldNotFoundError, InvalidOperationError, ModelUpdater, update

__all__ = [
    "AmbiguousModelError",
    "FieldNotFoundError",
    "InvalidFieldError",
    "InvalidOperationError",
    "ModelNotFoundError",
    "ModelRegistry",
    "ModelUpdater",
    "PartialBaseModel",
    "UnsupportedTypeError",
    "dummy",
    "partial",
    "update",
]
