import datetime as dt
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator
from .models import Category

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    created_at: dt.datetime

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class ExpenseCreate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    title: str = Field(min_length=1, max_length=100)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    category: Category
    date: dt.date
    description: str | None = Field(default=None, max_length=500)

class ExpenseUpdate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    title: str | None = Field(default=None, min_length=1, max_length=100)
    amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    category: Category | None = None
    date: dt.date | None = None
    description: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def required_fields_not_null(self):
        # description may be set to null (to clear it); the others may be omitted but not nulled
        for name in ("title", "amount", "category", "date"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self

class ExpenseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    amount: Decimal
    category: Category
    date: dt.date
    description: str | None
    created_at: dt.datetime
    updated_at: dt.datetime