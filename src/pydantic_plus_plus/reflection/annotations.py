from __future__ import annotations

import types
from typing import Any, Optional, Union, get_args, get_origin

from pydantic import BaseModel


def is_optional(annotation: Any) -> bool:
    if is_union_type(annotation, unwrap=False):
        return type(None) in get_args(annotation)
    return annotation is type(None)


def unwrap_optional(annotation: Any) -> Any:
    if is_union_type(annotation, unwrap=False):
        args = get_args(annotation)
        non_none = [arg for arg in args if arg is not type(None)]
        if len(non_none) == 1:
            return non_none[0]
    return annotation


def make_optional(annotation: Any) -> Any:
    if is_optional(annotation):
        return annotation
    return Optional[annotation]


def is_base_model_type(annotation: Any, *, unwrap: bool = True) -> bool:
    if unwrap:
        annotation = unwrap_optional(annotation)
    return isinstance(annotation, type) and issubclass(annotation, BaseModel)


def is_union_type(annotation: Any, *, unwrap: bool = True) -> bool:
    if unwrap:
        annotation = unwrap_optional(annotation)
    return isinstance(annotation, types.UnionType) or get_origin(annotation) is Union


def is_collection_type(annotation: Any, *, unwrap: bool = True) -> bool:
    if unwrap:
        annotation = unwrap_optional(annotation)
    origin = get_origin(annotation)
    return origin in (list, set, frozenset)


def is_list_type(annotation: Any, *, unwrap: bool = True) -> bool:
    if unwrap:
        annotation = unwrap_optional(annotation)
    origin = get_origin(annotation)
    return origin is list


def is_set_type(annotation: Any, *, unwrap: bool = True) -> bool:
    if unwrap:
        annotation = unwrap_optional(annotation)
    origin = get_origin(annotation)
    return origin is set


def is_frozenset_type(annotation: Any, *, unwrap: bool = True) -> bool:
    if unwrap:
        annotation = unwrap_optional(annotation)
    origin = get_origin(annotation)
    return origin is frozenset


def is_dict_type(annotation: Any, *, unwrap: bool = True) -> bool:
    if unwrap:
        annotation = unwrap_optional(annotation)
    origin = get_origin(annotation)
    return origin is dict
