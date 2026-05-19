from datetime import date
from typing import Optional
from pydantic import BaseModel, Field

class Transaction(BaseModel):
    date: date
    description: str                # raw text from the PDF row
    merchant: str                   # cleaned merchant name used for categorization
    amount: float                   # positive for income, negative for expenses
    category: Optional[str] = None

class CategorySummary(BaseModel):
    category: str
    total: float
    count: int

class MerchantSummary(BaseModel):
    merchant: str
    total: float
    count: int

class AnalysisResult(BaseModel):
    bank: str
    period_start: date
    period_end: date
    total_spend: float                   # excludes transfers and income
    transactions: list[Transaction]
    by_category: list[CategorySummary]
    top_merchants: list[MerchantSummary]