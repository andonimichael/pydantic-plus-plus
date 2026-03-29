from __future__ import annotations

import importlib
import inspect
import pkgutil
from types import ModuleType
from typing import Union


def scan_modules(
    modules: tuple[Union[str, ModuleType], ...],
    base: type,
    *,
    include_base: bool,
    include_abstract: bool,
) -> frozenset[type]:
    found: set[type] = set()
    for module_ref in modules:
        found.update(_walk_module(module_ref, base, include_base=include_base, include_abstract=include_abstract))
    return frozenset(found)


def _walk_module(
    module_ref: Union[str, ModuleType],
    base: type,
    *,
    include_base: bool,
    include_abstract: bool,
) -> set[type]:
    found: set[type] = set()
    root = _import_module(module_ref)
    found.update(_collect_classes(root, base, include_base=include_base, include_abstract=include_abstract))

    package_path = getattr(root, "__path__", None)
    if package_path is not None:
        for _importer, submodule_name, _is_pkg in pkgutil.walk_packages(package_path, prefix=root.__name__ + "."):
            submodule = importlib.import_module(submodule_name)
            found.update(
                _collect_classes(
                    submodule,
                    base,
                    include_base=include_base,
                    include_abstract=include_abstract,
                )
            )

    return found


def _import_module(module: Union[str, ModuleType]) -> ModuleType:
    if isinstance(module, str):
        return importlib.import_module(module)
    return module


def _collect_classes(module: ModuleType, base: type, *, include_base: bool, include_abstract: bool) -> set[type]:
    found: set[type] = set()
    for _name, obj in inspect.getmembers(module, inspect.isclass):
        if not issubclass(obj, base):
            continue
        if obj is base:
            if include_base:
                found.add(obj)
            continue
        if not include_abstract and inspect.isabstract(obj):
            continue
        found.add(obj)
    return found
