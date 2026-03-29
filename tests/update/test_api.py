from __future__ import annotations

from typing import Optional

import pytest
from pydantic import BaseModel

from pydantic_plus_plus.update import (
    FieldNotFoundError,
    InvalidOperationError,
    update,
)


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
    tags: list[str] = []
    scores: set[int] = set()
    frozen_tags: frozenset[str] = frozenset()
    metadata: dict[str, str] = {}
    nickname: Optional[str] = None


class AdminUser(User):
    role: str = "admin"


class TestSet:
    def test_flat_field_update(self) -> None:
        user = User(
            name="Alice",
            age=30,
            address=Address(street="123 1st Ave", city="New York", state="NY", zip_code="10001"),
        )
        result = update(user).set(name="Bob").apply()
        assert result.name == "Bob"
        assert result.age == 30

    def test_multiple_fields(self) -> None:
        user = User(
            name="Alice",
            age=30,
            address=Address(street="123 1st Ave", city="New York", state="NY", zip_code="10001"),
        )
        result = update(user).set(name="Bob", age=31).apply()
        assert result.name == "Bob"
        assert result.age == 31

    def test_nested_model_via_dict(self) -> None:
        user = User(
            name="Alice",
            age=30,
            address=Address(street="123 1st Ave", city="New York", state="NY", zip_code="10001"),
        )
        result = update(user).set(address={"city": "New York City"}).apply()
        assert result.address.city == "New York City"
        assert result.address.street == "123 1st Ave"

    def test_nested_model_via_model_updater(self) -> None:
        user = User(
            name="Alice",
            age=30,
            address=Address(street="123 1st Ave", city="New York", state="NY", zip_code="10001"),
        )
        address_updater = update(user.address).set(city="New York City")
        result = update(user).set(address=address_updater).apply()
        assert result.address.city == "New York City"
        assert result.address.street == "123 1st Ave"

    def test_set_field_to_none(self) -> None:
        user = User(
            name="Alice",
            age=30,
            nickname="Ali",
            address=Address(street="123 1st Ave", city="New York", state="NY", zip_code="10001"),
        )
        result = update(user).set(nickname=None).apply()
        assert result.nickname is None

    def test_invalid_field_raises(self) -> None:
        user = User(
            name="Alice",
            age=30,
            address=Address(street="123 1st Ave", city="New York", state="NY", zip_code="10001"),
        )
        with pytest.raises(FieldNotFoundError):
            update(user).set(nonexistent="value")  # type: ignore[call-arg]


class TestAppend:
    def test_append_to_list(self) -> None:
        user = User(
            name="Alice",
            age=30,
            tags=["a"],
            address=Address(street="123 1st Ave", city="New York", state="NY", zip_code="10001"),
        )
        result = update(user).append(tags="b").apply()
        assert result.tags == ["a", "b"]

    def test_append_to_set(self) -> None:
        user = User(
            name="Alice",
            age=30,
            scores={1, 2},
            address=Address(street="123 1st Ave", city="New York", state="NY", zip_code="10001"),
        )
        result = update(user).append(scores=3).apply()
        assert 3 in result.scores

    def test_append_to_frozenset(self) -> None:
        user = User(
            name="Alice",
            age=30,
            frozen_tags=frozenset({"x"}),
            address=Address(street="123 1st Ave", city="New York", state="NY", zip_code="10001"),
        )
        result = update(user).append(frozen_tags="y").apply()
        assert "y" in result.frozen_tags

    def test_append_to_non_sequence_raises(self) -> None:
        user = User(
            name="Alice", age=30, address=Address(street="123 1st Ave", city="New York", state="NY", zip_code="10001")
        )
        with pytest.raises(InvalidOperationError):
            update(user).append(name="value")  # type: ignore[call-arg]


class TestExtend:
    def test_extend_list(self) -> None:
        user = User(
            name="Alice",
            age=30,
            tags=["a"],
            address=Address(street="123 1st Ave", city="New York", state="NY", zip_code="10001"),
        )
        result = update(user).extend(tags=["b", "c"]).apply()
        assert result.tags == ["a", "b", "c"]

    def test_extend_set(self) -> None:
        user = User(
            name="Alice",
            age=30,
            scores={1},
            address=Address(street="123 1st Ave", city="New York", state="NY", zip_code="10001"),
        )
        result = update(user).extend(scores=[2, 3]).apply()
        assert result.scores == {1, 2, 3}

    def test_extend_frozenset(self) -> None:
        user = User(
            name="Alice",
            age=30,
            frozen_tags=frozenset({"x"}),
            address=Address(street="123 1st Ave", city="New York", state="NY", zip_code="10001"),
        )
        result = update(user).extend(frozen_tags=["y", "z"]).apply()
        assert result.frozen_tags == frozenset({"x", "y", "z"})

    def test_extend_non_sequence_raises(self) -> None:
        user = User(
            name="Alice", age=30, address=Address(street="123 1st Ave", city="New York", state="NY", zip_code="10001")
        )
        with pytest.raises(InvalidOperationError):
            update(user).extend(age=[1, 2])  # type: ignore[call-arg]


class TestRemove:
    def test_remove_from_list(self) -> None:
        user = User(
            name="Alice",
            age=30,
            tags=["a", "b"],
            address=Address(street="123 1st Ave", city="New York", state="NY", zip_code="10001"),
        )
        result = update(user).remove(tags="a").apply()
        assert result.tags == ["b"]

    def test_remove_from_set(self) -> None:
        user = User(
            name="Alice",
            age=30,
            scores={1, 2, 3},
            address=Address(street="123 1st Ave", city="New York", state="NY", zip_code="10001"),
        )
        result = update(user).remove(scores=2).apply()
        assert 2 not in result.scores

    def test_remove_from_frozenset(self) -> None:
        user = User(
            name="Alice",
            age=30,
            frozen_tags=frozenset({"x", "y"}),
            address=Address(street="123 1st Ave", city="New York", state="NY", zip_code="10001"),
        )
        result = update(user).remove(frozen_tags="x").apply()
        assert "x" not in result.frozen_tags

    def test_remove_dict_key(self) -> None:
        user = User(
            name="Alice",
            age=30,
            metadata={"a": "1", "b": "2"},
            address=Address(street="123 1st Ave", city="New York", state="NY", zip_code="10001"),
        )
        result = update(user).remove(metadata="a").apply()
        assert "a" not in result.metadata
        assert result.metadata["b"] == "2"

    def test_remove_non_collection_raises(self) -> None:
        user = User(
            name="Alice", age=30, address=Address(street="123 1st Ave", city="New York", state="NY", zip_code="10001")
        )
        with pytest.raises(InvalidOperationError):
            update(user).remove(name="value")  # type: ignore[call-arg]

    def test_remove_missing_silent(self) -> None:
        user = User(
            name="Alice",
            age=30,
            tags=["a"],
            address=Address(street="123 1st Ave", city="New York", state="NY", zip_code="10001"),
        )
        result = update(user).remove(tags="nonexistent").apply()
        assert result.tags == ["a"]

    def test_remove_missing_raises_when_configured(self) -> None:
        user = User(
            name="Alice",
            age=30,
            tags=["a"],
            address=Address(street="123 1st Ave", city="New York", state="NY", zip_code="10001"),
        )
        with pytest.raises(FieldNotFoundError):
            update(user, raise_on_missing=True).remove(tags="nonexistent").apply()

    def test_remove_missing_dict_key_silent(self) -> None:
        user = User(
            name="Alice",
            age=30,
            metadata={"a": "1"},
            address=Address(street="123 1st Ave", city="New York", state="NY", zip_code="10001"),
        )
        result = update(user).remove(metadata="nonexistent").apply()
        assert result.metadata == {"a": "1"}

    def test_remove_missing_dict_key_raises(self) -> None:
        user = User(
            name="Alice",
            age=30,
            metadata={"a": "1"},
            address=Address(street="123 1st Ave", city="New York", state="NY", zip_code="10001"),
        )
        with pytest.raises(FieldNotFoundError):
            update(user, raise_on_missing=True).remove(metadata="nonexistent").apply()


class TestSetItem:
    def test_merge_into_dict(self) -> None:
        user = User(
            name="Alice",
            age=30,
            metadata={"a": "1"},
            address=Address(street="123 1st Ave", city="New York", state="NY", zip_code="10001"),
        )
        result = update(user).set_item(metadata={"b": "2"}).apply()
        assert result.metadata == {"a": "1", "b": "2"}

    def test_set_item_non_dict_raises(self) -> None:
        user = User(
            name="Alice", age=30, address=Address(street="123 1st Ave", city="New York", state="NY", zip_code="10001")
        )
        with pytest.raises(InvalidOperationError):
            update(user).set_item(tags={"key": "value"})  # type: ignore[call-arg]

    def test_set_item_value_must_be_dict(self) -> None:
        user = User(
            name="Alice", age=30, address=Address(street="123 1st Ave", city="New York", state="NY", zip_code="10001")
        )
        with pytest.raises(InvalidOperationError):
            update(user).set_item(metadata="not a dict")  # type: ignore[arg-type]


class TestSetPath:
    def test_shallow_path(self) -> None:
        user = User(
            name="Alice", age=30, address=Address(street="123 1st Ave", city="New York", state="NY", zip_code="10001")
        )
        result = update(user).set_path("name", "Bob").apply()
        assert result.name == "Bob"

    def test_deep_nested_path(self) -> None:
        user = User(
            name="Alice", age=30, address=Address(street="123 1st Ave", city="New York", state="NY", zip_code="10001")
        )
        result = update(user).set_path("address.city", "New York City").apply()
        assert result.address.city == "New York City"
        assert result.address.street == "123 1st Ave"

    def test_set_path_no_validation_at_call_time(self) -> None:
        user = User(
            name="Alice", age=30, address=Address(street="123 1st Ave", city="New York", state="NY", zip_code="10001")
        )
        updater = update(user).set_path("address.nonexistent", "value")
        result = updater.apply()
        assert result.address.city == "New York"


class TestImmutability:
    def test_set_returns_new_instance(self) -> None:
        user = User(
            name="Alice", age=30, address=Address(street="123 1st Ave", city="New York", state="NY", zip_code="10001")
        )
        original = update(user)
        modified = original.set(name="Bob")
        assert original is not modified

    def test_original_updater_unchanged(self) -> None:
        user = User(
            name="Alice", age=30, address=Address(street="123 1st Ave", city="New York", state="NY", zip_code="10001")
        )
        original = update(user)
        original.set(name="Bob")
        result = original.apply()
        assert result.name == "Alice"

    def test_divergent_chains(self) -> None:
        user = User(
            name="Alice", age=30, address=Address(street="123 1st Ave", city="New York", state="NY", zip_code="10001")
        )
        base = update(user)
        chain_a = base.set(name="Bob")
        chain_b = base.set(name="Charlie")
        assert chain_a.apply().name == "Bob"
        assert chain_b.apply().name == "Charlie"


class TestApply:
    def test_returns_copy_with_no_ops(self) -> None:
        user = User(
            name="Alice", age=30, address=Address(street="123 1st Ave", city="New York", state="NY", zip_code="10001")
        )
        result = update(user).apply()
        assert result is not user
        assert result.name == "Alice"

    def test_preserves_subclass_type(self) -> None:
        admin = AdminUser(
            name="Alice",
            age=30,
            role="superadmin",
            address=Address(street="123 1st Ave", city="New York", state="NY", zip_code="10001"),
        )
        result = update(admin).set(name="Bob").apply()
        assert isinstance(result, AdminUser)
        assert result.role == "superadmin"

    def test_operation_ordering(self) -> None:
        user = User(
            name="Alice",
            age=30,
            tags=["a"],
            address=Address(street="123 1st Ave", city="New York", state="NY", zip_code="10001"),
        )
        result = update(user).set(tags=["x"]).append(tags="y").apply()
        assert result.tags == ["x", "y"]

    def test_set_then_append(self) -> None:
        user = User(
            name="Alice",
            age=30,
            tags=[],
            address=Address(street="123 1st Ave", city="New York", state="NY", zip_code="10001"),
        )
        result = update(user).append(tags="a").append(tags="b").apply()
        assert result.tags == ["a", "b"]


class TestRaiseOnMissing:
    def test_propagated_through_chain(self) -> None:
        user = User(
            name="Alice",
            age=30,
            tags=["a"],
            address=Address(street="123 1st Ave", city="New York", state="NY", zip_code="10001"),
        )
        updater = update(user, raise_on_missing=True).set(name="Bob")
        chained = updater.remove(tags="nonexistent")
        with pytest.raises(FieldNotFoundError):
            chained.apply()
