from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.engine import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Statement(Base):
    __tablename__ = "statements"

    id: Mapped[int] = mapped_column(primary_key=True)
    bank: Mapped[str] = mapped_column(String)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    # sha256 of the raw PDF bytes — re-uploading the same file dedupes on this.
    content_hash: Mapped[str] = mapped_column(String, unique=True, index=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    transactions: Mapped[list["StoredTransaction"]] = relationship(
        back_populates="statement", cascade="all, delete-orphan"
    )


class StoredTransaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    statement_id: Mapped[int] = mapped_column(
        ForeignKey("statements.id", ondelete="CASCADE")
    )
    date: Mapped[date] = mapped_column(Date)
    description: Mapped[str] = mapped_column(String)
    merchant: Mapped[str] = mapped_column(String)
    amount: Mapped[float] = mapped_column(Float)  # negative = spend, positive = inflow
    category: Mapped[str] = mapped_column(String)

    statement: Mapped["Statement"] = relationship(back_populates="transactions")


class Offset(Base):
    """A confirmed reimbursement: an inbound transfer offsets some spend tx.

    Offsets are overlays, never edits — the original transactions stay intact
    and the net spend is computed by subtracting offsets at aggregation time.
    """

    __tablename__ = "offsets"

    id: Mapped[int] = mapped_column(primary_key=True)
    transfer_tx_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"))
    spend_tx_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"))
    amount: Mapped[float] = mapped_column(Float)  # positive: how much spend is offset
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
