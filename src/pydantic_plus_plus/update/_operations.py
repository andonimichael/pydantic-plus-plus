from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Sequence

from pydantic import BaseModel, ConfigDict

from pydantic_plus_plus.partial._merge import deep_merge
from pydantic_plus_plus.update._reflection import (
    get_field_annotation,
    is_base_model_type,
    unwrap_optional,
)
from pydantic_plus_plus.update.errors import FieldNotFoundError


class Operation(ABC, BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    @abstractmethod
    def apply(self, data: dict[str, Any], model_type: type[BaseModel], raise_on_missing: bool) -> None: ...


class SetOp(Operation):
    field: str
    value: Any

    def apply(self, data: dict[str, Any], model_type: type[BaseModel], raise_on_missing: bool) -> None:
        from pydantic_plus_plus.update.api import ModelUpdater

        annotation = get_field_annotation(model_type, self.field)
        value = self.value

        if isinstance(value, ModelUpdater):
            current_value = data.get(self.field)
            unwrapped = unwrap_optional(annotation)
            if isinstance(unwrapped, type) and issubclass(unwrapped, BaseModel) and isinstance(current_value, dict):
                current_instance = unwrapped.model_validate(current_value)
                resolved = value.apply_to(current_instance)
                data[self.field] = resolved.model_dump()
            else:
                data[self.field] = value
        elif isinstance(value, dict) and is_base_model_type(annotation):
            current_value = data.get(self.field)
            if isinstance(current_value, dict):
                data[self.field] = deep_merge(current_value, value)
            else:
                data[self.field] = value
        else:
            data[self.field] = value


class AppendOp(Operation):
    field: str
    item: Any

    def apply(self, data: dict[str, Any], model_type: type[BaseModel], raise_on_missing: bool) -> None:
        current = data.get(self.field)
        as_list = _to_mutable_sequence(current)
        as_list.append(self.item)
        data[self.field] = as_list


class ExtendOp(Operation):
    field: str
    items: Sequence[Any]

    def apply(self, data: dict[str, Any], model_type: type[BaseModel], raise_on_missing: bool) -> None:
        current = data.get(self.field)
        as_list = _to_mutable_sequence(current)
        as_list.extend(self.items)
        data[self.field] = as_list


class RemoveOp(Operation):
    field: str
    target: Any

    def apply(self, data: dict[str, Any], model_type: type[BaseModel], raise_on_missing: bool) -> None:
        current = data.get(self.field)

        if isinstance(current, (list, set, frozenset)):
            as_list = _to_mutable_sequence(current)
            try:
                as_list.remove(self.target)
            except ValueError:
                if raise_on_missing:
                    raise FieldNotFoundError(f"Value {self.target!r} not found in '{self.field}'") from None
            data[self.field] = as_list
        elif isinstance(current, dict):
            if self.target in current:
                del current[self.target]
            elif raise_on_missing:
                raise FieldNotFoundError(f"Key {self.target!r} not found in '{self.field}'")


class SetItemOp(Operation):
    field: str
    items: dict[str, Any]

    def apply(self, data: dict[str, Any], model_type: type[BaseModel], raise_on_missing: bool) -> None:
        current = data.get(self.field)
        if not isinstance(current, dict):
            current = {}
        current.update(self.items)
        data[self.field] = current


class SetPathOp(Operation):
    path: str
    value: Any

    def apply(self, data: dict[str, Any], model_type: type[BaseModel], raise_on_missing: bool) -> None:
        segments = self.path.split(".")
        target = data
        for segment in segments[:-1]:
            if segment not in target or not isinstance(target[segment], dict):
                target[segment] = {}
            target = target[segment]
        target[segments[-1]] = self.value


def _to_mutable_sequence(current: Any) -> list[Any]:
    if isinstance(current, (set, frozenset)):
        return list(current)
    if isinstance(current, list):
        return current
    return []
