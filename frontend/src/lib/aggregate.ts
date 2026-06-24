import type { Transaction, CategorySummary, MerchantSummary } from "../types";
import { EXCLUDED_CATEGORIES } from "../types";

// EXACT MIRROR of backend/aggregator.py (verified against the real file).
// Used only to reflect a local category correction without a full re-analyze.
// If the backend aggregation rules change, change them here too. The backend
// remains the source of truth on every real /analyze.
const round2 = (n: number) => Math.round((n + Number.EPSILON) * 100) / 100;

// Signed amount after applying a confirmed reimbursement offset; mirrors
// aggregator.effective_amount. Offsets shrink a spend toward zero only.
function effectiveAmount(tx: Transaction): number {
  if (tx.amount >= 0 || tx.reimbursed <= 0) return tx.amount;
  return tx.amount + Math.min(tx.reimbursed, -tx.amount);
}

export function recompute(transactions: Transaction[]): {
  total_spend: number;
  by_category: CategorySummary[];
  top_merchants: MerchantSummary[];
} {
  const catNet = new Map<string, number>();
  const catCount = new Map<string, number>();
  const merchantNet = new Map<string, number>();
  const merchantCount = new Map<string, number>();

  for (const tx of transactions) {
    const cat = tx.category ?? "Other";
    const eff = effectiveAmount(tx);
    catNet.set(cat, (catNet.get(cat) ?? 0) + eff); // signed, offset-adjusted
    catCount.set(cat, (catCount.get(cat) ?? 0) + 1);

    // Merchant totals accumulate over spending categories only — and they
    // net charges against refunds BEFORE any threshold (the bug in my port).
    if (!EXCLUDED_CATEGORIES.has(cat)) {
      merchantNet.set(tx.merchant, (merchantNet.get(tx.merchant) ?? 0) + eff);
      merchantCount.set(tx.merchant, (merchantCount.get(tx.merchant) ?? 0) + 1);
    }
  }

  // total_spend: net outflow across spending categories; net inflow → 0.
  let total_spend = 0;
  for (const [cat, net] of catNet) {
    if (!EXCLUDED_CATEGORIES.has(cat) && net < 0) total_spend += -net;
  }

  // Spending category: -net if it net-spent, else 0 (NOT abs of an inflow).
  // Excluded category: abs(net), so it's still visible as movement.
  const by_category: CategorySummary[] = [...catNet.entries()]
    .map(([cat, net]) => ({
      category: cat,
      total: EXCLUDED_CATEGORIES.has(cat)
        ? round2(Math.abs(net))
        : round2(net < 0 ? -net : 0),
      count: catCount.get(cat) ?? 0,
    }))
    .sort((a, b) => b.total - a.total);

  // Only merchants you NET-spent at; total = -net, count = all spending rows.
  const top_merchants: MerchantSummary[] = [...merchantNet.entries()]
    .filter(([, net]) => net < 0)
    .map(([merchant, net]) => ({
      merchant,
      total: round2(-net),
      count: merchantCount.get(merchant) ?? 0,
    }))
    .sort((a, b) => b.total - a.total)
    .slice(0, 10);

  return { total_spend: round2(total_spend), by_category, top_merchants };
}