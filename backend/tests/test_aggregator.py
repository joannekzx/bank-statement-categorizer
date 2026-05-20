from datetime import date

import pytest

from backend.aggregator import aggregate
from backend.models import Transaction


def _tx(merchant, amount, category):
    return Transaction(
        date=date(2026, 4, 1), description=merchant,
        merchant=merchant, amount=amount, category=category,
    )


def test_basic_spend():
    txs = [
        _tx("KOPITIAM", -5.00, "Food"),
        _tx("SHENG SIONG", -20.00, "Groceries"),
    ]
    result = aggregate(txs)
    assert result["total_spend"] == 25.00


def test_transfers_excluded_from_spend():
    txs = [
        _tx("KOPITIAM", -5.00, "Food"),
        _tx("YOUTRIP", -500.00, "Transfers"),  # huge, but not spend
    ]
    result = aggregate(txs)
    assert result["total_spend"] == 5.00


def test_income_excluded():
    txs = [
        _tx("KOPITIAM", -5.00, "Food"),
        _tx("TUITION", 80.00, "Income"),
    ]
    result = aggregate(txs)
    assert result["total_spend"] == 5.00


def test_refund_nets_against_charge():
    txs = [
        _tx("LINKEDIN", -302.66, "Subscriptions"),
        _tx("LINKEDIN", 302.66, "Subscriptions"),  # refund
    ]
    result = aggregate(txs)
    assert result["total_spend"] == 0.0  # nets to zero


def test_orphan_refund_does_not_go_negative():
    txs = [
        _tx("UDEMY", 19.42, "Subscriptions"),  # refund, no matching charge
        _tx("KOPITIAM", -5.00, "Food"),
    ]
    result = aggregate(txs)
    # Subscriptions nets positive (inflow) -> contributes 0, not -19.42
    assert result["total_spend"] == 5.00


def test_category_summary_sorted_by_spend():
    txs = [
        _tx("KOPITIAM", -5.00, "Food"),
        _tx("SHENG SIONG", -50.00, "Groceries"),
    ]
    result = aggregate(txs)
    cats = result["by_category"]
    assert cats[0].category == "Groceries"  # bigger spend first
    assert cats[0].total == 50.00


def test_top_merchants():
    txs = [
        _tx("SHENG SIONG", -30.00, "Groceries"),
        _tx("SHENG SIONG", -20.00, "Groceries"),
        _tx("KOPITIAM", -5.00, "Food"),
    ]
    result = aggregate(txs)
    top = result["top_merchants"]
    assert top[0].merchant == "SHENG SIONG"
    assert top[0].total == 50.00  # aggregated across both visits
    assert top[0].count == 2


def test_transfer_merchant_not_in_top():
    txs = [
        _tx("YOUTRIP", -500.00, "Transfers"),
        _tx("KOPITIAM", -5.00, "Food"),
    ]
    result = aggregate(txs)
    merchants = [m.merchant for m in result["top_merchants"]]
    assert "YOUTRIP" not in merchants  # transfers excluded from merchants too