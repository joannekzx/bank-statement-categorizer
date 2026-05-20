from collections import defaultdict

from backend.models import Transaction, CategorySummary, MerchantSummary


# Categories that move money without being consumption. Excluded from spend.
EXCLUDED_FROM_SPEND = {"Transfers", "Income", "Investments"}


def aggregate(transactions: list[Transaction]) -> dict:
    """Compute spend total, per-category summary, and top merchants.

    Spend convention:
      - Only spending categories count (Transfers/Income/Investments excluded).
      - Within a category, charges (negative) and refunds (positive) net out,
        so a fully-refunded purchase contributes $0.
      - total_spend is the sum of net spend across all spending categories.
    """
    # Net signed amount per category and per merchant.
    # Negative net = money out (spend). Positive net = net inflow.
    cat_net: dict[str, float] = defaultdict(float)
    cat_count: dict[str, int] = defaultdict(int)
    merchant_net: dict[str, float] = defaultdict(float)
    merchant_count: dict[str, int] = defaultdict(int)

    for tx in transactions:
        category = tx.category or "Other"
        cat_net[category] += tx.amount
        cat_count[category] += 1

        if category not in EXCLUDED_FROM_SPEND:
            merchant_net[tx.merchant] += tx.amount
            merchant_count[tx.merchant] += 1

    # total_spend: sum of net outflow across spending categories.
    # A category with net inflow (refunds > charges) contributes 0, so an
    # orphan refund can't push total_spend negative.
    total_spend = 0.0
    for category, net in cat_net.items():
        if category not in EXCLUDED_FROM_SPEND and net < 0:
            total_spend += -net

    # Per-category summary: report net spend (positive = money out).
    # Excluded categories report their net movement so they're still visible.
    by_category = [
        CategorySummary(
            category=cat,
            total=round(-net if net < 0 else 0.0, 2)
            if cat not in EXCLUDED_FROM_SPEND
            else round(abs(net), 2),
            count=cat_count[cat],
        )
        for cat, net in cat_net.items()
    ]
    by_category.sort(key=lambda c: -c.total)

    # Top merchants by net spend (spending categories only).
    top_merchants = [
        MerchantSummary(merchant=m, total=round(-net, 2), count=merchant_count[m])
        for m, net in merchant_net.items()
        if net < 0  # only merchants you net-spent money at
    ]
    top_merchants.sort(key=lambda m: -m.total)
    top_merchants = top_merchants[:10]

    return {
        "total_spend": round(total_spend, 2),
        "by_category": by_category,
        "top_merchants": top_merchants,
    }