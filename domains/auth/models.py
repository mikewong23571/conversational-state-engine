from datetime import datetime

from pydantic import BaseModel


class User(BaseModel):
    """Application user."""

    user_id: str
    email: str
    role: str
    permissions: list[str]
    is_active: bool = True
    created_at: datetime | None = None


class UserLogin(BaseModel):
    email: str
    password: str


class UserCreate(BaseModel):
    email: str
    password: str
    role: str = "user"


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
