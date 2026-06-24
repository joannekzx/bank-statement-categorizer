import hashlib
from datetime import date

from sqlalchemy import select

from backend.db.engine import SessionLocal
from backend.db.models import Offset, Statement, StoredTransaction
from backend.models import Transaction


def content_hash(pdf_bytes: bytes) -> str:
    """Stable fingerprint of the raw PDF bytes, used for dedupe on re-upload."""
    return hashlib.sha256(pdf_bytes).hexdigest()


def to_transaction(row: StoredTransaction, reimbursed: float = 0.0) -> Transaction:
    """Convert a stored row back into the API Transaction shape.

    `reimbursed` is the confirmed offset total applied to this row, computed
    from the offsets table — never stored on the row itself.
    """
    return Transaction(
        id=row.id,
        date=row.date,
        description=row.description,
        merchant=row.merchant,
        amount=row.amount,
        category=row.category,
        reimbursed=reimbursed,
    )


def save_statement(
    bank: str,
    period_start: date,
    period_end: date,
    pdf_bytes: bytes,
    transactions: list[Transaction],
) -> int:
    """Persist a statement and its transactions, deduping by content hash.

    Re-uploading the same file (identical bytes) replaces the prior copy: the
    old statement, its transactions, and any offsets referencing them are
    cleared first. Different bytes (a different month, or even the same month
    re-exported) are stored as a new statement.
    """
    h = content_hash(pdf_bytes)
    with SessionLocal() as s:
        existing = s.scalar(select(Statement).where(Statement.content_hash == h))
        if existing is not None:
            _delete_statement(s, existing)
            s.flush()

        stmt = Statement(
            bank=bank,
            period_start=period_start,
            period_end=period_end,
            content_hash=h,
        )
        stmt.transactions = [
            StoredTransaction(
                date=t.date,
                description=t.description,
                merchant=t.merchant,
                amount=t.amount,
                category=t.category or "Other",
            )
            for t in transactions
        ]
        s.add(stmt)
        s.commit()
        return stmt.id


def _delete_statement(s, stmt: Statement) -> None:
    """Delete a statement, its transactions (cascade), and any offsets that
    reference those transactions (offsets have no cascade of their own)."""
    tx_ids = [t.id for t in stmt.transactions]
    if tx_ids:
        for off in s.scalars(
            select(Offset).where(
                (Offset.transfer_tx_id.in_(tx_ids))
                | (Offset.spend_tx_id.in_(tx_ids))
            )
        ):
            s.delete(off)
    s.delete(stmt)


def list_statements() -> list[dict]:
    """Summaries for the history view, newest upload first."""
    out: list[dict] = []
    with SessionLocal() as s:
        statements = s.scalars(
            select(Statement).order_by(Statement.period_start.desc())
        ).all()
        for stmt in statements:
            txs = [to_transaction(t) for t in stmt.transactions]
            offsets = _offsets_for(s, [t.id for t in stmt.transactions])
            _apply_offsets(txs, offsets)
            from backend.aggregator import aggregate

            agg = aggregate(txs)
            out.append(
                {
                    "id": stmt.id,
                    "bank": stmt.bank,
                    "period_start": stmt.period_start,
                    "period_end": stmt.period_end,
                    "uploaded_at": stmt.uploaded_at,
                    "transaction_count": len(txs),
                    "total_spend": agg["total_spend"],
                }
            )
    return out


def get_statement_meta(statement_id: int) -> dict | None:
    with SessionLocal() as s:
        stmt = s.get(Statement, statement_id)
        if stmt is None:
            return None
        return {
            "id": stmt.id,
            "bank": stmt.bank,
            "period_start": stmt.period_start,
            "period_end": stmt.period_end,
        }


def get_statement_transactions(statement_id: int) -> list[Transaction] | None:
    """All transactions of a statement as API models, with offsets applied."""
    with SessionLocal() as s:
        stmt = s.get(Statement, statement_id)
        if stmt is None:
            return None
        txs = [to_transaction(t) for t in stmt.transactions]
        offsets = _offsets_for(s, [t.id for t in stmt.transactions])
        _apply_offsets(txs, offsets)
        return txs


def _offsets_for(s, tx_ids: list[int]) -> list[Offset]:
    if not tx_ids:
        return []
    return list(
        s.scalars(select(Offset).where(Offset.spend_tx_id.in_(tx_ids))).all()
    )


def _apply_offsets(txs: list[Transaction], offsets: list[Offset]) -> None:
    """Populate each transaction's `reimbursed` total from confirmed offsets.

    Multiple offsets can point at one spend (a dinner split among friends);
    their amounts sum, capped at the spend magnitude.
    """
    by_spend: dict[int, float] = {}
    for off in offsets:
        by_spend[off.spend_tx_id] = by_spend.get(off.spend_tx_id, 0.0) + off.amount
    for tx in txs:
        if tx.id in by_spend:
            tx.reimbursed = min(by_spend[tx.id], -tx.amount) if tx.amount < 0 else 0.0


def create_offset(transfer_tx_id: int, spend_tx_id: int, amount: float) -> dict:
    """Record a confirmed reimbursement. Returns the created offset as a dict.

    Validates that both transactions exist, that the spend is actually a spend,
    and caps `amount` so the summed offsets never exceed the spend magnitude.
    """
    with SessionLocal() as s:
        transfer = s.get(StoredTransaction, transfer_tx_id)
        spend = s.get(StoredTransaction, spend_tx_id)
        if transfer is None or spend is None:
            raise ValueError("transfer or spend transaction not found")
        if spend.amount >= 0:
            raise ValueError("spend transaction must be an outflow")

        already = sum(
            o.amount
            for o in s.scalars(
                select(Offset).where(Offset.spend_tx_id == spend_tx_id)
            )
        )
        room = max(0.0, -spend.amount - already)  # remaining offsettable spend
        capped = round(min(max(amount, 0.0), room), 2)

        off = Offset(
            transfer_tx_id=transfer_tx_id,
            spend_tx_id=spend_tx_id,
            amount=capped,
        )
        s.add(off)
        s.commit()
        return {
            "id": off.id,
            "transfer_tx_id": off.transfer_tx_id,
            "spend_tx_id": off.spend_tx_id,
            "amount": off.amount,
        }
