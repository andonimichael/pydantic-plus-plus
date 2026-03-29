from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from pydantic_plus_plus.update._validators import (
    validate_dict_field,
    validate_field_exists,
    validate_removable_field,
    validate_sequence_field,
)
from pydantic_plus_plus.update._operations import (
    AppendOp,
    ExtendOp,
    Operation,
    RemoveOp,
    SetItemOp,
    SetOp,
    SetPathOp,
)
from pydantic_plus_plus.update.errors import InvalidOperationError

T = TypeVar("T", bound=BaseModel)


class ModelUpdater(Generic[T]):
    """A builder for type-safe updates to Pydantic ``BaseModel`` instances.

    ``ModelUpdater`` accumulates update operations (set, append, extend,
    set_item, remove, set_path) and applies them all at once via :meth:`apply`,
    returning a new model instance. This class is immutable -- every mutation
     method returns a **new** ``ModelUpdater``.

    Use the :func:`update` function as the primary entry point::

        updated = ModelUpdater(user).set(name="Bob").append(tags="vip").apply()

    Parameters
    ----------
    instance:
        The model instance to update.
    raise_on_missing:
        When ``True``, :meth:`remove` raises ``FieldNotFoundError`` if the
        element or key is not present in the collection. Defaults to ``False``
        (silent no-op).
    """

    _instance: T
    _operations: tuple[Operation, ...]
    _raise_on_missing: bool

    def __init__(self, instance: T, *, raise_on_missing: bool = False) -> None:
        self._instance = instance
        self._operations = ()
        self._raise_on_missing = raise_on_missing

    @classmethod
    def with_operation(cls, updater: ModelUpdater[T], operation: Operation) -> ModelUpdater[T]:
        new: ModelUpdater[T] = object.__new__(cls)
        new._instance = updater._instance
        new._operations = updater._operations + (operation,)
        new._raise_on_missing = updater._raise_on_missing
        return new

    @property
    def instance(self) -> T:
        """The original model instance this updater was created from."""
        return self._instance

    def set(self, **kwargs: Any) -> ModelUpdater[T]:
        """Set one or more fields to new values.

        For nested ``BaseModel`` fields, accepts model instances, raw dicts
        (deep-merged with the current value), or another ``ModelUpdater``
        (resolved at :meth:`apply` time).

        Raises :class:`~pydantic_plus_plus.update.errors.FieldNotFoundError`
        if a field name does not exist on the model.
        """
        result = self
        for field, value in kwargs.items():
            validate_field_exists(result.instance, field)
            result = ModelUpdater.with_operation(result, SetOp(field=field, value=value))
        return result

    def append(self, **kwargs: Any) -> ModelUpdater[T]:
        """Append a single element to a ``list``, ``set``, or ``frozenset`` field.

        Raises :class:`~pydantic_plus_plus.update.errors.InvalidOperationError`
        if the field is not a sequence type.
        """
        result = self
        for field, item in kwargs.items():
            validate_sequence_field(result.instance, field)
            result = ModelUpdater.with_operation(result, AppendOp(field=field, item=item))
        return result

    def extend(self, **kwargs: Any) -> ModelUpdater[T]:
        """Extend a ``list``, ``set``, or ``frozenset`` field with multiple elements.

        Raises :class:`~pydantic_plus_plus.update.errors.InvalidOperationError`
        if the field is not a sequence type.
        """
        result = self
        for field, items in kwargs.items():
            validate_sequence_field(result.instance, field)
            result = ModelUpdater.with_operation(result, ExtendOp(field=field, items=items))
        return result

    def set_item(self, **kwargs: Any) -> ModelUpdater[T]:
        """Merge key-value pairs into a ``dict`` field.

        Each value must itself be a ``dict`` whose entries are merged into the
        current field value.

        Raises :class:`~pydantic_plus_plus.update.errors.InvalidOperationError`
        if the field is not a ``dict`` type or the value is not a ``dict``.
        """
        result = self
        for field, items in kwargs.items():
            validate_dict_field(result.instance, field)
            if not isinstance(items, dict):
                raise InvalidOperationError(f"Value for '{field}' must be a dict, got {type(items).__name__}")
            result = ModelUpdater.with_operation(result, SetItemOp(field=field, items=items))
        return result

    def remove(self, **kwargs: Any) -> ModelUpdater[T]:
        """Remove an element from a sequence field or a key from a ``dict`` field.

        By default, removing a non-existent element or key is a silent no-op.
        Pass ``raise_on_missing=True`` to the :func:`update` call to raise
        :class:`~pydantic_plus_plus.update.errors.FieldNotFoundError` instead.

        Raises :class:`~pydantic_plus_plus.update.errors.InvalidOperationError`
        if the field is neither a sequence nor a ``dict``.
        """
        result = self
        for field, target in kwargs.items():
            validate_removable_field(result.instance, field)
            result = ModelUpdater.with_operation(result, RemoveOp(field=field, target=target))
        return result

    def set_path(self, path: str, value: Any) -> ModelUpdater[T]:
        """Set a value at an arbitrary dot-separated path.

        This is an untyped escape hatch for deeply nested updates. No static
        type checking is performed — validation happens at :meth:`apply` time
        via Pydantic's ``model_validate``.

        Example::

            update(user).set_path("address.geo.lat", 40.7).apply()
        """
        return ModelUpdater.with_operation(self, SetPathOp(path=path, value=value))

    def apply(self) -> T:
        """Replay all accumulated operations and return a new model instance.

        Always returns a new instance (even with no operations). The original
        model is never mutated. Subclass types are preserved.
        """
        return self.apply_to(self.instance)

    def apply_to(self, instance: T) -> T:
        """Apply this updater's operations to a specific model instance.

        Like :meth:`apply`, but uses the provided *instance* instead of the
        one stored at construction time.
        """
        data = instance.model_dump()
        for operation in self._operations:
            operation.apply(data, type(instance), self._raise_on_missing)
        return type(instance).model_validate(data)


def update(instance: T, *, raise_on_missing: bool = False) -> ModelUpdater[T]:
    """Create a :class:`ModelUpdater` for the given model instance.

    This is the primary entry point for type-safe model updates::

        updated = update(user).set(name="Bob", age=31).apply()

    Parameters
    ----------
    instance:
        The model instance to update.
    raise_on_missing:
        When ``True``, :meth:`~ModelUpdater.remove` raises
        ``FieldNotFoundError`` if the target element or key does not exist.
        Defaults to ``False``.
    """
    return ModelUpdater(instance, raise_on_missing=raise_on_missing)
