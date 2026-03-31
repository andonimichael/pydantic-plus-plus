from __future__ import annotations

import importlib

import pytest
from pydantic import BaseModel

from pydantic_plus_plus.registry import AmbiguousModelError, ModelNotFoundError, ModelRegistry

BASIC_PKG = "tests.registry.fixtures.basic"
WITH_BASE_PKG = "tests.registry.fixtures.with_base"
WITH_ABSTRACT_PKG = "tests.registry.fixtures.with_abstract"
AMBIGUOUS_PKG = "tests.registry.fixtures.ambiguous"


def _model_names(registry: ModelRegistry[BaseModel]) -> set[str]:
    return {model.__name__ for model in registry}


class TestBasicScanning:
    def test_discovers_models_in_package(self) -> None:
        registry: ModelRegistry[BaseModel] = ModelRegistry(BASIC_PKG)
        assert _model_names(registry) == {"UserModel", "OrderModel", "DeepModel"}

    def test_discovers_models_from_module_object(self) -> None:
        module = importlib.import_module(BASIC_PKG)
        registry: ModelRegistry[BaseModel] = ModelRegistry(module)
        assert "UserModel" in registry
        assert "OrderModel" in registry

    def test_multiple_modules(self) -> None:
        registry: ModelRegistry[BaseModel] = ModelRegistry(BASIC_PKG, WITH_BASE_PKG)
        names = _model_names(registry)
        assert "UserModel" in names
        assert "SystemPrompt" in names


class TestBaseTypeFiltering:
    def test_filters_by_base_type(self) -> None:
        base_prompt = _get_class(WITH_BASE_PKG, "models", "BasePrompt")
        registry = ModelRegistry(WITH_BASE_PKG, base=base_prompt)
        names = _model_names(registry)
        assert names == {"SystemPrompt", "UserPrompt"}

    def test_include_base(self) -> None:
        base_prompt = _get_class(WITH_BASE_PKG, "models", "BasePrompt")
        registry = ModelRegistry(WITH_BASE_PKG, base=base_prompt, include_base=True)
        names = _model_names(registry)
        assert names == {"BasePrompt", "SystemPrompt", "UserPrompt"}


class TestAbstractFiltering:
    def test_excludes_abstract_by_default(self) -> None:
        registry: ModelRegistry[BaseModel] = ModelRegistry(WITH_ABSTRACT_PKG)
        names = _model_names(registry)
        assert "ConcreteConfig" in names
        assert "AbstractConfig" not in names

    def test_include_abstract(self) -> None:
        registry: ModelRegistry[BaseModel] = ModelRegistry(WITH_ABSTRACT_PKG, include_abstract=True)
        names = _model_names(registry)
        assert "ConcreteConfig" in names
        assert "AbstractConfig" in names


class TestLookup:
    def test_getitem_by_short_name(self) -> None:
        registry: ModelRegistry[BaseModel] = ModelRegistry(BASIC_PKG)
        assert registry["UserModel"].__name__ == "UserModel"

    def test_getitem_by_qualified_name(self) -> None:
        registry: ModelRegistry[BaseModel] = ModelRegistry(BASIC_PKG)
        qualified = f"{BASIC_PKG}.models.UserModel"
        assert registry[qualified].__name__ == "UserModel"

    def test_getitem_not_found_raises(self) -> None:
        registry: ModelRegistry[BaseModel] = ModelRegistry(BASIC_PKG)
        with pytest.raises(ModelNotFoundError):
            registry["Nonexistent"]

    def test_getitem_ambiguous_raises(self) -> None:
        registry: ModelRegistry[BaseModel] = ModelRegistry(AMBIGUOUS_PKG)
        with pytest.raises(AmbiguousModelError):
            registry["SharedName"]

    def test_ambiguous_resolved_by_qualified_name(self) -> None:
        registry: ModelRegistry[BaseModel] = ModelRegistry(AMBIGUOUS_PKG)
        result = registry[f"{AMBIGUOUS_PKG}.module_a.SharedName"]
        assert result.__module__ == f"{AMBIGUOUS_PKG}.module_a"


class TestGet:
    def test_returns_none_for_not_found(self) -> None:
        registry: ModelRegistry[BaseModel] = ModelRegistry(BASIC_PKG)
        assert registry.get("Nonexistent") is None

    def test_raises_for_ambiguous(self) -> None:
        registry: ModelRegistry[BaseModel] = ModelRegistry(AMBIGUOUS_PKG)
        with pytest.raises(AmbiguousModelError):
            registry.get("SharedName")

    def test_returns_model_when_unambiguous(self) -> None:
        registry: ModelRegistry[BaseModel] = ModelRegistry(BASIC_PKG)
        result = registry.get("UserModel")
        assert result is not None
        assert result.__name__ == "UserModel"


class TestCollectionProtocol:
    def test_len(self) -> None:
        registry: ModelRegistry[BaseModel] = ModelRegistry(BASIC_PKG)
        assert len(registry) == 3

    def test_iter(self) -> None:
        registry: ModelRegistry[BaseModel] = ModelRegistry(BASIC_PKG)
        assert _model_names(registry) == {"UserModel", "OrderModel", "DeepModel"}

    def test_contains_with_class(self) -> None:
        registry: ModelRegistry[BaseModel] = ModelRegistry(BASIC_PKG)
        user_model = registry["UserModel"]
        assert user_model in registry

    def test_contains_with_short_name(self) -> None:
        registry: ModelRegistry[BaseModel] = ModelRegistry(BASIC_PKG)
        assert "UserModel" in registry

    def test_contains_with_qualified_name(self) -> None:
        registry: ModelRegistry[BaseModel] = ModelRegistry(BASIC_PKG)
        assert f"{BASIC_PKG}.models.UserModel" in registry

    def test_contains_returns_false_for_missing(self) -> None:
        registry: ModelRegistry[BaseModel] = ModelRegistry(BASIC_PKG)
        assert "Nonexistent" not in registry

    def test_contains_raises_for_ambiguous(self) -> None:
        registry: ModelRegistry[BaseModel] = ModelRegistry(AMBIGUOUS_PKG)
        with pytest.raises(AmbiguousModelError):
            registry.__contains__("SharedName")


class TestFilter:
    def test_filter_returns_subset(self) -> None:
        registry: ModelRegistry[BaseModel] = ModelRegistry(BASIC_PKG)
        filtered = registry.filter(lambda model: model.__name__.startswith("User"))
        assert len(filtered) == 1
        assert "UserModel" in filtered

    def test_filter_preserves_base(self) -> None:
        base_prompt = _get_class(WITH_BASE_PKG, "models", "BasePrompt")
        registry = ModelRegistry(WITH_BASE_PKG, base=base_prompt)
        filtered = registry.filter(lambda model: model.__name__.startswith("System"))
        assert filtered.base is base_prompt

    def test_filter_to_empty(self) -> None:
        registry: ModelRegistry[BaseModel] = ModelRegistry(BASIC_PKG)
        filtered = registry.filter(lambda _: False)
        assert len(filtered) == 0


class TestProperties:
    def test_models_property(self) -> None:
        registry: ModelRegistry[BaseModel] = ModelRegistry(BASIC_PKG)
        assert isinstance(registry.models, frozenset)
        assert len(registry.models) == 3

    def test_base_property(self) -> None:
        base_prompt = _get_class(WITH_BASE_PKG, "models", "BasePrompt")
        registry = ModelRegistry(WITH_BASE_PKG, base=base_prompt)
        assert registry.base is base_prompt

    def test_base_defaults_to_base_model(self) -> None:
        registry: ModelRegistry[BaseModel] = ModelRegistry(BASIC_PKG)
        assert registry.base is BaseModel

    def test_modules_property(self) -> None:
        registry: ModelRegistry[BaseModel] = ModelRegistry(BASIC_PKG)
        assert registry.modules == (BASIC_PKG,)


def _get_class(package: str, module_name: str, class_name: str) -> type[BaseModel]:
    module = importlib.import_module(f"{package}.{module_name}")
    cls = getattr(module, class_name)
    assert issubclass(cls, BaseModel)
    return cls  # type: ignore[no-any-return]
