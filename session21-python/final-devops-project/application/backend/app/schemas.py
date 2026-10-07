from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Category = Literal["FOOD", "TRANSPORT", "RENT", "BILLS", "SHOPPING", "HEALTH", "ENTERTAINMENT", "EDUCATION", "OTHER"]
CATEGORIES: tuple[str, ...] = Category.__args__


class ExpenseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    amount: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    category: Category = "OTHER"
    spent_on: date = Field(default_factory=date.today)
    note: str = Field(default="", max_length=500)


class ExpenseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    amount: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    category: Category | None = None
    spent_on: date | None = None
    note: str | None = Field(default=None, max_length=500)


class ExpenseOut(ExpenseCreate):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class CategoryTotal(BaseModel):
    category: str
    total: Decimal
    count: int


class SummaryOut(BaseModel):
    currency: str
    count: int
    total: Decimal
    this_month: Decimal
    top_category: str | None
    by_category: list[CategoryTotal]
