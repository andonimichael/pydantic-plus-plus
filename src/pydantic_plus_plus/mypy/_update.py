from __future__ import annotations

from mypy.nodes import ARG_NAMED_OPT, ArgKind, TypeInfo, Var
from mypy.plugin import MethodSigContext
from mypy.types import (
    AnyType,
    CallableType as MypyCallableType,
    Instance,
    NoneType,
    Type,
    TypeOfAny,
    UnionType,
    get_proper_type,
)

_PYDANTIC_INTERNAL_NAMES = frozenset(
    {
        "model_config",
        "model_fields",
        "model_computed_fields",
        "model_extra",
        "model_fields_set",
        "model_post_init",
    }
)

_SEQUENCE_FULLNAMES = frozenset(
    {
        "builtins.list",
        "builtins.set",
        "builtins.frozenset",
    }
)

SET_METHOD_NAMES = frozenset(
    {
        "pydantic_plus_plus.update.api.ModelUpdater.set",
    }
)

APPEND_METHOD_NAMES = frozenset(
    {
        "pydantic_plus_plus.update.api.ModelUpdater.append",
    }
)

EXTEND_METHOD_NAMES = frozenset(
    {
        "pydantic_plus_plus.update.api.ModelUpdater.extend",
    }
)

REMOVE_METHOD_NAMES = frozenset(
    {
        "pydantic_plus_plus.update.api.ModelUpdater.remove",
    }
)

MERGE_ITEMS_METHOD_NAMES = frozenset(
    {
        "pydantic_plus_plus.update.api.ModelUpdater.merge_items",
    }
)

ALL_METHOD_SIGNATURE_NAMES = (
    SET_METHOD_NAMES | APPEND_METHOD_NAMES | EXTEND_METHOD_NAMES | REMOVE_METHOD_NAMES | MERGE_ITEMS_METHOD_NAMES
)


def set_signature_callback(ctx: MethodSigContext) -> MypyCallableType:
    model_info = _extract_model_info(ctx)
    if model_info is None:
        return ctx.default_signature

    fields = _get_model_fields(model_info)
    instance_type = get_proper_type(ctx.type)
    updater_type_info = instance_type.type if isinstance(instance_type, Instance) else None

    dict_str_any = ctx.api.named_generic_type(
        "builtins.dict",
        [ctx.api.named_generic_type("builtins.str", []), AnyType(TypeOfAny.explicit)],
    )

    kwargs = [
        (name, _build_set_param_type(field_type, updater_type_info, dict_str_any))
        for name, field_type in fields.items()
    ]
    return _copy_with_expanded_kwargs(ctx, kwargs)


def append_signature_callback(ctx: MethodSigContext) -> MypyCallableType:
    model_info = _extract_model_info(ctx)
    if model_info is None:
        return ctx.default_signature

    fields = _get_model_fields(model_info)
    kwargs: list[tuple[str, Type]] = []
    for name, field_type in fields.items():
        element_type = _get_element_type(field_type)
        if element_type is not None:
            kwargs.append((name, element_type))

    return _copy_with_expanded_kwargs(ctx, kwargs)


def extend_signature_callback(ctx: MethodSigContext) -> MypyCallableType:
    model_info = _extract_model_info(ctx)
    if model_info is None:
        return ctx.default_signature

    fields = _get_model_fields(model_info)
    kwargs: list[tuple[str, Type]] = []
    for name, field_type in fields.items():
        element_type = _get_element_type(field_type)
        if element_type is not None:
            sequence_of_element = ctx.api.named_generic_type("builtins.list", [element_type])
            kwargs.append((name, sequence_of_element))

    return _copy_with_expanded_kwargs(ctx, kwargs)


def remove_signature_callback(ctx: MethodSigContext) -> MypyCallableType:
    model_info = _extract_model_info(ctx)
    if model_info is None:
        return ctx.default_signature

    fields = _get_model_fields(model_info)
    kwargs: list[tuple[str, Type]] = []
    for name, field_type in fields.items():
        element_type = _get_element_type(field_type)
        if element_type is not None:
            kwargs.append((name, element_type))
            continue

        key_type = _get_dict_key_type(field_type)
        if key_type is not None:
            kwargs.append((name, key_type))

    return _copy_with_expanded_kwargs(ctx, kwargs)


def merge_items_signature_callback(ctx: MethodSigContext) -> MypyCallableType:
    model_info = _extract_model_info(ctx)
    if model_info is None:
        return ctx.default_signature

    fields = _get_model_fields(model_info)
    kwargs: list[tuple[str, Type]] = []
    for name, field_type in fields.items():
        dict_instance = _get_dict_instance(field_type)
        if dict_instance is not None:
            kwargs.append((name, dict_instance))

    return _copy_with_expanded_kwargs(ctx, kwargs)


def _extract_model_info(ctx: MethodSigContext) -> TypeInfo | None:
    instance_type = get_proper_type(ctx.type)
    if not isinstance(instance_type, Instance) or not instance_type.args:
        return None
    model_type = get_proper_type(instance_type.args[0])
    if isinstance(model_type, Instance):
        return model_type.type
    return None


def _unwrap_optional(typ: Type) -> Type:
    proper = get_proper_type(typ)
    if isinstance(proper, UnionType):
        non_none = [t for t in proper.items if not isinstance(get_proper_type(t), NoneType)]
        if len(non_none) == 1:
            return non_none[0]
    return typ


def _is_basemodel_subclass(info: TypeInfo) -> bool:
    return any(base.fullname == "pydantic.main.BaseModel" for base in info.mro)


def _get_model_fields(model_info: TypeInfo) -> dict[str, Type]:
    fields: dict[str, Type] = {}
    for base in model_info.mro:
        for name, sym in base.names.items():
            if name in fields:
                continue
            if not isinstance(sym.node, Var) or sym.node.type is None:
                continue
            if name.startswith("_") or name in _PYDANTIC_INTERNAL_NAMES:
                continue
            fields[name] = sym.node.type
    return fields


def _get_element_type(typ: Type) -> Type | None:
    proper = get_proper_type(_unwrap_optional(typ))
    if isinstance(proper, Instance) and proper.type.fullname in _SEQUENCE_FULLNAMES and proper.args:
        return proper.args[0]
    return None


def _get_dict_key_type(typ: Type) -> Type | None:
    proper = get_proper_type(_unwrap_optional(typ))
    if isinstance(proper, Instance) and proper.type.fullname == "builtins.dict" and len(proper.args) >= 1:
        return proper.args[0]
    return None


def _get_dict_instance(typ: Type) -> Instance | None:
    proper = get_proper_type(_unwrap_optional(typ))
    if isinstance(proper, Instance) and proper.type.fullname == "builtins.dict":
        return proper
    return None


def _build_set_param_type(
    field_type: Type,
    updater_type_info: TypeInfo | None,
    dict_str_any: Instance,
) -> Type:
    unwrapped = _unwrap_optional(field_type)
    proper = get_proper_type(unwrapped)
    if isinstance(proper, Instance) and _is_basemodel_subclass(proper.type):
        types: list[Type] = [field_type, dict_str_any]
        if updater_type_info is not None:
            types.append(Instance(updater_type_info, [proper]))
        return UnionType(types)
    return field_type


def _copy_with_expanded_kwargs(
    ctx: MethodSigContext,
    kwargs: list[tuple[str, Type]],
) -> MypyCallableType:
    sig = ctx.default_signature
    arg_types: list[Type] = []
    arg_kinds: list[ArgKind] = []
    arg_names: list[str | None] = []

    for name, typ in kwargs:
        arg_types.append(typ)
        arg_kinds.append(ARG_NAMED_OPT)
        arg_names.append(name)

    return MypyCallableType(
        arg_types=arg_types,
        arg_kinds=arg_kinds,
        arg_names=arg_names,
        ret_type=sig.ret_type,
        fallback=sig.fallback,
        variables=sig.variables,
    )
