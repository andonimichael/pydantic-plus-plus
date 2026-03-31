from __future__ import annotations

import datetime
import types
import uuid
from decimal import Decimal
from enum import Enum
from random import Random
from typing import Any, Literal, TypeVar, Union, get_args, get_origin

from pydantic import BaseModel
from pydantic.fields import FieldInfo

from pydantic_plus_plus.reflection import has_default_value, is_base_model_type, is_optional, get_default_value
from pydantic_plus_plus.dummy._constraints import (
    generate_constrained_decimal,
    generate_constrained_float,
    generate_constrained_int,
    generate_constrained_string,
    resolve_collection_length,
)
from pydantic_plus_plus.dummy.errors import UnsupportedTypeError

T = TypeVar("T", bound=BaseModel)

_MAX_RECURSION_DEPTH = 10


class DummyGenerator:
    def __init__(
        self,
        random: Random,
        set_nones: bool | set[str],
        set_defaults: bool | set[str],
        depth: int = 0,
        ancestors: frozenset[type] = frozenset(),
    ) -> None:
        self._random = random
        self._set_nones = set_nones
        self._set_defaults = set_defaults
        self._depth = depth
        self._ancestors = ancestors

    def generate(self, model: type[T]) -> T:
        field_values: dict[str, Any] = {}
        for field_name, field_info in model.model_fields.items():
            field_values[field_name] = self._generate_field_value(field_name, field_info)
        return model.model_validate(field_values)

    def _generate_field_value(self, field_name: str, field_info: FieldInfo) -> Any:
        if self._should_use_none(field_name, field_info):
            return None

        if self._should_use_default(field_name, field_info):
            return get_default_value(field_info)

        annotation = field_info.annotation
        metadata = list(field_info.metadata) if field_info.metadata else []
        return self._generate_for_type(annotation, metadata)

    def _generate_for_type(self, annotation: Any, metadata: list[Any]) -> Any:
        if annotation is None or annotation is type(None):
            return None

        origin = get_origin(annotation)
        args = get_args(annotation)

        if origin is Union or isinstance(annotation, types.UnionType):
            return self._generate_union(args, metadata)

        if origin is Literal:
            return self._random.choice(args)

        if origin is not None:
            return self._generate_generic_type(origin, args, metadata)

        if isinstance(annotation, type):
            return self._generate_concrete_type(annotation, metadata)

        raise UnsupportedTypeError(f"Cannot generate value for type: {annotation}")

    def _generate_union(self, args: tuple[Any, ...], metadata: list[Any]) -> Any:
        non_none_args = [arg for arg in args if arg is not type(None)]
        if not non_none_args:
            return None

        self._random.shuffle(non_none_args)
        for candidate in non_none_args:
            try:
                return self._generate_for_type(candidate, metadata)
            except UnsupportedTypeError:
                continue

        if type(None) in args:
            return None
        raise UnsupportedTypeError(f"Cannot generate value for any member of Union{list(args)}")

    def _generate_concrete_type(self, annotation: type[Any], metadata: list[Any]) -> Any:
        if issubclass(annotation, Enum):
            members = list(annotation)
            return self._random.choice(members)
        if issubclass(annotation, bool):
            return self._random.choice([True, False])
        if issubclass(annotation, int):
            return generate_constrained_int(self._random, metadata)
        if issubclass(annotation, float):
            return generate_constrained_float(self._random, metadata)
        if issubclass(annotation, str):
            return generate_constrained_string(self._random, metadata)
        if issubclass(annotation, bytes):
            length = self._random.randint(4, 16)
            return self._random.randbytes(length)
        if issubclass(annotation, Decimal):
            return generate_constrained_decimal(self._random, metadata)
        if issubclass(annotation, uuid.UUID):
            return uuid.UUID(int=self._random.getrandbits(128))
        if issubclass(annotation, datetime.datetime):
            return self._generate_datetime()
        if issubclass(annotation, datetime.date):
            return self._generate_date()
        if issubclass(annotation, datetime.time):
            return self._generate_time()
        if issubclass(annotation, BaseModel):
            return self._generate_nested_model(annotation)

        raise UnsupportedTypeError(f"Cannot generate value for type: {annotation.__name__}")

    def _generate_generic_type(self, origin: type[Any], args: tuple[Any, ...], metadata: list[Any]) -> Any:
        if origin is list:
            return self._generate_list(args, metadata)
        if origin is dict:
            return self._generate_dict(args, metadata)
        if origin is set:
            return self._generate_set(args, metadata)
        if origin is frozenset:
            return frozenset(self._generate_set(args, metadata))
        if origin is tuple:
            return self._generate_tuple(args, metadata)

        raise UnsupportedTypeError(f"Cannot generate value for generic type: {origin.__name__}")

    def _should_use_none(self, field_name: str, field_info: FieldInfo) -> bool:
        if isinstance(self._set_nones, bool):
            return self._set_nones and is_optional(field_info.annotation)
        return field_name in self._set_nones

    def _should_use_default(self, field_name: str, field_info: FieldInfo) -> bool:
        if isinstance(self._set_defaults, bool):
            return self._set_defaults and has_default_value(field_info)
        return field_name in self._set_defaults

    def _at_generation_boundary(self, model_type: type[Any]) -> bool:
        return model_type in self._ancestors or self._depth >= _MAX_RECURSION_DEPTH

    def _generate_list(self, args: tuple[Any, ...], metadata: list[Any]) -> list[Any]:
        if not args:
            return []

        element_type = args[0]
        if is_base_model_type(element_type) and self._at_generation_boundary(element_type):
            return []

        length = resolve_collection_length(self._random, metadata)
        return [self._generate_for_type(element_type, []) for _ in range(length)]

    def _generate_dict(self, args: tuple[Any, ...], metadata: list[Any]) -> dict[Any, Any]:
        if len(args) < 2:
            return {}

        key_type, value_type = args[0], args[1]
        if is_base_model_type(value_type) and self._at_generation_boundary(value_type):
            return {}

        length = resolve_collection_length(self._random, metadata)
        return {self._generate_for_type(key_type, []): self._generate_for_type(value_type, []) for _ in range(length)}

    def _generate_set(self, args: tuple[Any, ...], metadata: list[Any]) -> set[Any]:
        if not args:
            return set()

        element_type = args[0]
        if is_base_model_type(element_type) and self._at_generation_boundary(element_type):
            return set()

        length = resolve_collection_length(self._random, metadata)
        return {self._generate_for_type(element_type, []) for _ in range(length)}

    def _generate_tuple(self, args: tuple[Any, ...], metadata: list[Any]) -> tuple[Any, ...]:
        if not args:
            return ()

        if len(args) == 2 and args[1] is Ellipsis:
            length = resolve_collection_length(self._random, metadata)
            return tuple(self._generate_for_type(args[0], []) for _ in range(length))

        return tuple(self._generate_for_type(arg, []) for arg in args)

    def _generate_nested_model(self, model: type[T]) -> T:
        if model in self._ancestors:
            raise UnsupportedTypeError(f"Cannot generate {model.__name__}: circular reference detected")

        if self._depth >= _MAX_RECURSION_DEPTH:
            raise UnsupportedTypeError(f"Cannot generate {model.__name__}: maximum recursion depth exceeded")

        nested = DummyGenerator(
            random=self._random,
            set_defaults=self._set_defaults if isinstance(self._set_defaults, bool) else False,
            set_nones=self._set_nones if isinstance(self._set_nones, bool) else False,
            depth=self._depth + 1,
            ancestors=self._ancestors | {model},
        )
        return nested.generate(model)

    def _generate_date(self) -> datetime.date:
        year = self._random.randint(2000, 2030)
        month = self._random.randint(1, 12)
        day = self._random.randint(1, 28)
        return datetime.date(year, month, day)

    def _generate_time(self) -> datetime.time:
        hour = self._random.randint(0, 23)
        minute = self._random.randint(0, 59)
        second = self._random.randint(0, 59)
        return datetime.time(hour, minute, second)

    def _generate_datetime(self) -> datetime.datetime:
        date = self._generate_date()
        time = self._generate_time()
        return datetime.datetime.combine(date, time)
