from __future__ import annotations

from pydantic import BaseModel


class FieldSelection:
    """Parsed representation of which fields to make optional within a model.

    Each instance represents one nesting level. It tracks which fields at this
    level should become ``Optional`` (terminal selectors), and which have deeper
    nested selections that transform their type into a nested partial.

    Usage::

        selection = FieldSelection.parse("name", "address.city")
        selection.should_make_optional("name")      # True
        selection.should_make_optional("address")   # False
        selection.has_nested_selection("address")    # True
    """

    __slots__ = ("optional_fields", "nested_selections", "is_wildcard", "original_specs")

    def __init__(
        self,
        *,
        optional_fields: frozenset[str],
        nested_selections: dict[str, FieldSelection],
        is_wildcard: bool,
        original_specs: frozenset[str],
    ) -> None:
        self.optional_fields = optional_fields
        self.nested_selections = nested_selections
        self.is_wildcard = is_wildcard
        self.original_specs = original_specs

    @classmethod
    def parse(cls, *field_specs: str) -> FieldSelection:
        """Parse field spec strings into a ``FieldSelection`` tree.

        Each spec is one of:
        - ``"field"`` -- terminal selector, makes the field optional
        - ``"field.subfield"`` -- nested dot-notation selector
        - ``"field.*"`` -- wildcard, makes all subfields optional
        """
        optional_fields: set[str] = set()
        nested_raw: dict[str, list[str]] = {}
        is_wildcard = False

        for spec in field_specs:
            if not spec:
                raise ValueError("Empty field spec is not allowed")

            first_segment, _, remainder = spec.partition(".")

            if not remainder:
                if first_segment == "*":
                    is_wildcard = True
                else:
                    optional_fields.add(first_segment)
            else:
                nested_raw.setdefault(first_segment, []).append(remainder)

        nested_selections = {field_name: cls.parse(*sub_specs) for field_name, sub_specs in nested_raw.items()}

        return cls(
            optional_fields=frozenset(optional_fields),
            nested_selections=nested_selections,
            is_wildcard=is_wildcard,
            original_specs=frozenset(field_specs),
        )

    def should_make_optional(self, field_name: str) -> bool:
        return self.is_wildcard or field_name in self.optional_fields

    def has_nested_selection(self, field_name: str) -> bool:
        return field_name in self.nested_selections

    def nested_selection_for(self, field_name: str) -> FieldSelection | None:
        return self.nested_selections.get(field_name)

    @property
    def is_wildcard_only(self) -> bool:
        return self.is_wildcard and not self.optional_fields and not self.nested_selections

    def validate(self, model: type[BaseModel]) -> None:
        """Validate that all field specs reference valid paths on the model."""

        model_fields = model.model_fields
        available_field_names = ", ".join(sorted(model_fields.keys()))

        for field_name in self.optional_fields:
            if field_name not in model_fields:
                raise ValueError(
                    f"Field '{field_name}' does not exist on model '{model.__name__}'. "
                    f"Available fields: {available_field_names}"
                )

        for field_name, nested_selection in self.nested_selections.items():
            if field_name not in model_fields:
                raise ValueError(
                    f"Field '{field_name}' does not exist on model '{model.__name__}'. "
                    f"Available fields: {available_field_names}"
                )

            field_annotation = model_fields[field_name].annotation
            if not (isinstance(field_annotation, type) and issubclass(field_annotation, BaseModel)):
                raise ValueError(
                    f"Cannot use dot-notation on field '{field_name}' of model "
                    f"'{model.__name__}': '{field_annotation.__name__ if isinstance(field_annotation, type) else field_annotation}' "
                    f"is not a BaseModel subclass"
                )

            if not nested_selection.is_wildcard:
                nested_selection.validate(field_annotation)
            elif nested_selection.optional_fields or nested_selection.nested_selections:
                nested_selection.validate(field_annotation)
