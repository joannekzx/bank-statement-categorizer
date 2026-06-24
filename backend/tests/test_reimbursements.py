from datetime import date

import pytest

from backend.aggregator import aggregate
from backend.db import repository
from backend.models import Transaction
from backend.reimbursements import find_candidates


def _tx(d, merchant, amount, category):
    return Transaction(
        date=d, description=merchant, merchant=merchant, amount=amount, category=category
    )


def _seed(transactions):
    sid = repository.save_statement(
        "UOB", date(2026, 4, 1), date(2026, 4, 30), b"april", transactions
    )
    return sid, repository.get_statement_transactions(sid)


def test_transfer_within_window_suggests_the_spend():
    _, txs = _seed([
        _tx(date(2026, 4, 18), "DINNER", -48.00, "Food"),
        _tx(date(2026, 4, 20), "TAN EN", 12.00, "Transfers"),
    ])
    suggestions = find_candidates(txs)
    assert len(suggestions) == 1
    assert suggestions[0]["transfer"].merchant == "TAN EN"
    assert [c.merchant for c in suggestions[0]["candidates"]] == ["DINNER"]


def test_transfer_outside_window_suggests_nothing():
    _, txs = _seed([
        _tx(date(2026, 4, 1), "DINNER", -48.00, "Food"),
        _tx(date(2026, 4, 20), "TAN EN", 12.00, "Transfers"),  # 19 days later
    ])
    assert find_candidates(txs) == []


def test_transfer_before_spend_not_suggested():
    # Money arrived before the spend — can't be a reimbursement for it.
    _, txs = _seed([
        _tx(date(2026, 4, 20), "DINNER", -48.00, "Food"),
        _tx(date(2026, 4, 18), "TAN EN", 12.00, "Transfers"),
    ])
    assert find_candidates(txs) == []


def test_confirmed_offset_reduces_category_total():
    sid, txs = _seed([
        _tx(date(2026, 4, 18), "DINNER", -48.00, "Food"),
        _tx(date(2026, 4, 20), "TAN EN", 12.00, "Transfers"),
    ])
    by_id = {t.merchant: t.id for t in txs}
    repository.create_offset(by_id["TAN EN"], by_id["DINNER"], 12.00)

    reloaded = repository.get_statement_transactions(sid)
    food = aggregate(reloaded)
    cats = {c.category: c.total for c in food["by_category"]}
    assert cats["Food"] == 36.00  # 48 - 12
    assert food["total_spend"] == 36.00


def test_offset_caps_at_spend_amount():
    sid, txs = _seed([
        _tx(date(2026, 4, 18), "DINNER", -48.00, "Food"),
        _tx(date(2026, 4, 20), "RICH FRIEND", 100.00, "Transfers"),
    ])
    by_id = {t.merchant: t.id for t in txs}
    off = repository.create_offset(by_id["RICH FRIEND"], by_id["DINNER"], 100.00)
    assert off["amount"] == 48.00  # capped at the spend magnitude

    reloaded = repository.get_statement_transactions(sid)
    cats = {c.category: c.total for c in aggregate(reloaded)["by_category"]}
    assert cats["Food"] == 0.00


def test_multiple_offsets_on_one_spend_sum():
    sid, txs = _seed([
        _tx(date(2026, 4, 18), "DINNER", -48.00, "Food"),
        _tx(date(2026, 4, 19), "FRIEND A", 16.00, "Transfers"),
        _tx(date(2026, 4, 20), "FRIEND B", 16.00, "Transfers"),
    ])
    by_id = {t.merchant: t.id for t in txs}
    repository.create_offset(by_id["FRIEND A"], by_id["DINNER"], 16.00)
    repository.create_offset(by_id["FRIEND B"], by_id["DINNER"], 16.00)

    reloaded = repository.get_statement_transactions(sid)
    dinner = next(t for t in reloaded if t.merchant == "DINNER")
    assert dinner.reimbursed == 32.00
    assert dinner.amount == -48.00  # original preserved
    cats = {c.category: c.total for c in aggregate(reloaded)["by_category"]}
    assert cats["Food"] == 16.00  # 48 - 32


def test_combined_offsets_cannot_exceed_spend():
    sid, txs = _seed([
        _tx(date(2026, 4, 18), "DINNER", -48.00, "Food"),
        _tx(date(2026, 4, 19), "FRIEND A", 40.00, "Transfers"),
        _tx(date(2026, 4, 20), "FRIEND B", 40.00, "Transfers"),
    ])
    by_id = {t.merchant: t.id for t in txs}
    repository.create_offset(by_id["FRIEND A"], by_id["DINNER"], 40.00)
    second = repository.create_offset(by_id["FRIEND B"], by_id["DINNER"], 40.00)
    assert second["amount"] == 8.00  # only 8 of the spend left to offset

    reloaded = repository.get_statement_transactions(sid)
    cats = {c.category: c.total for c in aggregate(reloaded)["by_category"]}
    assert cats["Food"] == 0.00


def test_offset_rejects_non_spend_target():
    _, txs = _seed([
        _tx(date(2026, 4, 18), "SALARY", 3000.00, "Income"),
        _tx(date(2026, 4, 20), "TAN EN", 12.00, "Transfers"),
    ])
    by_id = {t.merchant: t.id for t in txs}
    with pytest.raises(ValueError):
        repository.create_offset(by_id["TAN EN"], by_id["SALARY"], 12.00)
