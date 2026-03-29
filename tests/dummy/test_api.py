from __future__ import annotations

import datetime
import uuid
from decimal import Decimal
from enum import Enum
from typing import Literal, Optional

import pytest
from pydantic import BaseModel, Field

from pydantic_plus_plus import InvalidFieldError, UnsupportedTypeError, dummy


class Color(str, Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


class Address(BaseModel):
    street: str
    city: str
    state: str
    zip_code: str


class User(BaseModel):
    name: str
    age: int
    email: str = "user@example.com"
    address: Address


class PrimitiveModel(BaseModel):
    string_field: str
    int_field: int
    float_field: float
    bool_field: bool
    bytes_field: bytes


class DatetimeModel(BaseModel):
    datetime_field: datetime.datetime
    date_field: datetime.date
    time_field: datetime.time


class SpecialTypesModel(BaseModel):
    uuid_field: uuid.UUID
    decimal_field: Decimal
    enum_field: Color
    literal_field: Literal["a", "b", "c"]


class CollectionModel(BaseModel):
    list_field: list[int]
    dict_field: dict[str, int]
    set_field: set[str]
    frozenset_field: frozenset[str]
    tuple_field: tuple[int, str]
    var_tuple_field: tuple[int, ...]


class NestedModel(BaseModel):
    user: User
    tags: list[str]


class Tree(BaseModel):
    value: str
    children: list[Tree] = []


class ConstrainedModel(BaseModel):
    short_string: str = Field(min_length=2, max_length=5)
    bounded_int: int = Field(ge=10, le=100)
    bounded_float: float = Field(gt=0.0, lt=10.0)
    strict_int: int = Field(gt=0, lt=5)


class OptionalFieldsModel(BaseModel):
    required_field: str
    optional_field: Optional[str] = None
    optional_int: Optional[int] = None


class UnionModel(BaseModel):
    value: int | str


class WithDefaults(BaseModel):
    name: str
    color: Color = Color.RED
    tags: list[str] = Field(default_factory=list)


class TestDummyPrimitives:
    def test_generates_string(self) -> None:
        instance = dummy(PrimitiveModel, seed=1)
        assert isinstance(instance.string_field, str)
        assert len(instance.string_field) > 0

    def test_generates_int(self) -> None:
        instance = dummy(PrimitiveModel, seed=1)
        assert isinstance(instance.int_field, int)

    def test_generates_float(self) -> None:
        instance = dummy(PrimitiveModel, seed=1)
        assert isinstance(instance.float_field, float)

    def test_generates_bool(self) -> None:
        instance = dummy(PrimitiveModel, seed=1)
        assert isinstance(instance.bool_field, bool)

    def test_generates_bytes(self) -> None:
        instance = dummy(PrimitiveModel, seed=1)
        assert isinstance(instance.bytes_field, bytes)
        assert len(instance.bytes_field) > 0


class TestDummyDatetime:
    def test_generates_datetime(self) -> None:
        instance = dummy(DatetimeModel, seed=1)
        assert isinstance(instance.datetime_field, datetime.datetime)

    def test_generates_date(self) -> None:
        instance = dummy(DatetimeModel, seed=1)
        assert isinstance(instance.date_field, datetime.date)

    def test_generates_time(self) -> None:
        instance = dummy(DatetimeModel, seed=1)
        assert isinstance(instance.time_field, datetime.time)


class TestDummySpecialTypes:
    def test_generates_uuid(self) -> None:
        instance = dummy(SpecialTypesModel, seed=1)
        assert isinstance(instance.uuid_field, uuid.UUID)

    def test_generates_decimal(self) -> None:
        instance = dummy(SpecialTypesModel, seed=1)
        assert isinstance(instance.decimal_field, Decimal)

    def test_generates_enum(self) -> None:
        instance = dummy(SpecialTypesModel, seed=1)
        assert isinstance(instance.enum_field, Color)

    def test_generates_literal(self) -> None:
        instance = dummy(SpecialTypesModel, seed=1)
        assert instance.literal_field in ("a", "b", "c")


class TestDummyCollections:
    def test_generates_list(self) -> None:
        instance = dummy(CollectionModel, seed=1)
        assert isinstance(instance.list_field, list)
        assert len(instance.list_field) > 0
        assert all(isinstance(item, int) for item in instance.list_field)

    def test_generates_dict(self) -> None:
        instance = dummy(CollectionModel, seed=1)
        assert isinstance(instance.dict_field, dict)
        assert len(instance.dict_field) > 0

    def test_generates_set(self) -> None:
        instance = dummy(CollectionModel, seed=1)
        assert isinstance(instance.set_field, set)
        assert all(isinstance(item, str) for item in instance.set_field)

    def test_generates_frozenset(self) -> None:
        instance = dummy(CollectionModel, seed=1)
        assert isinstance(instance.frozenset_field, frozenset)

    def test_generates_tuple(self) -> None:
        instance = dummy(CollectionModel, seed=1)
        assert isinstance(instance.tuple_field, tuple)
        assert len(instance.tuple_field) == 2

    def test_generates_variable_length_tuple(self) -> None:
        instance = dummy(CollectionModel, seed=1)
        assert isinstance(instance.var_tuple_field, tuple)
        assert len(instance.var_tuple_field) > 0
        assert all(isinstance(item, int) for item in instance.var_tuple_field)


class TestDummyNestedModels:
    def test_generates_nested_model(self) -> None:
        instance = dummy(NestedModel, seed=1)
        assert isinstance(instance.user, User)
        assert isinstance(instance.user.address, Address)
        assert isinstance(instance.user.name, str)

    def test_generates_nested_collections(self) -> None:
        instance = dummy(NestedModel, seed=1)
        assert isinstance(instance.tags, list)
        assert all(isinstance(tag, str) for tag in instance.tags)


class TestDummySelfReferential:
    def test_generates_self_referential_model(self) -> None:
        instance = dummy(Tree, seed=1)
        assert isinstance(instance.value, str)
        assert isinstance(instance.children, list)

    def test_respects_max_depth(self) -> None:
        instance = dummy(Tree, seed=42)
        assert isinstance(instance, Tree)

    def test_circular_required_field_raises(self) -> None:
        class CircularNode(BaseModel):
            child: Optional[CircularNode] = None

        instance = dummy(CircularNode, seed=1)
        assert isinstance(instance, CircularNode)


class TestDummyCircularReferences:
    def test_detects_circular_reference_in_optional_field(self) -> None:
        class Node(BaseModel):
            value: str
            next_node: Optional[Node] = None

        instance = dummy(Node, seed=1)
        assert isinstance(instance, Node)
        assert isinstance(instance.value, str)

    def test_detects_circular_reference_in_list_field(self) -> None:
        class Category(BaseModel):
            name: str
            subcategories: list[Category] = []

        instance = dummy(Category, seed=1)
        assert isinstance(instance, Category)
        assert isinstance(instance.subcategories, list)

    def test_raises_for_required_circular_reference(self) -> None:
        class Impossible(BaseModel):
            name: str
            cycle: Impossible  # type: ignore[misc]

        with pytest.raises(UnsupportedTypeError, match="circular reference"):
            dummy(Impossible, seed=1)


class TestDummyConstraints:
    def test_respects_min_max_length(self) -> None:
        for seed in range(10):
            instance = dummy(ConstrainedModel, seed=seed)
            assert 2 <= len(instance.short_string) <= 5

    def test_respects_ge_le(self) -> None:
        for seed in range(10):
            instance = dummy(ConstrainedModel, seed=seed)
            assert 10 <= instance.bounded_int <= 100

    def test_respects_gt_lt_float(self) -> None:
        for seed in range(10):
            instance = dummy(ConstrainedModel, seed=seed)
            assert 0.0 < instance.bounded_float < 10.0

    def test_respects_gt_lt_int(self) -> None:
        for seed in range(10):
            instance = dummy(ConstrainedModel, seed=seed)
            assert 0 < instance.strict_int < 5

    def test_respects_list_min_length(self) -> None:
        class Model(BaseModel):
            items: list[int] = Field(min_length=5)

        for seed in range(10):
            instance = dummy(Model, seed=seed)
            assert len(instance.items) >= 5

    def test_respects_list_max_length(self) -> None:
        class Model(BaseModel):
            items: list[int] = Field(max_length=2)

        for seed in range(10):
            instance = dummy(Model, seed=seed)
            assert len(instance.items) <= 2

    def test_respects_set_min_length(self) -> None:
        class Model(BaseModel):
            items: set[int] = Field(min_length=4)

        for seed in range(10):
            instance = dummy(Model, seed=seed)
            assert len(instance.items) >= 4

    def test_respects_dict_min_length(self) -> None:
        class Model(BaseModel):
            items: dict[str, int] = Field(min_length=4)

        for seed in range(10):
            instance = dummy(Model, seed=seed)
            assert len(instance.items) >= 4

    def test_respects_variable_tuple_min_length(self) -> None:
        class Model(BaseModel):
            items: tuple[int, ...] = Field(min_length=5)

        for seed in range(10):
            instance = dummy(Model, seed=seed)
            assert len(instance.items) >= 5


class TestDummySetDefaults:
    def test_set_defaults_bool_true(self) -> None:
        instance = dummy(WithDefaults, seed=1, set_defaults=True)
        assert instance.color == Color.RED
        assert instance.tags == []

    def test_set_defaults_specific_fields(self) -> None:
        instance = dummy(WithDefaults, seed=1, set_defaults={"color"})
        assert instance.color == Color.RED
        assert isinstance(instance.tags, list)
        assert len(instance.tags) > 0

    def test_set_defaults_invalid_field_raises(self) -> None:
        with pytest.raises(InvalidFieldError, match="does not exist"):
            dummy(WithDefaults, seed=1, set_defaults={"nonexistent"})

    def test_set_defaults_field_without_default_raises(self) -> None:
        with pytest.raises(InvalidFieldError, match="has no default"):
            dummy(WithDefaults, seed=1, set_defaults={"name"})

    def test_set_defaults_bool_propagates_to_nested(self) -> None:
        class Inner(BaseModel):
            value: str
            tag: str = "default_tag"

        class Outer(BaseModel):
            inner: Inner

        instance = dummy(Outer, seed=1, set_defaults=True)
        assert instance.inner.tag == "default_tag"

    def test_set_defaults_set_does_not_propagate_to_nested(self) -> None:
        class Inner(BaseModel):
            value: str
            tag: str = "default_tag"

        class Outer(BaseModel):
            inner: Inner
            color: Color = Color.RED

        instance = dummy(Outer, seed=1, set_defaults={"color"})
        assert instance.color == Color.RED
        assert isinstance(instance.inner.tag, str)


class TestDummySetNones:
    def test_set_nones_bool_true(self) -> None:
        instance = dummy(OptionalFieldsModel, seed=1, set_nones=True)
        assert isinstance(instance.required_field, str)
        assert instance.optional_field is None
        assert instance.optional_int is None

    def test_set_nones_specific_fields(self) -> None:
        instance = dummy(OptionalFieldsModel, seed=1, set_nones={"optional_field"})
        assert instance.optional_field is None
        assert isinstance(instance.required_field, str)

    def test_set_nones_invalid_field_raises(self) -> None:
        with pytest.raises(InvalidFieldError, match="does not exist"):
            dummy(OptionalFieldsModel, seed=1, set_nones={"nonexistent"})

    def test_set_nones_non_optional_field_raises(self) -> None:
        with pytest.raises(InvalidFieldError, match="is not Optional"):
            dummy(OptionalFieldsModel, seed=1, set_nones={"required_field"})

    def test_set_nones_bool_propagates_to_nested(self) -> None:
        class Inner(BaseModel):
            value: str
            optional_value: Optional[str] = None

        class Outer(BaseModel):
            inner: Inner

        instance = dummy(Outer, seed=1, set_nones=True)
        assert instance.inner.optional_value is None

    def test_set_nones_set_does_not_propagate_to_nested(self) -> None:
        class Inner(BaseModel):
            value: str
            optional_value: Optional[str] = None

        class Outer(BaseModel):
            inner: Inner
            optional_field: Optional[str] = None

        instance = dummy(Outer, seed=1, set_nones={"optional_field"})
        assert instance.optional_field is None


class TestDummySetNonesAndDefaults:
    def test_set_nones_wins_over_defaults(self) -> None:
        class Model(BaseModel):
            value: Optional[str] = "hello"

        instance = dummy(Model, seed=1, set_nones={"value"}, set_defaults={"value"})
        assert instance.value is None


class TestDummySeed:
    def test_same_seed_same_result(self) -> None:
        first = dummy(User, seed=42)
        second = dummy(User, seed=42)
        assert first.model_dump() == second.model_dump()

    def test_different_seed_different_result(self) -> None:
        first = dummy(User, seed=1)
        second = dummy(User, seed=2)
        assert first.model_dump() != second.model_dump()


class TestDummyOptionalFields:
    def test_optional_fields_get_non_none_by_default(self) -> None:
        instance = dummy(OptionalFieldsModel, seed=1)
        assert isinstance(instance.required_field, str)


class TestDummyUnion:
    def test_generates_union_type(self) -> None:
        instance = dummy(UnionModel, seed=1)
        assert isinstance(instance.value, (int, str))


class TestDummyUnsupportedType:
    def test_raises_for_unsupported_type(self) -> None:
        class CustomType:
            pass

        class ModelWithCustom(BaseModel):
            model_config = {"arbitrary_types_allowed": True}

            value: CustomType

        with pytest.raises(UnsupportedTypeError, match="Cannot generate"):
            dummy(ModelWithCustom, seed=1)


class TestDummyValidation:
    def test_generated_instance_passes_validation(self) -> None:
        instance = dummy(User, seed=1)
        validated = User.model_validate(instance.model_dump())
        assert validated.model_dump() == instance.model_dump()

    def test_constrained_instance_passes_validation(self) -> None:
        for seed in range(20):
            instance = dummy(ConstrainedModel, seed=seed)
            ConstrainedModel.model_validate(instance.model_dump())
