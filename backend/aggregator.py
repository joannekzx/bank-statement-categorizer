from collections import defaultdict
from typing import Iterable

from backend.models import Transaction, CategorySummary, MerchantSummary


# Categories that move money without being consumption. Excluded from spend.
EXCLUDED_FROM_SPEND = {"Transfers", "Income", "Investments"}


def net_spend_contribution(signed_amounts: Iterable[float]) -> float:
    """The ONE netting rule, shared by single-statement and trends views.

    Given the signed amounts in a group (negative = charge, positive = refund),
    return the net spend: -net if the group netted outward, else 0. A group that
    netted inward (refunds > charges) contributes 0, never a negative spend.
    """
    net = sum(signed_amounts)
    return -net if net < 0 else 0.0


def effective_amount(tx: Transaction) -> float:
    """Signed amount after applying any confirmed reimbursement offset.

    Offsets only shrink a spend toward zero; they never flip it to income and
    never exceed the original magnitude. The stored `amount` is preserved —
    this is computed on read.
    """
    if tx.amount >= 0 or tx.reimbursed <= 0:
        return tx.amount
    applied = min(tx.reimbursed, -tx.amount)  # cap at the spend magnitude
    return tx.amount + applied


def aggregate(transactions: list[Transaction]) -> dict:
    """Compute spend total, per-category summary, and top merchants.

    Spend convention:
      - Only spending categories count (Transfers/Income/Investments excluded).
      - Within a category, charges and refunds net out (a fully-refunded
        purchase contributes $0), via the shared netting rule.
      - Confirmed reimbursement offsets reduce the offset spend's contribution.
      - total_spend is the sum of net spend across all spending categories.
    """
    cat_amounts: dict[str, list[float]] = defaultdict(list)
    cat_count: dict[str, int] = defaultdict(int)
    cat_signed_net: dict[str, float] = defaultdict(float)  # for excluded movement
    merchant_amounts: dict[str, list[float]] = defaultdict(list)
    merchant_count: dict[str, int] = defaultdict(int)

    for tx in transactions:
        category = tx.category or "Other"
        eff = effective_amount(tx)
        cat_amounts[category].append(eff)
        cat_signed_net[category] += tx.amount  # excluded cats show raw movement
        cat_count[category] += 1

        if category not in EXCLUDED_FROM_SPEND:
            merchant_amounts[tx.merchant].append(eff)
            merchant_count[tx.merchant] += 1

    # total_spend: sum of net outflow across spending categories.
    total_spend = sum(
        net_spend_contribution(amounts)
        for cat, amounts in cat_amounts.items()
        if cat not in EXCLUDED_FROM_SPEND
    )

    # Per-category summary. Spending cats report net spend; excluded cats report
    # their net movement so they stay visible without counting as spend.
    by_category = [
        CategorySummary(
            category=cat,
            total=round(abs(cat_signed_net[cat]), 2)
            if cat in EXCLUDED_FROM_SPEND
            else round(net_spend_contribution(amounts), 2),
            count=cat_count[cat],
        )
        for cat, amounts in cat_amounts.items()
    ]
    by_category.sort(key=lambda c: -c.total)

    # Top merchants by net spend (spending categories only).
    top_merchants = [
        MerchantSummary(
            merchant=m,
            total=round(net_spend_contribution(amounts), 2),
            count=merchant_count[m],
        )
        for m, amounts in merchant_amounts.items()
        if net_spend_contribution(amounts) > 0  # only where you net-spent
    ]
    top_merchants.sort(key=lambda m: -m.total)
    top_merchants = top_merchants[:10]

    return {
        "total_spend": round(total_spend, 2),
        "by_category": by_category,
        "top_merchants": top_merchants,
    }
