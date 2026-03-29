from pydantic import BaseModel


class UserModel(BaseModel):
    name: str
    age: int


class OrderModel(BaseModel):
    order_id: str
    total: float
