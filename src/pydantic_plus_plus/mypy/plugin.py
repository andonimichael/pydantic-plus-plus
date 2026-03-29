"""Mypy plugin for pydantic-plus-plus.

Enable in ``pyproject.toml``::

    [tool.mypy]
    plugins = ["pydantic_plus_plus.mypy"]
"""

from __future__ import annotations

from typing import Callable

from mypy.plugin import DynamicClassDefContext, FunctionContext, MethodContext, MethodSigContext, Plugin
from mypy.types import (
    CallableType as MypyCallableType,
    Type,
)
from pydantic_plus_plus.mypy import _partial as partial
from pydantic_plus_plus.mypy import _update as update


class PydanticPlusPlusPlugin(Plugin):
    def get_dynamic_class_hook(self, fullname: str) -> Callable[[DynamicClassDefContext], None] | None:
        if fullname in partial.ALL_HOOK_NAMES:
            return partial.dynamic_class_callback
        return None

    def get_function_hook(self, fullname: str) -> Callable[[FunctionContext], Type] | None:
        if fullname in partial.FUNCTION_NAMES:
            return partial.function_hook_callback
        return None

    def get_method_hook(self, fullname: str) -> Callable[[MethodContext], Type] | None:
        if fullname in partial.CLASS_METHOD_NAMES:
            return partial.function_hook_callback  # type: ignore[return-value]
        return None

    def get_method_signature_hook(self, fullname: str) -> Callable[[MethodSigContext], MypyCallableType] | None:
        if fullname in update.SET_METHOD_NAMES:
            return update.set_signature_callback
        if fullname in update.APPEND_METHOD_NAMES:
            return update.append_signature_callback
        if fullname in update.EXTEND_METHOD_NAMES:
            return update.extend_signature_callback
        if fullname in update.REMOVE_METHOD_NAMES:
            return update.remove_signature_callback
        if fullname in update.SET_ITEM_METHOD_NAMES:
            return update.set_item_signature_callback
        return None


def plugin(version: str) -> type[Plugin]:
    return PydanticPlusPlusPlugin
