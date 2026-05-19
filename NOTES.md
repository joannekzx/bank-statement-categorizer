# Project Notes

## Future features

### Reimbursement matching
When the user pays for a shared meal and friends PayNow them back afterwards,
the inbound transfers should offset the original spend in the category totals,
not show up as "Income".

**Example flow:**
- 19 Apr: -$120 at restaurant → Food
- 20 Apr: +$30 from Friend A, +$30 from Friend B, +$30 from Friend C
- True personal spend on this meal: $30, not $120

**Open questions to resolve when building:**
- Pure heuristic (match incoming PayNow to recent food spend within N days)
  vs. user-confirmed (LLM suggests matches, user approves)?
- How to handle partial reimbursements (only one friend pays back)?
- What window? 7 days feels right but should be configurable.
- Should reimbursements be a new transaction category ("Reimbursement") or
  silently net against the original transaction?
- UI: show original $120 with a "-$90 reimbursed" annotation, or just show
  net $30? The former preserves auditability.

**Likely approach:** new optional field `reimbursements: list[Transaction]`
on Transaction, populated in a post-categorization pass. Aggregator subtracts
reimbursement totals from the parent transaction's category.