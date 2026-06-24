from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel

class Transaction(BaseModel):
    id: Optional[int] = None        # stored-row id; None for a fresh /analyze
    date: date
    description: str                # raw text from the PDF row
    merchant: str                   # cleaned merchant name used for categorization
    amount: float                   # positive for income, negative for expenses
    category: Optional[str] = None
    reimbursed: float = 0.0         # confirmed offset applied to this spend (>=0)

class CategorySummary(BaseModel):
    category: str
    total: float
    count: int

class MerchantSummary(BaseModel):
    merchant: str
    total: float
    count: int

class AnalysisResult(BaseModel):
    id: Optional[int] = None             # stored statement id (None for raw /analyze)
    bank: str
    period_start: date
    period_end: date
    total_spend: float                   # excludes transfers and income
    transactions: list[Transaction]
    by_category: list[CategorySummary]
    top_merchants: list[MerchantSummary]


class Correction(BaseModel):
    merchant: str
    category: str


class StatementSummary(BaseModel):
    id: int
    bank: str
    period_start: date
    period_end: date
    uploaded_at: datetime
    transaction_count: int
    total_spend: float


class ReimbursementSuggestion(BaseModel):
    transfer: Transaction
    candidates: list[Transaction]


class OffsetRequest(BaseModel):
    transfer_tx_id: int
    spend_tx_id: int
    amount: float


class OffsetResponse(BaseModel):
    id: int
    transfer_tx_id: int
    spend_tx_id: int
    amount: float