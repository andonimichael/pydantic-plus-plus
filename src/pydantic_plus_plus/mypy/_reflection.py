from __future__ import annotations

from mypy.nodes import TypeInfo, Var
from mypy.types import (
    NoneType,
    Type,
    UnionType,
    get_proper_type,
)

from pydantic_plus_plus.mypy._constants import PYDANTIC_INTERNAL_NAMES


def is_basemodel_subclass(info: TypeInfo) -> bool:
    return any(b.fullname == "pydantic.main.BaseModel" for b in info.mro)


def get_model_fields(model_info: TypeInfo) -> dict[str, Type]:
    fields: dict[str, Type] = {}
    for base in model_info.mro:
        for name, sym in base.names.items():
            if name in fields:
                continue
            if not isinstance(sym.node, Var) or sym.node.type is None:
                continue
            if name.startswith("_") or name in PYDANTIC_INTERNAL_NAMES:
                continue
            fields[name] = sym.node.type
    return fields


def is_optional_type(typ: Type) -> bool:
    proper = get_proper_type(typ)
    if isinstance(proper, UnionType):
        return any(isinstance(t, NoneType) for t in proper.items)
    return isinstance(proper, NoneType)


def make_optional(typ: Type) -> Type:
    proper_typ = get_proper_type(typ)
    if isinstance(proper_typ, UnionType) and any(isinstance(t, NoneType) for t in proper_typ.items):
        return typ
    return UnionType([typ, NoneType()])


def unwrap_optional(typ: Type) -> Type:
    proper = get_proper_type(typ)
    if isinstance(proper, UnionType):
        non_none = [t for t in proper.items if not isinstance(get_proper_type(t), NoneType)]
        if len(non_none) == 1:
            return non_none[0]
    return typ
