"""Mypy plugin for pydantic-plus-plus.

When mypy sees ``partial(BaseModel)`` or
``PartialBaseModel.from_model(BaseModel)``, this plugin creates a synthetic
TypeInfo whose fields are ``Optional`` versions of the original model's fields.
This gives full field-level type safety and IDE autocompletion.

Enable in ``pyproject.toml``::

    [tool.mypy]
    plugins = ["pydantic_plus_plus.mypy_plugin"]
"""

from __future__ import annotations

from typing import Callable

from mypy.nodes import (
    ARG_NAMED_OPT,
    ARG_POS,
    MDEF,
    Argument,
    Block,
    ClassDef,
    FuncDef,
    PassStmt,
    SymbolTable,
    SymbolTableNode,
    TypeInfo,
    Var,
)
from mypy.plugin import CheckerPluginInterface, FunctionContext, MethodContext, Plugin
from mypy.types import (
    CallableType as MypyCallableType,
    Instance,
    NoneType,
    Type,
    TypeType,
    UnionType,
    get_proper_type,
)

PARTIAL_FUNC = "pydantic_plus_plus.partial.partial"
FROM_MODEL = "pydantic_plus_plus.partial.PartialBaseModel.from_model"

_synthetic_cache: dict[str, TypeInfo] = {}


def _make_optional(typ: Type) -> Type:
    proper_typ = get_proper_type(typ)
    if isinstance(proper_typ, UnionType) and any(isinstance(t, NoneType) for t in proper_typ.items):
        return typ
    return UnionType([typ, NoneType()])


def _build_partial_typeinfo(
    model_info: TypeInfo,
    partial_base_info: TypeInfo,
) -> TypeInfo:
    if model_info.fullname in _synthetic_cache:
        return _synthetic_cache[model_info.fullname]

    partial_name = f"Partial{model_info.name}"
    cls_def = ClassDef(partial_name, Block([]))
    cls_def.fullname = f"pydantic_plus_plus.partial.{partial_name}"

    info = TypeInfo(SymbolTable(), cls_def, "pydantic_plus_plus.partial")
    cls_def.info = info
    info.bases = [Instance(partial_base_info, [Instance(model_info, [])])]
    info.mro = [info] + partial_base_info.mro

    # Walk MRO to collect all fields, including inherited ones
    for base in model_info.mro:
        for name, sym in base.names.items():
            if name in info.names:
                continue  # already added from a more derived class
            if not isinstance(sym.node, Var) or sym.node.type is None:
                continue
            if name.startswith("_"):
                continue

            var = Var(name, _make_optional(sym.node.type))
            var.info = info
            var._fullname = f"{info.fullname}.{name}"
            var.is_initialized_in_class = True
            info.names[name] = SymbolTableNode(MDEF, var)

    _synthetic_cache[model_info.fullname] = info
    return info


def _add_init(info: TypeInfo, fields: dict[str, Type], api: CheckerPluginInterface) -> None:
    """Add a synthetic ``__init__`` so mypy accepts keyword construction."""
    function_type = api.named_generic_type("builtins.function", [])
    self_type = Instance(info, [])

    args = [Argument(Var("self"), self_type, None, ARG_POS)]
    for name, field_type in fields.items():
        args.append(Argument(Var(name), field_type, None, ARG_NAMED_OPT))

    arg_types = [arg.type_annotation for arg in args]
    arg_kinds = [arg.kind for arg in args]
    arg_names = [arg.variable.name for arg in args]

    sig = MypyCallableType(arg_types, arg_kinds, arg_names, NoneType(), function_type)  # type: ignore[arg-type]
    func = FuncDef("__init__", args, Block([PassStmt()]))
    func.info = info
    func.type = sig
    func._fullname = f"{info.fullname}.__init__"

    sym = SymbolTableNode(MDEF, func)
    sym.plugin_generated = True
    info.names["__init__"] = sym


def _extract_model_info(ctx: FunctionContext | MethodContext) -> TypeInfo | None:
    if not ctx.arg_types or not ctx.arg_types[0]:
        return None

    model_arg = get_proper_type(ctx.arg_types[0][0])

    if isinstance(model_arg, TypeType):
        inner = get_proper_type(model_arg.item)
        if isinstance(inner, Instance):
            return inner.type
        return None

    if isinstance(model_arg, MypyCallableType):
        ret = get_proper_type(model_arg.ret_type)
        if isinstance(ret, Instance):
            return ret.type
        return None

    return None


def _partial_callback(ctx: FunctionContext | MethodContext) -> Type:
    model_info = _extract_model_info(ctx)
    if model_info is None:
        return ctx.default_return_type

    # Extract PartialBaseModel TypeInfo from the default return type
    default = get_proper_type(ctx.default_return_type)
    if not isinstance(default, TypeType):
        return ctx.default_return_type
    inner = get_proper_type(default.item)
    if not isinstance(inner, Instance):
        return ctx.default_return_type
    partial_base_info = inner.type

    partial_info = _build_partial_typeinfo(model_info, partial_base_info)

    # Add __init__ if not already present (first call only)
    if "__init__" not in partial_info.names:
        fields = {
            name: sym.node.type
            for name, sym in partial_info.names.items()
            if isinstance(sym.node, Var) and sym.node.type is not None
        }
        _add_init(partial_info, fields, ctx.api)

    return TypeType(Instance(partial_info, []))


class PydanticPlusPlusPlugin(Plugin):
    def get_function_hook(self, fullname: str) -> Callable[[FunctionContext], Type] | None:
        if fullname == PARTIAL_FUNC:
            return _partial_callback  # type: ignore[return-value]
        return None

    def get_method_hook(self, fullname: str) -> Callable[[MethodContext], Type] | None:
        if fullname == FROM_MODEL:
            return _partial_callback  # type: ignore[return-value]
        return None


def plugin(version: str) -> type[Plugin]:
    return PydanticPlusPlusPlugin
