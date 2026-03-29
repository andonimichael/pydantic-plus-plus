from __future__ import annotations

from random import Random
from typing import TypeVar

from pydantic import BaseModel

from pydantic_plus_plus.dummy._constraints import validate_defaultable_fields, validate_optional_fields
from pydantic_plus_plus.dummy._generator import DummyGenerator

T = TypeVar("T", bound=BaseModel)


def dummy(
    model: type[T],
    *,
    set_nones: bool | set[str] = False,
    set_defaults: bool | set[str] = False,
    seed: int | None = None,
) -> T:
    """Generate a dummy instance of a Pydantic model populated with random data.

    The generated instance satisfies field constraints (``ge``, ``min_length``,
    etc.) and recursively populates nested ``BaseModel`` fields.

    Parameters
    ----------
    model:
        The Pydantic ``BaseModel`` subclass to instantiate.
    set_nones:
        When ``True``, every ``Optional`` field is set to ``None`` instead of
        generating a value. When ``False``, every ``Optional`` field is
        generated with a random value instead of None. Pass a ``set[str]`` of
        field names to apply this selectively.

        Raises ``InvalidFieldError`` if a named field is not ``Optional``. When
        both ``set_nones`` and ``set_defaults`` target the same field,
        ``set_nones`` takes precedence.
    set_defaults:
        When ``True``, every field that declares a default uses that default
        instead of generating a random value. When ``False``, every defaultable
        field is generated with a random value instead of the default. Pass a
        ``set[str]`` of field names to apply this selectively.

        Raises ``InvalidFieldError`` if a named field has no default.
    seed:
        Optional seed for the random number generator. Providing the same seed
        produces identical output, useful for deterministic tests.
    """
    if isinstance(set_nones, set):
        validate_optional_fields(model, set_nones)

    if isinstance(set_defaults, set):
        validate_defaultable_fields(model, set_defaults)

    random = Random(seed) if seed is not None else Random()
    generator = DummyGenerator(random=random, set_nones=set_nones, set_defaults=set_defaults)
    return generator.generate(model)
