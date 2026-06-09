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

## Future features

### Manual category corrections
When the LLM classifies a merchant as the wrong category, the user should be
able to override it. The override should be stored as a per-user rule (in DB,
not YAML) and take priority over both the rules engine and the LLM on future
runs. The cache should respect these overrides.

**Example:** Math tuition payments from "LEE HUAY LING" look like outgoing
PayNow to a person's name. The LLM will guess "Transfers". User corrects to
"Income" once, the system remembers forever.

### Reimbursement matching (refined with real data)

**Problem observed in April statement:** Food total was $166.83, but several
inbound PayNows (TAY SHU CHEN +$9 +$3, TAN HUI +$12, TAN EN +$12) are likely
friends repaying shared meals. True food spend is lower; the offset money is
stranded in Transfers, disconnected from the Food charge it relates to.

**Why it can't be fully automatic:** The statement has only name + amount + date.
A +$12 could be a meal repayment, loan, gift, or Grab split — indistinguishable
from the data alone. Wrong financial numbers are worse than none.

**Design: suggest-then-confirm**
1. After categorization, find inbound transfers (positive amount, Transfers cat).
2. For each, find candidate spend transactions within a window (e.g. 7 days
   before, configurable) in offset-eligible categories (Food, Shopping, Travel).
3. Surface candidates in the UI: "Does +$12 from TAN EN offset your -$48
   dinner on 18 Apr?" User links or dismisses.
4. On confirm, store a link: the transfer offsets N dollars of the parent
   transaction. Parent's effective spend drops by the offset amount.

**Data model sketch:**
- New table/field: `offsets` linking a transfer tx to a spend tx + amount.
- Aggregator: subtract confirmed offsets from category & merchant totals.
- Display: show original -$48 with "-$12 reimbursed (TAN EN)" annotation,
  net $36. Preserve the original for auditability — never silently rewrite.

**Open questions:**
- One transfer offsetting multiple meals? Split a transfer across parents?
- What if offsets exceed the charge (you over-collected)? Cap at charge amount.
- Should confirmed offset pairs be remembered (TAN EN always = food split)?

**Dependencies:** needs the frontend (Weekend 4+). Until then, Transfers stays
a separate bucket and Food is slightly overstated. Acceptable for MVP.


### Manual category corrections — SHIPPED (Weekend 2)

Implemented as `POST /correct {merchant, category}` → `categorizer.cache.set_many`.
The frontend pill dropdown calls it, updates all rows of that merchant locally,
and re-aggregates client-side (see `frontend/src/lib/aggregate.ts`, an exact
mirror of `aggregator.py`).

**Known limitation — corrections only beat the LLM, not the rules engine.**
The cascade is rules → cache → LLM, and `/correct` writes to the cache. So:
- Correcting an LLM- or Other-categorized merchant persists: the cache pass
  catches it on the next /analyze, before the LLM runs.
- Correcting a *rule*-matched merchant does NOT persist: the rule still fires
  first and overwrites it on re-upload.

This is acceptable for the MVP — the merchants users actually want to fix are
the LLM/Other ones. The proper fix is the per-user override store already
sketched above (overrides beating BOTH rules and LLM). Defer to a later weekend;
do not try to make the cache outrank rules, as that breaks rule determinism for
everything else.

**Client-side re-aggregation caveat:** `aggregate.ts` duplicates the backend's
netting/exclusion/rounding rules so a correction's effect shows without a full
re-analyze. If `aggregator.py` ever changes, update `aggregate.ts` in lockstep —
it's the one place frontend forks backend math, and it's marked as such.