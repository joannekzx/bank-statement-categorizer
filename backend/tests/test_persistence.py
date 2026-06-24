from datetime import date

from sqlalchemy import func, select

from backend.db import repository
from backend.db.engine import SessionLocal
from backend.db.models import Statement, StoredTransaction
from backend.models import Transaction


def _tx(day, merchant, amount, category):
    return Transaction(
        date=date(2026, 4, day),
        description=f"{merchant} desc",
        merchant=merchant,
        amount=amount,
        category=category,
    )


def _sample():
    return [
        _tx(1, "HAWKER", -8.50, "Food"),
        _tx(2, "NTUC", -42.00, "Groceries"),
        _tx(3, "TAN EN", 12.00, "Transfers"),
    ]


def _count(model):
    with SessionLocal() as s:
        return s.scalar(select(func.count()).select_from(model))


def test_save_and_reload_round_trips():
    sid = repository.save_statement(
        "UOB", date(2026, 4, 1), date(2026, 4, 30), b"pdf-bytes-A", _sample()
    )
    reloaded = repository.get_statement_transactions(sid)
    assert len(reloaded) == 3
    by_merchant = {t.merchant: t for t in reloaded}
    assert by_merchant["HAWKER"].amount == -8.50
    assert by_merchant["HAWKER"].category == "Food"
    assert all(t.id is not None for t in reloaded)


def test_same_hash_dedupes():
    args = ("UOB", date(2026, 4, 1), date(2026, 4, 30))
    repository.save_statement(*args, b"identical-bytes", _sample())
    repository.save_statement(*args, b"identical-bytes", _sample())  # re-upload

    assert _count(Statement) == 1
    assert _count(StoredTransaction) == 3  # not duplicated


def test_different_hash_coexists():
    repository.save_statement(
        "UOB", date(2026, 3, 1), date(2026, 3, 31), b"march-bytes", _sample()
    )
    repository.save_statement(
        "UOB", date(2026, 4, 1), date(2026, 4, 30), b"april-bytes", _sample()
    )
    assert _count(Statement) == 2
    assert _count(StoredTransaction) == 6


def test_reupload_cascade_clears_old_transactions():
    args = ("UOB", date(2026, 4, 1), date(2026, 4, 30))
    repository.save_statement(*args, b"same-bytes", _sample())
    # Re-upload the same file but with fewer transactions.
    repository.save_statement(*args, b"same-bytes", [_tx(1, "HAWKER", -8.50, "Food")])

    assert _count(Statement) == 1
    assert _count(StoredTransaction) == 1  # old 3 rows cascade-deleted


def test_list_statements_summary():
    repository.save_statement(
        "UOB", date(2026, 4, 1), date(2026, 4, 30), b"april", _sample()
    )
    rows = repository.list_statements()
    assert len(rows) == 1
    row = rows[0]
    assert row["transaction_count"] == 3
    # Spend = 8.50 + 42.00 (transfer excluded).
    assert row["total_spend"] == 50.50
