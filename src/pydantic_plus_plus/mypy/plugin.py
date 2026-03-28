"""Mypy plugin for pydantic-plus-plus.

When mypy sees ``partial(BaseModel)`` or
``PartialBaseModel.from_model(BaseModel)``, this plugin creates a synthetic
TypeInfo whose fields are ``Optional`` versions of the original model's fields.
This gives full field-level type safety and IDE autocompletion.

Enable in ``pyproject.toml``::

    [tool.mypy]
    plugins = ["pydantic_plus_plus.mypy"]
"""

from __future__ import annotations

from typing import Callable

from mypy.nodes import (
    ARG_NAMED_OPT,
    ARG_POS,
    GDEF,
    MDEF,
    Argument,
    Block,
    CallExpr,
    ClassDef,
    FuncDef,
    NameExpr,
    PassStmt,
    RefExpr,
    SymbolTable,
    SymbolTableNode,
    TypeInfo,
    Var,
)
from mypy.plugin import DynamicClassDefContext, FunctionContext, MethodContext, Plugin
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


def _get_partial_base_info(api: DynamicClassDefContext) -> TypeInfo | None:
    partial_base_sym = api.api.lookup_fully_qualified_or_none("pydantic_plus_plus.partial.PartialBaseModel")
    if partial_base_sym is None or not isinstance(partial_base_sym.node, TypeInfo):
        return None
    return partial_base_sym.node


def _resolve_model_info(call: CallExpr, api: DynamicClassDefContext) -> TypeInfo | None:
    if not call.args:
        return None

    first_arg = call.args[0]
    if not isinstance(first_arg, RefExpr):
        return None

    if isinstance(first_arg, NameExpr) and first_arg.fullname:
        sym = api.api.lookup_fully_qualified_or_none(first_arg.fullname)
        if sym is not None and isinstance(sym.node, TypeInfo):
            return sym.node

    if first_arg.node is not None and isinstance(first_arg.node, TypeInfo):
        return first_arg.node

    return None


def _build_partial_typeinfo(
    model_info: TypeInfo,
    partial_base_info: TypeInfo,
    module_name: str,
    assigned_name: str,
) -> TypeInfo:
    cache_key = model_info.fullname
    if cache_key in _synthetic_cache:
        return _synthetic_cache[cache_key]

    cls_def = ClassDef(assigned_name, Block([]))
    cls_def.fullname = f"{module_name}.{assigned_name}"

    info = TypeInfo(SymbolTable(), cls_def, module_name)
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

    _synthetic_cache[cache_key] = info
    return info


def _add_init(info: TypeInfo, function_type: Instance) -> None:
    self_type = Instance(info, [])

    args = [Argument(Var("self"), self_type, None, ARG_POS)]
    for name, sym in info.names.items():
        if isinstance(sym.node, Var) and sym.node.type is not None:
            args.append(Argument(Var(name), sym.node.type, None, ARG_NAMED_OPT))

    arg_types = [arg.type_annotation for arg in args]
    arg_kinds = [arg.kind for arg in args]
    arg_names = [arg.variable.name for arg in args]

    sig = MypyCallableType(arg_types, arg_kinds, arg_names, NoneType(), function_type)  # type: ignore[arg-type]
    func = FuncDef("__init__", args, Block([PassStmt()]))
    func.info = info
    func.type = sig
    func._fullname = f"{info.fullname}.__init__"

    sym_node = SymbolTableNode(MDEF, func)
    sym_node.plugin_generated = True
    info.names["__init__"] = sym_node


def _dynamic_class_callback(ctx: DynamicClassDefContext) -> None:
    call = ctx.call

    model_info = _resolve_model_info(call, ctx)
    if model_info is None:
        return

    partial_base_info = _get_partial_base_info(ctx)
    if partial_base_info is None:
        return

    caller_module = ctx.api.modules.get(ctx.api.cur_mod_id)  # type: ignore[attr-defined]
    if caller_module is None:
        return

    info = _build_partial_typeinfo(model_info, partial_base_info, caller_module.fullname, ctx.name)

    if "__init__" not in info.names:
        function_type = ctx.api.named_type("builtins.function", [])
        _add_init(info, function_type)

    caller_module.names[ctx.name] = SymbolTableNode(GDEF, info)


def _extract_model_info_from_type(typ: Type) -> TypeInfo | None:
    proper = get_proper_type(typ)
    if isinstance(proper, TypeType):
        inner = get_proper_type(proper.item)
        if isinstance(inner, Instance):
            return inner.type
    if isinstance(proper, MypyCallableType):
        ret = get_proper_type(proper.ret_type)
        if isinstance(ret, Instance):
            return ret.type
    return None


def _extract_partial_base_from_default(default_return_type: Type) -> TypeInfo | None:
    proper = get_proper_type(default_return_type)
    if isinstance(proper, TypeType):
        inner = get_proper_type(proper.item)
        if isinstance(inner, Instance):
            return inner.type
    return None


def _function_hook_callback(ctx: FunctionContext | MethodContext) -> Type:
    if not ctx.arg_types or not ctx.arg_types[0]:
        return ctx.default_return_type

    model_info = _extract_model_info_from_type(ctx.arg_types[0][0])
    if model_info is None:
        return ctx.default_return_type

    cache_key = model_info.fullname
    if cache_key in _synthetic_cache:
        info = _synthetic_cache[cache_key]
        return TypeType(Instance(info, []))

    partial_base_info = _extract_partial_base_from_default(ctx.default_return_type)
    if partial_base_info is None:
        return ctx.default_return_type

    assigned_name = f"Partial{model_info.name}"
    info = _build_partial_typeinfo(model_info, partial_base_info, model_info.module_name, assigned_name)

    if "__init__" not in info.names:
        function_type = ctx.api.named_generic_type("builtins.function", [])
        _add_init(info, function_type)

    return TypeType(Instance(info, []))


class PydanticPlusPlusPlugin(Plugin):
    def get_dynamic_class_hook(self, fullname: str) -> Callable[[DynamicClassDefContext], None] | None:
        if fullname in (PARTIAL_FUNC, FROM_MODEL):
            return _dynamic_class_callback
        return None

    def get_function_hook(self, fullname: str) -> Callable[[FunctionContext], Type] | None:
        if fullname == PARTIAL_FUNC:
            return _function_hook_callback
        return None

    def get_method_hook(self, fullname: str) -> Callable[[MethodContext], Type] | None:
        if fullname == FROM_MODEL:
            return _function_hook_callback  # type: ignore[return-value]
        return None


def plugin(version: str) -> type[Plugin]:
    return PydanticPlusPlusPlugin
