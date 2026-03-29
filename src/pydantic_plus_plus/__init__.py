"""Pydantic utilities that improve on the core library."""

from pydantic_plus_plus.dummy import InvalidFieldError, UnsupportedTypeError, dummy
from pydantic_plus_plus.partial import PartialBaseModel, partial

__all__ = ["InvalidFieldError", "PartialBaseModel", "UnsupportedTypeError", "dummy", "partial"]
