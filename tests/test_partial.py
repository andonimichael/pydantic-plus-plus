from __future__ import annotations
from enum import Enum
from typing import Annotated, Optional, get_args
import pytest
from pydantic import BaseModel, Field, ValidationError, field_validator
from pydantic_plus_plus.partial import PartialBaseModel, partial, _partial_model_cache


class Country(str, Enum):
    CANADA = "Canada"
    MEXICO = "Mexico"
    UNITED_STATES = "United States"
    OTHER = "Other"


class Address(BaseModel):
    street: str
    city: str
    state: str
    zip_code: str
    country: Country = Country.UNITED_STATES


class User(BaseModel):
    name: str
    age: int
    email: str = "user@example.com"
    address: Address


class Admin(User):
    role: str
    permissions: list[str]


class Config(BaseModel):
    name: Annotated[str, Field(min_length=1, description="Config name")]
    value: int = Field(ge=0, description="Config value")
    tags: list[str] = Field(default_factory=list)


class WithOptional(BaseModel):
    required_field: str
    optional_field: Optional[str] = None


class UserWithFriends(BaseModel):
    name: str
    friends: list[User]


class Registry(BaseModel):
    name: str
    entries: dict[str, User]


class Tree(BaseModel):
    value: str
    children: list[Tree] = []


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    _partial_model_cache.clear()


class TestPartialConstruction:
    def test_partial_function(self) -> None:
        PartialUser = partial(User, recursive=True)
        assert issubclass(PartialUser, BaseModel)
        assert issubclass(PartialUser, PartialBaseModel)
        assert not issubclass(PartialUser, User)  # type: ignore[unreachable]

    def test_from_model_classmethod(self) -> None:
        PartialUser = PartialBaseModel.from_model(User, recursive=True)
        assert issubclass(PartialUser, BaseModel)
        assert issubclass(PartialUser, PartialBaseModel)
        assert not issubclass(PartialUser, User)  # type: ignore[unreachable]

    def test_both_syntaxes_equivalent(self) -> None:
        P1 = partial(User, recursive=True)
        P2 = PartialBaseModel.from_model(User, recursive=True)
        assert P1 is P2

    def test_returns_class_not_instance(self) -> None:
        PartialUser = partial(User, recursive=True)
        assert isinstance(PartialUser, type)


class TestPartialFields:
    def test_all_fields_optional(self) -> None:
        PartialUser = partial(User, recursive=True)
        for field_name, field_info in PartialUser.model_fields.items():
            assert not field_info.is_required(), f"{field_name} should not be required"

    def test_all_fields_default_none(self) -> None:
        PartialUser = partial(User, recursive=True)
        p = PartialUser()
        for field_name in User.model_fields:
            assert getattr(p, field_name) is None

    def test_instantiate_with_no_args(self) -> None:
        PartialUser = partial(User, recursive=True)
        p = PartialUser()
        assert p.name is None
        assert p.age is None
        assert p.email is None
        assert p.address is None

    def test_instantiate_with_some_args(self) -> None:
        PartialUser = partial(User, recursive=True)
        p = PartialUser(name="Alice")
        assert p.name == "Alice"
        assert p.age is None

    def test_instantiate_with_all_args(self) -> None:
        PartialUser = partial(User, recursive=False)
        address = Address(street="123 1st Ave", city="New York", state="NY", zip_code="10001")
        p = PartialUser(name="Alice", age=30, email="ali@ce.com", address=address)
        assert p.name == "Alice"
        assert p.age == 30
        assert p.email == "ali@ce.com"
        assert p.address == address

    def test_already_optional_stays_optional(self) -> None:
        Partial = partial(WithOptional, recursive=True)
        p = Partial()
        assert p.required_field is None
        assert p.optional_field is None

    def test_field_with_existing_default_becomes_none(self) -> None:
        PartialUser = partial(User, recursive=True)
        p = PartialUser()
        # email had a default of "user@example.com" but partial should default to None
        assert p.email is None


class TestPartialAnnotations:
    def test_annotations_are_optional(self) -> None:
        PartialUser = partial(User, recursive=True)
        ann = PartialUser.model_fields["name"].annotation
        # Should be str | None
        assert ann == str | None

    def test_nested_model_annotation_shallow(self) -> None:
        PartialUser = partial(User, recursive=False)
        ann = PartialUser.model_fields["address"].annotation
        assert ann == Address | None

    def test_nested_model_annotation_recursive(self) -> None:
        PartialUser = partial(User, recursive=True)
        ann = PartialUser.model_fields["address"].annotation
        # Inner model is partialized, so it's PartialAddress | None
        assert ann != Address | None
        assert type(None) in get_args(ann)

    def test_list_annotation_optional(self) -> None:
        PartialAdmin = partial(Admin, recursive=True)
        ann = PartialAdmin.model_fields["permissions"].annotation
        assert ann == list[str] | None


class TestPartialTypeRelationship:
    def test_is_standalone(self) -> None:
        PartialUser = partial(User, recursive=True)
        p = PartialUser(name="Alice")
        assert not isinstance(p, User)  # type: ignore[unreachable]
        assert isinstance(p, BaseModel)
        assert isinstance(p, PartialUser)

    def test_not_subclass_of_original(self) -> None:
        PartialUser = partial(User, recursive=True)
        assert not issubclass(PartialUser, User)  # type: ignore[unreachable]
        assert issubclass(PartialUser, BaseModel)

    def test_mro_excludes_original(self) -> None:
        PartialUser = partial(User, recursive=True)
        assert User not in PartialUser.__mro__


class TestPartialSubclass:
    def test_partial_subclass_includes_parent_fields(self) -> None:
        PartialAdmin = partial(Admin, recursive=True)
        p = PartialAdmin()
        assert p.name is None  # from User
        assert p.role is None  # from Admin
        assert p.permissions is None

    def test_partial_subclass_all_optional(self) -> None:
        PartialAdmin = partial(Admin, recursive=True)
        for field_name, field_info in PartialAdmin.model_fields.items():
            assert not field_info.is_required(), f"{field_name} should not be required"

    def test_partial_subclass_isinstance(self) -> None:
        PartialAdmin = partial(Admin, recursive=True)
        p = PartialAdmin(role="admin")
        assert not isinstance(p, Admin)  # type: ignore[unreachable]
        assert not isinstance(p, User)  # type: ignore[unreachable]
        assert isinstance(p, BaseModel)


class TestPartialNestedShallow:
    def test_nested_model_is_none_by_default(self) -> None:
        PartialUser = partial(User, recursive=False)
        p = PartialUser()
        assert p.address is None

    def test_nested_model_requires_complete_when_provided(self) -> None:
        PartialUser = partial(User, recursive=False)
        addr = Address(street="123 1st Ave", city="New York", state="NY", zip_code="10001")
        p = PartialUser(address=addr)
        assert p.address is not None
        assert p.address.city == "New York"

    def test_nested_model_rejects_incomplete(self) -> None:
        PartialUser = partial(User, recursive=False)
        with pytest.raises(ValidationError):
            PartialUser(address={"city": "New York"})  # type: ignore[arg-type]  # missing street, zip_code


class TestPartialNestedRecursive:
    def test_recursive_nested_model_optional(self) -> None:
        PartialUser = partial(User, recursive=True)
        p = PartialUser(address={"city": "New York"})  # type: ignore[arg-type]
        assert p.address is not None
        assert p.address.city == "New York"
        assert p.address.street is None

    def test_recursive_list_of_models(self) -> None:
        Partial = partial(UserWithFriends, recursive=True)
        p = Partial(friends=[{"name": "Alice"}])  # type: ignore[list-item]
        assert p.friends is not None
        assert p.friends[0].name == "Alice"
        assert p.friends[0].age is None

    def test_recursive_dict_of_models(self) -> None:
        Partial = partial(Registry, recursive=True)
        p = Partial(entries={"alice": {"name": "Alice"}})  # type: ignore[dict-item]
        assert p.entries is not None
        assert p.entries["alice"].name == "Alice"
        assert p.entries["alice"].age is None

    def test_recursive_self_referencing(self) -> None:
        Partial = partial(Tree, recursive=True)
        p = Partial(value="root", children=[{"value": "child"}])  # type: ignore[list-item]
        assert p.children is not None
        assert p.children[0].value == "child"


class TestPartialModelDump:
    def test_dump_all_none(self) -> None:
        PartialUser = partial(User, recursive=True)
        p = PartialUser()
        d = p.model_dump()
        assert d == {"name": None, "age": None, "email": None, "address": None}

    def test_dump_exclude_none(self) -> None:
        PartialUser = partial(User, recursive=True)
        p = PartialUser(name="Alice")
        d = p.model_dump(exclude_none=True)
        assert d == {"name": "Alice"}

    def test_dump_exclude_unset(self) -> None:
        PartialUser = partial(User, recursive=True)
        p = PartialUser(name="Alice")
        d = p.model_dump(exclude_unset=True)
        assert d == {"name": "Alice"}

    def test_dump_with_nested(self) -> None:
        PartialUser = partial(User, recursive=False)
        addr = Address(street="123 1st Ave", city="New York", state="NY", zip_code="10001")
        p = PartialUser(name="Alice", address=addr)
        d = p.model_dump(exclude_none=True)
        assert d == {
            "name": "Alice",
            "address": {
                "street": "123 1st Ave",
                "city": "New York",
                "state": "NY",
                "zip_code": "10001",
                "country": "United States",
            },
        }


class TestPartialModelValidate:
    def test_validate_empty_dict(self) -> None:
        PartialUser = partial(User, recursive=True)
        p = PartialUser.model_validate({})
        assert p.name is None

    def test_validate_partial_dict(self) -> None:
        PartialUser = partial(User, recursive=True)
        p = PartialUser.model_validate({"name": "Alice", "age": 30})
        assert p.name == "Alice"
        assert p.age == 30
        assert p.address is None

    def test_validate_full_dict(self) -> None:
        PartialUser = partial(User, recursive=True)
        data = {
            "name": "Alice",
            "age": 30,
            "email": "ali@ce.com",
            "address": {
                "street": "123 1st Ave",
                "city": "New York",
                "state": "NY",
                "zip_code": "10001",
                "country": "United States",
            },
        }
        p = PartialUser.model_validate(data)
        assert p.name == "Alice"
        assert p.address is not None
        assert p.address.city == "New York"


class TestPartialJsonRoundTrip:
    def test_json_round_trip(self) -> None:
        PartialUser = partial(User, recursive=True)
        p = PartialUser(name="Alice", age=30)
        json_str = p.model_dump_json()
        restored = PartialUser.model_validate_json(json_str)
        assert restored.name == "Alice"
        assert restored.age == 30
        assert restored.address is None

    def test_json_schema(self) -> None:
        PartialUser = partial(User, recursive=True)
        schema = PartialUser.model_json_schema()
        assert schema["title"] == "PartialUser"
        # All properties should allow null
        for prop_name, prop_schema in schema["properties"].items():
            assert "default" in prop_schema, f"{prop_name} should have a default"


class TestPartialToOriginalRoundTrip:
    def test_partial_to_original_via_dump(self) -> None:
        PartialUser = partial(User, recursive=False)
        addr = Address(street="123 1st Ave", city="New York", state="NY", zip_code="10001")
        p = PartialUser(name="Alice", age=30, email="ali@ce.com", address=addr)
        data = p.model_dump()
        user = User.model_validate(data)
        assert user.name == "Alice"
        assert user.address.city == "New York"

    def test_original_to_partial_via_dump(self) -> None:
        user = User(
            name="Alice",
            age=30,
            address=Address(street="123 1st Ave", city="New York", state="NY", zip_code="10001"),
        )
        PartialUser = partial(User, recursive=True)
        data = user.model_dump()
        p = PartialUser.model_validate(data)
        assert p.name == "Alice"
        assert not isinstance(p, User)  # type: ignore[unreachable]


class TestPartialFieldMetadata:
    def test_description_preserved(self) -> None:
        PartialConfig = partial(Config, recursive=True)
        fi = PartialConfig.model_fields["name"]
        assert fi.description == "Config name"

    def test_constraints_preserved_on_non_none(self) -> None:
        PartialConfig = partial(Config, recursive=True)
        with pytest.raises(ValidationError):
            PartialConfig(name="")  # min_length=1 violated

    def test_constraints_allow_none(self) -> None:
        PartialConfig = partial(Config, recursive=True)
        p = PartialConfig(name=None)
        assert p.name is None

    def test_ge_constraint_preserved(self) -> None:
        PartialConfig = partial(Config, recursive=True)
        with pytest.raises(ValidationError):
            PartialConfig(value=-1)  # ge=0 violated

    def test_ge_constraint_allows_none(self) -> None:
        PartialConfig = partial(Config, recursive=True)
        p = PartialConfig(value=None)
        assert p.value is None


class ModelWithValidator(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def name_must_be_capitalized(cls, v: str) -> str:
        if v is not None and v != v.capitalize():
            raise ValueError("name must be capitalized")
        return v


class TestPartialValidators:
    def test_standalone_does_not_inherit_field_validators(self) -> None:
        Partial = partial(ModelWithValidator, recursive=True)
        # @field_validator is NOT inherited — standalone class
        p = Partial(name="alice")
        assert p.name == "alice"

    def test_accepts_none(self) -> None:
        Partial = partial(ModelWithValidator, recursive=True)
        p = Partial(name=None)
        assert p.name is None


class TestPartialCaching:
    def test_same_model_same_result(self) -> None:
        P1 = partial(User, recursive=True)
        P2 = partial(User, recursive=True)
        assert P1 is P2

    def test_different_models_different_result(self) -> None:
        PU = partial(User, recursive=True)
        PA = partial(Admin, recursive=True)
        assert PU is not PA

    def test_recursive_vs_shallow_different(self) -> None:
        P1 = partial(User, recursive=False)
        P2 = partial(User, recursive=True)
        assert P1 is not P2


class TestPartialModelCopy:
    def test_model_copy_update(self) -> None:
        PartialUser = partial(User, recursive=True)
        p = PartialUser(name="Alice")
        p2 = p.model_copy(update={"age": 30})
        assert p2.name == "Alice"
        assert p2.age == 30
        assert p.age is None  # original unchanged


class TestPartialApply:
    def test_apply_flat_fields(self) -> None:
        PartialUser = partial(User, recursive=True)
        user = User(
            name="Alice",
            age=30,
            email="ali@ce.com",
            address=Address(street="123 1st Ave", city="New York", state="NY", zip_code="10001"),
        )
        patch = PartialUser(age=31)
        updated = patch.apply(user)
        assert isinstance(updated, User)
        assert updated.age == 31
        assert updated.name == "Alice"  # unchanged

    def test_apply_preserves_original(self) -> None:
        PartialUser = partial(User, recursive=True)
        user = User(
            name="Alice",
            age=30,
            email="ali@ce.com",
            address=Address(street="123 1st Ave", city="New York", state="NY", zip_code="10001"),
        )
        patch = PartialUser(age=31)
        patch.apply(user)
        assert user.age == 30  # original untouched

    def test_apply_nested_deep_merge(self) -> None:
        PartialUser = partial(User, recursive=True)
        user = User(
            name="Alice",
            age=30,
            email="ali@ce.com",
            address=Address(street="123 1st Ave", city="New York", state="NY", zip_code="10001"),
        )
        patch = PartialUser(address={"city": "New York City"})  # type: ignore[arg-type]
        updated = patch.apply(user)
        assert updated.address.city == "New York City"
        assert updated.address.street == "123 1st Ave"  # preserved
        assert updated.address.zip_code == "10001"  # preserved

    def test_apply_noop(self) -> None:
        PartialUser = partial(User, recursive=True)
        user = User(
            name="Alice",
            age=30,
            email="ali@ce.com",
            address=Address(street="123 1st Ave", city="New York", state="NY", zip_code="10001"),
        )
        patch = PartialUser()
        updated = patch.apply(user)
        assert updated == user

    def test_apply_returns_original_model_type(self) -> None:
        PartialAdmin = partial(Admin, recursive=True)
        admin = Admin(
            name="Admin",
            age=40,
            email="admin@example.com",
            address=Address(street="123 Main St", city="San Francisco", state="CA", zip_code="94105"),
            role="admin",
            permissions=["read", "write"],
        )
        patch = PartialAdmin(role="read-write")
        updated = patch.apply(admin)
        assert isinstance(updated, Admin)
        assert updated.role == "read-write"
        assert updated.permissions == ["read", "write"]
