"""Mypy plugin for pydantic-plus-plus.partial

When mypy sees ``partial(Model)`` or ``PartialBaseModel.from_model(Model)``,
this plugin creates a synthetic TypeInfo whose fields mirror the original
model's. For all-fields mode every field becomes Optional; for selective mode
(``partial(Model, "name")``) only the named fields do.
"""

from __future__ import annotations


from mypy.nodes import (
    ARG_NAMED,
    ARG_NAMED_OPT,
    ARG_POS,
    GDEF,
    MDEF,
    Argument,
    AssignmentStmt,
    Block,
    CallExpr,
    ClassDef,
    FuncDef,
    NameExpr,
    PassStmt,
    RefExpr,
    StrExpr,
    SymbolTable,
    SymbolTableNode,
    TempNode,
    TypeInfo,
    Var,
)
from mypy.plugin import DynamicClassDefContext, FunctionContext, MethodContext
from mypy.types import (
    AnyType,
    CallableType as MypyCallableType,
    Instance,
    NoneType,
    Type,
    TypeOfAny,
    TypeType,
    UnionType,
    get_proper_type,
)

FUNCTION_NAMES = {
    "pydantic_plus_plus.partial.api.partial",
    "pydantic_plus_plus.partial.partial",
}
CLASS_METHOD_NAMES = {
    "pydantic_plus_plus.partial.api.PartialBaseModel.from_model",
    "pydantic_plus_plus.partial.PartialBaseModel.from_model",
}
ALL_HOOK_NAMES = FUNCTION_NAMES | CLASS_METHOD_NAMES

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

_synthetic_cache: dict[str, TypeInfo] = {}


def dynamic_class_callback(ctx: DynamicClassDefContext) -> None:
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

    field_specs = _extract_field_specs_from_call(call)
    function_type = ctx.api.named_type("builtins.function", [])
    dict_str_any = ctx.api.named_type(
        "builtins.dict",
        [
            ctx.api.named_type("builtins.str", []),
            AnyType(TypeOfAny.explicit),
        ],
    )
    info = _build_partial_typeinfo(
        model_info,
        partial_base_info,
        caller_module.fullname,
        ctx.name,
        field_specs,
        function_type=function_type,
        dict_str_any=dict_str_any,
    )

    caller_module.names[ctx.name] = SymbolTableNode(GDEF, info)


def function_hook_callback(ctx: FunctionContext | MethodContext) -> Type:
    if not ctx.arg_types or not ctx.arg_types[0]:
        return ctx.default_return_type

    model_info = _extract_model_info_from_type(ctx.arg_types[0][0])
    if model_info is None:
        return ctx.default_return_type

    field_specs = _extract_field_specs_from_hook(ctx)
    cache_key = _build_cache_key(model_info, field_specs)

    if cache_key in _synthetic_cache:
        info = _synthetic_cache[cache_key]
        return TypeType(Instance(info, []))

    partial_base_info = _extract_partial_base_from_default(ctx.default_return_type)
    if partial_base_info is None:
        return ctx.default_return_type

    assigned_name = f"Partial{model_info.name}"
    function_type = ctx.api.named_generic_type("builtins.function", [])
    dict_str_any = ctx.api.named_generic_type(
        "builtins.dict",
        [
            ctx.api.named_generic_type("builtins.str", []),
            AnyType(TypeOfAny.explicit),
        ],
    )
    info = _build_partial_typeinfo(
        model_info,
        partial_base_info,
        model_info.module_name,
        assigned_name,
        field_specs,
        function_type=function_type,
        dict_str_any=dict_str_any,
    )

    return TypeType(Instance(info, []))


def _extract_field_specs_from_call(call: CallExpr) -> tuple[str, ...] | None:
    specs: list[str] = []
    for arg in call.args[1:]:
        if isinstance(arg, StrExpr):
            specs.append(arg.value)
    return tuple(specs) if specs else None


def _extract_field_specs_from_hook(ctx: FunctionContext | MethodContext) -> tuple[str, ...] | None:
    if len(ctx.args) < 2 or not ctx.args[1]:
        return None
    specs: list[str] = []
    for arg_expr in ctx.args[1]:
        if isinstance(arg_expr, StrExpr):
            specs.append(arg_expr.value)
    return tuple(specs) if specs else None


def _parse_field_specs(field_specs: tuple[str, ...]) -> tuple[set[str] | None, dict[str, tuple[str, ...]]]:
    optional_fields: set[str] = set()
    nested_raw: dict[str, list[str]] = {}
    is_wildcard = False
    for spec in field_specs:
        first, _, rest = spec.partition(".")
        if not rest:
            if first == "*":
                is_wildcard = True
            else:
                optional_fields.add(first)
        else:
            nested_raw.setdefault(first, []).append(rest)
    return None if is_wildcard else optional_fields, {k: tuple(v) for k, v in nested_raw.items()}


def _has_default_rvalue(stmt: AssignmentStmt) -> bool:
    rvalue = stmt.rvalue
    if isinstance(rvalue, TempNode):
        return False
    if isinstance(rvalue, CallExpr) and isinstance(rvalue.callee, RefExpr):
        fullname = rvalue.callee.fullname
        if fullname and fullname.endswith(".Field"):
            has_default_kwarg = any(n in ("default", "default_factory") for n in rvalue.arg_names)
            has_positional_default = bool(rvalue.args) and rvalue.arg_names[0] is None
            return has_default_kwarg or has_positional_default
    return True


def _get_fields_with_defaults(model_info: TypeInfo) -> frozenset[str]:
    result: set[str] = set()
    for base in model_info.mro:
        if base.fullname in ("builtins.object", "pydantic.main.BaseModel"):
            continue
        for stmt in base.defn.defs.body:
            if not isinstance(stmt, AssignmentStmt) or stmt.type is None:
                continue
            if len(stmt.lvalues) != 1 or not isinstance(stmt.lvalues[0], NameExpr):
                continue
            if _has_default_rvalue(stmt):
                result.add(stmt.lvalues[0].name)
    return frozenset(result)


def _make_optional(typ: Type) -> Type:
    proper_typ = get_proper_type(typ)
    if isinstance(proper_typ, UnionType) and any(isinstance(t, NoneType) for t in proper_typ.items):
        return typ
    return UnionType([typ, NoneType()])


def _is_optional_type(typ: Type) -> bool:
    proper = get_proper_type(typ)
    if isinstance(proper, UnionType):
        return any(isinstance(t, NoneType) for t in proper.items)
    return isinstance(proper, NoneType)


def _is_basemodel_subclass(info: TypeInfo) -> bool:
    return any(b.fullname == "pydantic.main.BaseModel" for b in info.mro)


def _with_dict_coercion(typ: Type, dict_str_any: Instance) -> Type:
    proper = get_proper_type(typ)
    if isinstance(proper, Instance) and _is_basemodel_subclass(proper.type):
        return UnionType([typ, dict_str_any])
    if isinstance(proper, UnionType):
        for item in proper.items:
            item_proper = get_proper_type(item)
            if isinstance(item_proper, Instance) and _is_basemodel_subclass(item_proper.type):
                return UnionType([*proper.items, dict_str_any])
    return typ


def _get_partial_base_info(api: DynamicClassDefContext) -> TypeInfo | None:
    partial_base_sym = api.api.lookup_fully_qualified_or_none("pydantic_plus_plus.partial.api.PartialBaseModel")
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


def _build_cache_key(model_info: TypeInfo, field_specs: tuple[str, ...] | None) -> str:
    if field_specs is not None:
        return f"{model_info.fullname}:{','.join(sorted(field_specs))}"
    return model_info.fullname


def _resolve_nested_partial_type(
    typ: Type,
    nested_specs: tuple[str, ...],
    partial_base_info: TypeInfo,
    module_name: str,
    function_type: Instance,
) -> Type:
    proper = get_proper_type(typ)
    if isinstance(proper, Instance):
        nested_info = _build_partial_typeinfo(
            proper.type,
            partial_base_info,
            module_name,
            f"Partial{proper.type.name}",
            nested_specs,
            function_type=function_type,
        )
        return Instance(nested_info, [])
    if isinstance(proper, UnionType):
        new_items = [
            _resolve_nested_partial_type(item, nested_specs, partial_base_info, module_name, function_type)
            for item in proper.items
        ]
        return UnionType(new_items)
    return typ


def _build_partial_typeinfo(
    model_info: TypeInfo,
    partial_base_info: TypeInfo,
    module_name: str,
    assigned_name: str,
    field_specs: tuple[str, ...] | None = None,
    *,
    function_type: Instance | None = None,
    dict_str_any: Instance | None = None,
) -> TypeInfo:
    cache_key = _build_cache_key(model_info, field_specs)
    if cache_key in _synthetic_cache:
        return _synthetic_cache[cache_key]

    cls_def = ClassDef(assigned_name, Block([]))
    cls_def.fullname = f"{module_name}.{assigned_name}"

    info = TypeInfo(SymbolTable(), cls_def, module_name)
    cls_def.info = info
    info.bases = [Instance(partial_base_info, [Instance(model_info, [])])]
    info.mro = [info] + partial_base_info.mro

    optional_fields: set[str] | None
    nested_specs: dict[str, tuple[str, ...]]
    if field_specs is not None:
        optional_fields, nested_specs = _parse_field_specs(field_specs)
    else:
        optional_fields = None
        nested_specs = {}

    original_field_types: dict[str, Type] = {}
    for base in model_info.mro:
        for name, sym in base.names.items():
            if name in info.names:
                continue
            if not isinstance(sym.node, Var) or sym.node.type is None:
                continue
            if name.startswith("_") or name in _PYDANTIC_INTERNAL_NAMES:
                continue

            original_type = sym.node.type
            is_terminal = optional_fields is None or name in optional_fields
            nested = nested_specs.get(name)

            if nested is not None and function_type is not None:
                field_type = _resolve_nested_partial_type(
                    original_type,
                    nested,
                    partial_base_info,
                    module_name,
                    function_type,
                )
                if is_terminal:
                    field_type = _make_optional(field_type)
            elif is_terminal:
                field_type = _make_optional(original_type)
            else:
                field_type = original_type

            if field_type is not original_type:
                original_field_types[name] = original_type

            var = Var(name, field_type)
            var.info = info
            var._fullname = f"{info.fullname}.{name}"
            var.is_initialized_in_class = True
            info.names[name] = SymbolTableNode(MDEF, var)

    _synthetic_cache[cache_key] = info

    if function_type is not None and "__init__" not in info.names:
        _add_init(info, function_type, _get_fields_with_defaults(model_info), dict_str_any, original_field_types)

    return info


def _add_init(
    info: TypeInfo,
    function_type: Instance,
    fields_with_defaults: frozenset[str] = frozenset(),
    dict_str_any: Instance | None = None,
    original_field_types: dict[str, Type] | None = None,
) -> None:
    self_type = Instance(info, [])
    args = [Argument(Var("self"), self_type, None, ARG_POS)]
    for name, sym in info.names.items():
        if isinstance(sym.node, Var) and sym.node.type is not None:
            param_type = sym.node.type
            original = original_field_types.get(name) if original_field_types else None
            if original is not None:
                param_type = UnionType([param_type, original])
            if dict_str_any is not None:
                param_type = _with_dict_coercion(param_type, dict_str_any)
            is_init_optional = _is_optional_type(sym.node.type) or name in fields_with_defaults
            arg_kind = ARG_NAMED_OPT if is_init_optional else ARG_NAMED
            args.append(Argument(Var(name), param_type, None, arg_kind))

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
