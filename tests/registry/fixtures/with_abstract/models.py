from abc import ABC, abstractmethod

from pydantic import BaseModel


class AbstractConfig(BaseModel, ABC):
    name: str

    @abstractmethod
    def validate_config(self) -> bool: ...


class ConcreteConfig(AbstractConfig):
    value: int

    def validate_config(self) -> bool:
        return self.value > 0
