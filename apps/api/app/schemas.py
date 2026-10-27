"""
Pydantic request and response schemas for VeriHire v2
"""

from datetime import datetime
from typing import Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.security import validate_and_normalize_email


class RegisterRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email_address(cls, v: str) -> str:
        return validate_and_normalize_email(v)

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, v: str) -> str:
        if not isinstance(v, str) or len(v) < 8 or len(v) > 128:
            raise ValueError("Password must be between 8 and 128 characters")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email_address(cls, v: str) -> str:
        if not v or not isinstance(v, str):
            raise ValueError("Email is required")
        return v.strip().lower()

    @field_validator("password")
    @classmethod
    def validate_password_not_empty(cls, v: str) -> str:
        if not v or not isinstance(v, str):
            raise ValueError("Password is required")
        return v


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str


class AuthResponse(BaseModel):
    user: Optional[UserResponse] = None
    access_token: str
    token_type: str = "bearer"


class JobCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=30, max_length=20000)

    @field_validator("title")
    @classmethod
    def strip_title(cls, v: str) -> str:
        stripped = v.strip()
        if len(stripped) < 1 or len(stripped) > 200:
            raise ValueError("Title must be between 1 and 200 characters")
        return stripped

    @field_validator("description")
    @classmethod
    def strip_description(cls, v: str) -> str:
        stripped = v.strip()
        if len(stripped) < 30 or len(stripped) > 20000:
            raise ValueError("Description must be between 30 and 20000 characters")
        return stripped


class JobUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None

    @field_validator("title")
    @classmethod
    def validate_title_if_present(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            stripped = v.strip()
            if len(stripped) < 1 or len(stripped) > 200:
                raise ValueError("Title must be between 1 and 200 characters")
            return stripped
        return v

    @field_validator("description")
    @classmethod
    def validate_desc_if_present(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            stripped = v.strip()
            if len(stripped) < 30 or len(stripped) > 20000:
                raise ValueError("Description must be between 30 and 20000 characters")
            return stripped
        return v


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    title: str
    description: str
    status: str
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
