from enum import Enum
from pydantic import BaseModel

from pydantic_plus_plus import partial


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
    email: str
    address: Address


PartialUser = partial(User, recursive=True)

if __name__ == "__main__":
    test_user = User(
        name="Alice",
        age=30,
        email="alice@example.com",
        address=Address(
            street="123 Main St",
            city="San Francisco",
            state="CA",
            zip_code="94105",
            country=Country.UNITED_STATES,
        ),
    )
    print(f"Test user:\n{test_user.model_dump_json(indent=4)}")

    update_json = '{"age": 31, "address": {"street": "123 Main St Apt 1"}}'
    print(f"\nUpdate JSON:\n{update_json}")

    patch = PartialUser.model_validate_json(update_json)
    print(f"Patch:\n{patch.model_dump_json(indent=4)}")

    updated_user = patch.apply(test_user)
    print(f"\nUpdated user:\n{updated_user.model_dump_json(indent=4)}")
