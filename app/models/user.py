from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class UserBase(BaseModel):
    email: str
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    pan: Optional[str] = Field(default=None, alias="PAN")

    class Config:
        allow_population_by_field_name = True
        orm_mode = True


class UserCreate(UserBase):
    password: str


class UserUpdate(UserBase):
    pass


class User(UserBase):
    id: str = Field(default_factory=lambda: f"usr_{uuid4().hex}")
    roles: List[str] = Field(default_factory=lambda: ["client"])
    created_at: datetime = Field(default_factory=datetime.utcnow)
    approved: bool = False
    password_hash: Optional[str] = None


class UserPublic(UserBase):
    id: str
    roles: List[str]
    created_at: datetime
    approved: bool
