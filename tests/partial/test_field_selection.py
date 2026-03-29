from __future__ import annotations

import pytest
from pydantic import BaseModel

from pydantic_plus_plus.partial._field_selection import FieldSelection


class Address(BaseModel):
    street: str
    city: str
    state: str
    zip_code: str


class User(BaseModel):
    name: str
    age: int
    email: str
    address: Address


class Company(BaseModel):
    name: str
    headquarters: Address
    ceo: User


class TestFieldSelectionParsing:
    def test_parse_single_terminal(self) -> None:
        selection = FieldSelection.parse("name")
        assert selection.should_make_optional("name") is True
        assert selection.should_make_optional("age") is False

    def test_parse_multiple_terminals(self) -> None:
        selection = FieldSelection.parse("name", "email")
        assert selection.should_make_optional("name") is True
        assert selection.should_make_optional("email") is True
        assert selection.should_make_optional("age") is False

    def test_parse_dot_notation(self) -> None:
        selection = FieldSelection.parse("address.city")
        assert selection.should_make_optional("address") is False
        assert selection.has_nested_selection("address") is True
        nested = selection.nested_selection_for("address")
        assert nested is not None
        assert nested.should_make_optional("city") is True
        assert nested.should_make_optional("street") is False

    def test_parse_wildcard(self) -> None:
        selection = FieldSelection.parse("address.*")
        assert selection.should_make_optional("address") is False
        assert selection.has_nested_selection("address") is True
        nested = selection.nested_selection_for("address")
        assert nested is not None
        assert nested.is_wildcard is True
        assert nested.should_make_optional("city") is True
        assert nested.should_make_optional("street") is True

    def test_parse_combined_terminal_and_dot(self) -> None:
        selection = FieldSelection.parse("name", "address.city")
        assert selection.should_make_optional("name") is True
        assert selection.should_make_optional("address") is False
        assert selection.has_nested_selection("address") is True
        nested = selection.nested_selection_for("address")
        assert nested is not None
        assert nested.should_make_optional("city") is True

    def test_parse_terminal_and_nested_same_field(self) -> None:
        selection = FieldSelection.parse("address", "address.city")
        assert selection.should_make_optional("address") is True
        assert selection.has_nested_selection("address") is True
        nested = selection.nested_selection_for("address")
        assert nested is not None
        assert nested.should_make_optional("city") is True

    def test_parse_deep_nesting(self) -> None:
        selection = FieldSelection.parse("ceo.address.city")
        assert selection.has_nested_selection("ceo") is True
        ceo_sel = selection.nested_selection_for("ceo")
        assert ceo_sel is not None
        assert ceo_sel.has_nested_selection("address") is True
        addr_sel = ceo_sel.nested_selection_for("address")
        assert addr_sel is not None
        assert addr_sel.should_make_optional("city") is True

    def test_parse_no_specs_returns_is_wildcard(self) -> None:
        selection = FieldSelection.parse()
        assert selection.should_make_optional("name") is False
        assert selection.is_wildcard is False

    def test_nested_selection_for_nonexistent_returns_none(self) -> None:
        selection = FieldSelection.parse("name")
        assert selection.nested_selection_for("address") is None

    def test_parse_terminal_subsumes_wildcard(self) -> None:
        selection = FieldSelection.parse("address", "address.*")
        assert selection.should_make_optional("address") is True
        nested = selection.nested_selection_for("address")
        assert nested is not None
        assert nested.is_wildcard is True


class TestFieldSelectionValidation:
    def test_valid_single_field(self) -> None:
        selection = FieldSelection.parse("name")
        selection.validate(User)  # should not raise

    def test_nonexistent_field_raises(self) -> None:
        selection = FieldSelection.parse("nonexistent")
        with pytest.raises(ValueError, match="does not exist on model 'User'"):
            selection.validate(User)

    def test_dot_notation_on_non_model_raises(self) -> None:
        selection = FieldSelection.parse("name.foo")
        with pytest.raises(ValueError, match="is not a BaseModel subclass"):
            selection.validate(User)

    def test_valid_dot_notation(self) -> None:
        selection = FieldSelection.parse("address.city")
        selection.validate(User)  # should not raise

    def test_nonexistent_nested_field_raises(self) -> None:
        selection = FieldSelection.parse("address.nonexistent")
        with pytest.raises(ValueError, match="does not exist on model 'Address'"):
            selection.validate(User)

    def test_valid_wildcard(self) -> None:
        selection = FieldSelection.parse("address.*")
        selection.validate(User)  # should not raise

    def test_wildcard_on_non_model_raises(self) -> None:
        selection = FieldSelection.parse("name.*")
        with pytest.raises(ValueError, match="is not a BaseModel subclass"):
            selection.validate(User)

    def test_empty_spec_raises(self) -> None:
        with pytest.raises(ValueError, match="Empty field spec"):
            FieldSelection.parse("")

    def test_deep_nesting_validation(self) -> None:
        selection = FieldSelection.parse("ceo.address.city")
        selection.validate(Company)  # should not raise

    def test_deep_nesting_invalid_leaf(self) -> None:
        selection = FieldSelection.parse("ceo.address.nonexistent")
        with pytest.raises(ValueError, match="does not exist on model 'Address'"):
            selection.validate(Company)
