from datetime import date

from backend.db import repository
from backend.models import Transaction
from backend.trends import category_trends


def _tx(d, merchant, amount, category):
    return Transaction(
        date=d, description=merchant, merchant=merchant, amount=amount, category=category
    )


def test_two_months_produce_per_month_totals():
    repository.save_statement(
        "UOB", date(2026, 3, 1), date(2026, 3, 31), b"march",
        [
            _tx(date(2026, 3, 5), "HAWKER", -10.00, "Food"),
            _tx(date(2026, 3, 6), "CAFE", -20.00, "Food"),
            _tx(date(2026, 3, 7), "MRT", -5.00, "Transport"),
        ],
    )
    repository.save_statement(
        "UOB", date(2026, 4, 1), date(2026, 4, 30), b"april",
        [
            _tx(date(2026, 4, 5), "HAWKER", -40.00, "Food"),
            _tx(date(2026, 4, 6), "MRT", -8.00, "Transport"),
        ],
    )

    trends = category_trends()
    assert trends["Food"] == {"2026-03": 30.00, "2026-04": 40.00}
    assert trends["Transport"] == {"2026-03": 5.00, "2026-04": 8.00}


def test_month_level_refund_netting():
    # A refund nets against a charge within the same month/category.
    repository.save_statement(
        "UOB", date(2026, 4, 1), date(2026, 4, 30), b"april",
        [
            _tx(date(2026, 4, 5), "SHOP", -100.00, "Shopping"),
            _tx(date(2026, 4, 9), "SHOP", 30.00, "Shopping"),  # partial refund
        ],
    )
    trends = category_trends()
    assert trends["Shopping"] == {"2026-04": 70.00}


def test_category_that_nets_positive_is_dropped():
    repository.save_statement(
        "UOB", date(2026, 4, 1), date(2026, 4, 30), b"april",
        [
            _tx(date(2026, 4, 5), "SHOP", -40.00, "Shopping"),
            _tx(date(2026, 4, 9), "SHOP", 50.00, "Shopping"),  # over-refunded
        ],
    )
    trends = category_trends()
    assert "Shopping" not in trends  # net inflow -> not spend, dropped


def test_excluded_categories_absent_from_trends():
    repository.save_statement(
        "UOB", date(2026, 4, 1), date(2026, 4, 30), b"april",
        [
            _tx(date(2026, 4, 5), "TAN EN", 12.00, "Transfers"),
            _tx(date(2026, 4, 6), "SALARY", 3000.00, "Income"),
        ],
    )
    assert category_trends() == {}
