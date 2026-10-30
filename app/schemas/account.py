from pydantic import BaseModel,EmailStr,Field
from typing import Literal

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(
        min_length=12,
        max_length=128,
    )

class AccountResponse(BaseModel):
    customer_id: str
    email: EmailStr
    is_active: bool

    model_config = {
        "from_attributes": True
    }

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    customer_id: str