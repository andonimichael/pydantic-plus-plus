from pydantic import BaseModel


class BasePrompt(BaseModel):
    text: str


class SystemPrompt(BasePrompt):
    system_instruction: str


class UserPrompt(BasePrompt):
    user_name: str
