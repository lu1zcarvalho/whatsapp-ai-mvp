from pydantic import BaseModel, Field


class TestChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4096)


class TestChatResponse(BaseModel):
    response: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    session_id: str = Field(default="demo", min_length=1, max_length=100, pattern=r"^[\w-]+$")


class ChatResponse(BaseModel):
    reply: str


class ResetRequest(BaseModel):
    session_id: str = Field(default="demo", min_length=1, max_length=100, pattern=r"^[\w-]+$")


class IncomingTextMessage(BaseModel):
    phone_number: str
    customer_name: str | None = None
    message_id: str
    text: str
