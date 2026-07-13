# Bank Statement Categorizer — Walkthrough & Interview Prep

Read this before talking about the project. It's meant to be explained out loud,
not consulted as a spec. It covers what the thing is, how the pieces fit, the
order I built them in, how to run it, and how I'd defend the tricky parts.

---

## What this is, in one paragraph

You export a PDF bank statement (UOB savings), drop it on the page, and get back
a clean picture of where your money went: total spend, a per-category breakdown,
and your top merchants. The hard part isn't the chart — it's turning a messy PDF
into trustworthy numbers. A statement is just dates, cryptic descriptions, and a
running balance; there's no "category" column and no reliable sign on the amount.
So the project parses the PDF into real transactions, categorizes each merchant
through a cheap-to-expensive cascade (rules → cache → LLM), and aggregates spend
with one carefully-defined netting rule. Everything analyzed is stored, so you
also get history, month-over-month trends, and a suggest-then-confirm flow for
reimbursements (a friend PayNow-ing you back for a shared dinner).

## The flow, end to end

```
  PDF upload
     │
     ▼
  UOBParser ──► Transaction[]        parse text, derive signs from balance deltas
     │
     ▼
  Categorizer ──► rules → cache → LLM   three passes, each handles the leftovers
     │
     ▼
  repository.save_statement           persist to SQLite, dedupe by PDF hash
     │
     ▼
  aggregator.aggregate                one netting rule → totals / categories / merchants
     │
     ▼
  FastAPI JSON ──► React dashboard    charts, editable categories, history, trends
```

Two ideas do most of the work and are worth holding in your head:

- **The cascade** — most merchants are categorized for free (a rule or a cached
  past answer); the LLM only runs for genuinely novel ones, and its answers are
  cached so it never pays for the same merchant twice.
- **One netting rule** — there is exactly one function that decides "how much did
  you actually spend in this group of transactions," and the single-statement
  view, the trends view, and the offset math all call it. The views can't drift.

---

## A tour of the real files

### Backend

**`backend/models.py`** — the Pydantic API models (`Transaction`, `CategorySummary`,
`AnalysisResult`, `OffsetRequest`, …). This is the shape of the JSON crossing the
wire. Deliberately separate from the storage models (below); I convert at the
boundary so the API contract and the DB schema can evolve independently.

**`backend/parsers/uob.py`** — the parser, and the fiddliest file in the repo. A
UOB statement prints each transaction as a magnitude with no sign, plus a running
balance. So instead of trusting the printed amount, I derive the signed amount
from the **balance delta**: `new_balance − previous_balance`. A charge lowers the
balance (negative), a credit raises it (positive) — always correct, no guessing.
The parser reads the opening `BALANCE B/F`, groups lines into per-transaction
blocks, and walks them carrying the running balance forward. A pile of regexes
(`_SKIP_PATTERNS`, `_NOT_MERCHANT_PATTERNS`) strip headers, card refs, and PayNow
noise so the leftover line is the actual merchant name. `base.py` is the tiny
abstract `BaseParser` interface — the seam for adding another bank later.

**`backend/categorizer/`** — the cascade, one class per pass:
- `engine.py` (`RulesEngine`) — loads `rules.yaml`, does case-insensitive
  substring matching, first-match-wins. Validates on load that every rule points
  at a known category, so a typo fails loudly instead of silently mis-filing.
- `cache.py` (`CategoryCache`) — a SQLite table of `merchant → category`, keyed on
  a normalized (lowercased, trimmed) merchant so `"SHENG SIONG"` and
  `"sheng siong "` collapse to one entry. Batched `get_many` / `set_many`.
- `llm_fallback.py` (`LLMCategorizer`) — the only network call. Sends the novel
  merchants to Claude Haiku with a Singapore-aware system prompt, then defends
  hard against the model: extract the first `{...}` block, tolerate code fences,
  and coerce anything unknown, omitted, or any API error into `"Other"`.
- `pipeline.py` (`Categorizer`) — orchestrates the three passes. Each pass only
  sees what the previous one couldn't place; the LLM runs on the unique unmatched
  merchants only, and confident results are cached (but never `"Other"`, since
  that's often a transient API failure we'd want to retry).

**`backend/aggregator.py`** — the money math. `net_spend_contribution()` is *the*
netting rule: sum a group's signed amounts; if it netted outward, that's the
spend, otherwise it's zero (a fully-refunded purchase costs $0, never negative).
`effective_amount()` applies a confirmed reimbursement offset to a single
transaction, capped so it can only shrink a spend toward zero. `aggregate()`
builds the totals: spending categories net internally, excluded categories
(Transfers / Income / Investments) show raw movement but never count as spend.

**`backend/db/`** — persistence (SQLAlchemy):
- `engine.py` — the engine + `SessionLocal`, with a `configure()` hook so tests
  can repoint at a throwaway database.
- `models.py` — the storage models: `Statement`, `StoredTransaction`, `Offset`.
  Note the `content_hash` unique column on `Statement` (dedupe) and that `Offset`
  is an **overlay** — a separate row, never an edit to the original transaction.
- `repository.py` — the boundary layer. `save_statement()` dedupes by SHA-256 of
  the PDF bytes, `get_statement_transactions()` rebuilds API `Transaction`s with
  offsets applied, and `create_offset()` caps the offset so summed reimbursements
  never exceed the spend magnitude.

**`backend/reimbursements.py`** — `find_candidates()`: for each inbound transfer,
suggest the spends in offset-eligible categories within a 7-day window *before*
it, closest first. It only ever suggests — a human confirms.

**`backend/trends.py`** — `category_trends()`: the same netting rule as the
aggregator, but bucketed per calendar month across every stored statement.

**`backend/main.py`** — the FastAPI app and all routes (`/analyze`, `/correct`,
`/statements`, `/statements/{id}`, `/trends`, `.../reimbursements`, `/offsets`),
plus CORS for the local frontend and a startup hook that creates tables.

### Frontend (React + TypeScript + Vite + Tailwind)

- `App.tsx` — the shell: tab nav (Upload / History / Trends) and the top-level
  state machine (upload → dashboard → reimbursement review).
- `components/UploadZone.tsx` — the drag-and-drop PDF dropzone.
- `components/Dashboard.tsx` — the results screen: total, category chart, top
  merchants, transaction table, CSV export.
- `components/CategoryChart.tsx` / `TopMerchants.tsx` — the two summary panels
  (Recharts bar chart + a ranked list).
- `components/TransactionTable.tsx` + `CategoryEditor.tsx` — the table, with a
  click-to-recategorize pill that opens a searchable popover.
- `components/StatementHistory.tsx` / `TrendsView.tsx` — the history list and the
  month-over-month line chart.
- `components/ReimbursementReview.tsx` — the suggest-then-confirm UI.
- `lib/aggregate.ts` — a deliberate **mirror** of `aggregator.py`, used only to
  reflect a local correction instantly without a full re-analyze. It's marked as
  the one place the frontend forks backend math; the backend stays the source of
  truth on every real `/analyze`.
- `lib/format.ts`, `lib/csv.ts`, `lib/categories.ts`, `types.ts`, `api.ts` —
  formatting, CSV export, the muted category palette, shared types, and the
  fetch layer.

---

## What was built when

**Method: derived from `git log --stat --reverse`** (this directory is a git
repo — 17 commits, 2026-05-19 → 2026-06-24). Grouped into the phases the commit
messages and `NOTES.md` already call "weekends."

**Phase 1 — Foundations (2026-05-19).** Project scaffold + `requirements.txt`,
then the Pydantic models (`models.py`), then `NOTES.md` capturing the
reimbursement-matching idea before any of it was built. The design doc came
first.

**Phase 2 — The categorization core (2026-05-20).** The bulk of the backend, and
the ordering is telling: **parser tests against a fixture came before the parser**
(TDD), then the rules engine + starter `rules.yaml`, the SQLite cache, the LLM
fallback (with robust JSON extraction landing as its own commit — I clearly hit
the "model returns prose around the JSON" problem), the aggregator with
refund-netting and transfer exclusion, then the pipeline that wires rules → cache
→ LLM together with the UOB parser. Finally the `/analyze` endpoint, end-to-end
endpoint tests, and a README documenting the working backend. Cheap-and-certain
layers (rules, cache) were built before the expensive-and-fuzzy one (LLM).

**Phase 3 — The frontend (2026-06-10).** The whole React dashboard in one large
commit — upload, dashboard, category chart, top merchants, transaction table with
inline category correction — plus a follow-up fixing TypeScript type mismatches.

**Phase 4 — Persistence, trends, reimbursements (2026-06-24, "Weekend 3").** The
`backend/db/` layer (engine, storage models, repository) with hash-based dedupe;
`reimbursements.py` and `trends.py`; the aggregator extended with
`effective_amount()` for offsets; the matching frontend views
(`ReimbursementReview`, `StatementHistory`, `TrendsView`); and the client-side
`aggregate.ts` mirror so a correction re-renders without a round-trip. This is
where the project went from "analyze one PDF" to "a small personal finance tool
with memory."

---

## How to run it

Backend:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # add your ANTHROPIC_API_KEY
uvicorn backend.main:app --reload
```

Open http://localhost:8000/docs to upload a statement, or
`curl -F "file=@statement.pdf" http://localhost:8000/analyze`. `app.db` is created
on first run.

Frontend:

```bash
cd frontend
npm install
npm run dev                   # http://localhost:5173
```

Tests:

```bash
pytest -v                     # 53 tests: parser, categorizer, aggregator,
                              # persistence, trends, reimbursements, endpoints
```

The frontend `npm run build` and `npm run lint` both run clean.

---

## How I'd explain the hard parts

**The categorization cascade — why three layers instead of just calling the LLM?**
Cost, speed, and determinism. Most transactions are repeat merchants (NTUC, Grab,
your usual kopitiam), and an LLM call for each of those every month is slow,
expensive, and non-deterministic. So I go cheapest-first: hard rules for the
obvious stuff, a SQLite cache for anything I've seen before, and the LLM only for
genuinely novel merchants — whose answers I then cache, so I never pay for them
twice. The one subtlety worth calling out: I **don't cache `"Other"`**, because
`"Other"` is also what I return on an API failure, and I don't want a transient
outage to poison the cache forever. The known limitation (documented in
`NOTES.md`) is that manual corrections write to the cache, so they beat the LLM
but not the rules engine — a rule-matched merchant still wins on re-upload. That's
a deliberate trade: I'd rather keep rules deterministic than let a correction
silently override them.

**Reimbursement window capping — the point-in-time-style discipline.** When a
friend PayNows you $12 back for dinner, that shouldn't show up as $12 of income —
it should reduce the dinner's cost. But a +$12 from a person's name is
indistinguishable from a loan, a gift, or a Grab split using statement data alone.
So the system never auto-applies anything: it **suggests** candidate spends within
a bounded 7-day window *before* the transfer (closest first) and a human confirms.
On confirm, I store an `Offset` — a separate overlay row, never an edit to the
original transaction — and the aggregator subtracts it at read time, **capped at
the spend's magnitude** so an over-collection (three friends paying back a $30
share each) can never flip a spend into fake income. The window and the cap are
the "don't let a match reach beyond what it can plausibly explain" discipline, the
same instinct as a point-in-time join: only pull in what was true within a
defensible boundary. The original transaction stays intact for auditability.

**Dedup via content hashing — why hash the bytes?** Re-uploading the same PDF
shouldn't create a duplicate statement, and I don't want to rely on the period
dates (two different exports of the same month, or a re-download, should be
handled sanely). So `save_statement()` computes a SHA-256 of the **raw PDF bytes**
and stores it as a unique column. Identical bytes → replace the prior copy (and
clean up its transactions and any offsets that referenced them, since offsets have
no cascade of their own). Different bytes → a new statement. It's the same "keep
the latest version, keyed on a stable fingerprint" idea you'd use for idempotent
ingestion anywhere — the fingerprint here just happens to be the file's hash.

**Why two sets of models, and why mirror the aggregator in TypeScript?** The
Pydantic (`models.py`) and SQLAlchemy (`db/models.py`) models look redundant but
aren't — one is the API contract, one is the storage schema, and converting at the
boundary keeps them free to change independently. The `aggregate.ts` mirror is a
conscious, documented exception: it exists purely so a category correction
re-renders instantly client-side, and it's marked to stay in lockstep with
`aggregator.py`, which remains the source of truth on every real analyze.
