from pydantic import BaseModel, Field


class TestChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4096)


class TestChatResponse(BaseModel):
    response: str


class IncomingTextMessage(BaseModel):
    phone_number: str
    customer_name: str | None = None
    message_id: str
    text: str
