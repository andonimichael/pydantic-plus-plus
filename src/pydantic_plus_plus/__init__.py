"""Pydantic utilities that improve on the core library."""

from pydantic_plus_plus.dummy import InvalidFieldError, UnsupportedTypeError, dummy
from pydantic_plus_plus.partial import PartialBaseModel, partial
from pydantic_plus_plus.registry import AmbiguousModelError, ModelNotFoundError, ModelRegistry

__all__ = [
    "AmbiguousModelError",
    "InvalidFieldError",
    "ModelNotFoundError",
    "ModelRegistry",
    "PartialBaseModel",
    "UnsupportedTypeError",
    "dummy",
    "partial",
]
