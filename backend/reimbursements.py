from datetime import timedelta

from backend.models import Transaction


# Categories where an inbound transfer plausibly offsets a shared expense.
OFFSET_ELIGIBLE = {"Food", "Shopping", "Travel", "Entertainment"}
WINDOW_DAYS = 7


def find_candidates(transactions: list[Transaction]) -> list[dict]:
    """Suggest, never apply.

    For each inbound transfer (positive Transfers row), propose the spend
    transactions within WINDOW_DAYS before it that it might offset, closest
    first. Spends already fully reimbursed are skipped. A +$12 from a friend is
    indistinguishable from a loan or gift using statement data alone, so this
    only surfaces candidates for a human to confirm or dismiss.
    """
    inbound = [
        t for t in transactions if t.category == "Transfers" and t.amount > 0
    ]
    spends = [
        t
        for t in transactions
        if t.amount < 0
        and t.category in OFFSET_ELIGIBLE
        and t.reimbursed < -t.amount  # still has unoffset spend left
    ]

    suggestions: list[dict] = []
    for transfer in inbound:
        candidates = [
            sp
            for sp in spends
            if timedelta(0) <= (transfer.date - sp.date) <= timedelta(days=WINDOW_DAYS)
        ]
        candidates.sort(key=lambda sp: transfer.date - sp.date)  # closest first
        if candidates:
            suggestions.append({"transfer": transfer, "candidates": candidates})
    return suggestions
