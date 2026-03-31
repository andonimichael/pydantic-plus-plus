from __future__ import annotations

from typing import ClassVar, Generic, TypeVar, cast, overload

from pydantic import BaseModel

from pydantic_plus_plus.partial._field_selection import FieldSelection
from pydantic_plus_plus.partial._merge import deep_merge
from pydantic_plus_plus.partial._partial import create_partial

T = TypeVar("T", bound=BaseModel)


class PartialBaseModel(BaseModel, Generic[T]):
    """Base class for partial Pydantic BaseModels.

    Overrides model fields as ``Optional[T]`` with a default of ``None``.

    Provides :meth:`apply` for deep-merging a partial into an existing
    model instance, and :meth:`from_model` for creating partial classes.

    Three calling conventions are supported::

        partial(User)                          # all fields optional, recursive
        partial(User, recursive=False)         # all fields optional, non-recursive
        partial(User, "name", "address.city")  # Only override selected fields as optional
    """

    _original_model: ClassVar[type[BaseModel]]

    @classmethod
    @overload
    def from_model(cls, model: type[T]) -> type[PartialBaseModel[T]]: ...

    @classmethod
    @overload
    def from_model(cls, model: type[T], *fields: str) -> type[PartialBaseModel[T]]: ...

    @classmethod
    @overload
    def from_model(cls, model: type[T], *, recursive: bool) -> type[PartialBaseModel[T]]: ...

    @classmethod
    def from_model(cls, model: type[T], *fields: str, recursive: bool = True) -> type[PartialBaseModel[T]]:
        """Create a standalone partial class from *model*."""
        if fields:
            field_selection = FieldSelection.parse(*fields)
            field_selection.validate(model)
            return create_partial(model, field_selection=field_selection)
        else:
            return create_partial(model, recursive=recursive)

    def apply(self, instance: T) -> T:
        """Deep-merge this partial's set fields into *instance* and return a
        new Pydantic model.

        Only fields that were explicitly provided when constructing the partial
        are merged. Nested models are merged recursively so that untouched
        nested fields are preserved.
        """
        base_data = instance.model_dump()
        update_data = self.model_dump(exclude_unset=True)
        merged = deep_merge(base_data, update_data)

        original_model = self.__class__._original_model
        return cast(T, original_model.model_validate(merged))


@overload
def partial(model: type[T]) -> type[PartialBaseModel[T]]: ...


@overload
def partial(model: type[T], *fields: str) -> type[PartialBaseModel[T]]: ...


@overload
def partial(model: type[T], *, recursive: bool) -> type[PartialBaseModel[T]]: ...


def partial(model: type[T], *fields: str, recursive: bool = True) -> type[PartialBaseModel[T]]:
    """Create a standalone partial class from a Pydantic model.

    When called without field specs, all fields become ``Optional`` with a
    default of ``None``::

        PartialUser = partial(User)
        PartialUser = partial(User, recursive=False)

    When called with field specs, only the specified fields are made optional.
    Supports dot-notation for nested fields and wildcards::

        PartialUser = partial(User, "name", "email")
        PartialUser = partial(User, "address.city")
        PartialUser = partial(User, "address.*")
    """
    return PartialBaseModel.from_model(model, *fields, recursive=recursive)
