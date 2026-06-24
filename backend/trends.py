from collections import defaultdict

from sqlalchemy import select

from backend.aggregator import EXCLUDED_FROM_SPEND, effective_amount, net_spend_contribution
from backend.db.engine import SessionLocal
from backend.db.models import Offset, StoredTransaction
from backend.db.repository import to_transaction


def category_trends() -> dict[str, dict[str, float]]:
    """Spend by (category, month) across every stored statement.

    Returns {category: {"2026-03": 180.5, "2026-04": 166.83, ...}}.

    Netting matches the single-statement aggregator exactly (same shared rule),
    but applied per calendar month rather than per statement: charges and
    refunds within a category net across the whole month, confirmed offsets are
    subtracted, and a month where a category netted positive is dropped.
    """
    # Accumulate signed (offset-adjusted) amounts per category per month.
    by_month_cat: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )

    with SessionLocal() as s:
        offsets = list(s.scalars(select(Offset)).all())
        reimbursed: dict[int, float] = defaultdict(float)
        for off in offsets:
            reimbursed[off.spend_tx_id] += off.amount

        for row in s.scalars(select(StoredTransaction)):
            if row.category in EXCLUDED_FROM_SPEND:
                continue
            tx = to_transaction(row, reimbursed=0.0)
            if row.id in reimbursed and row.amount < 0:
                tx.reimbursed = min(reimbursed[row.id], -row.amount)
            month = row.date.strftime("%Y-%m")
            by_month_cat[row.category][month].append(effective_amount(tx))

    # Net each (category, month) with the shared rule; drop net-zero months.
    out: dict[str, dict[str, float]] = {}
    for cat, months in by_month_cat.items():
        netted = {
            month: round(net_spend_contribution(amounts), 2)
            for month, amounts in months.items()
        }
        netted = {m: v for m, v in netted.items() if v > 0}
        if netted:
            out[cat] = dict(sorted(netted.items()))
    return out
