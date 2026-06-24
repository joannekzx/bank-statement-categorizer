# Bank Statement Categorizer

Parses Singapore bank PDF statements (UOB) and returns categorized spending
data: total spend, per-category breakdown, and top merchants. Statements are
persisted, so you also get a history list, month-over-month trends, and
suggest-then-confirm reimbursement matching.

## How it works

PDF → parser → categorizer (rules → cache → LLM cascade) → aggregator → JSON,
with every analyzed statement persisted to SQLite for history and trends.

- **Parser** extracts transactions using running-balance deltas for correct signs.
- **Categorizer** tries fast rules first, then a SQLite cache of past results,
  then falls back to Claude Haiku for novel merchants (and caches the answer).
- **Aggregator** computes spend via one shared netting rule (refunds net within
  a category, transfers/income/investments excluded, confirmed offsets subtracted).
- **Persistence** (`backend/db/`) stores statements + transactions in `app.db`,
  deduping re-uploads by a SHA-256 hash of the raw PDF bytes.
- **Trends** (`backend/trends.py`) re-applies the same netting rule per calendar
  month across all stored statements.
- **Reimbursements** (`backend/reimbursements.py`) suggests inbound transfers that
  may offset a recent spend; a confirmed offset is stored as a separate record and
  subtracted at read time — the original transaction is never rewritten.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/analyze` | Parse + categorize + persist a statement |
| `POST` | `/correct` | Persist a merchant→category correction (writes the cache) |
| `GET` | `/statements` | List stored statements (newest period first) |
| `GET` | `/statements/{id}` | Full `AnalysisResult` rebuilt from stored rows |
| `GET` | `/trends` | `{category: {"YYYY-MM": spend}}` across all statements |
| `GET` | `/statements/{id}/reimbursements` | Candidate transfer↔spend matches |
| `POST` | `/offsets` | Confirm a reimbursement (capped at the spend amount) |

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then add your ANTHROPIC_API_KEY
```

## Run

```bash
uvicorn backend.main:app --reload
```

Then open http://localhost:8000/docs to upload a statement, or:

```bash
curl -F "file=@your_statement.pdf" http://localhost:8000/analyze
```

The database (`app.db`) is created automatically on first run.

### Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173 (Upload / History / Trends tabs)
```

## Test

```bash
pytest -v
```

## Notes

- Currently supports UOB savings statements only. See `backend/parsers/` for
  adding banks.
- Storage models (`backend/db/models.py`, SQLAlchemy) are kept separate from API
  models (`backend/models.py`, Pydantic); convert at the boundary.
- Reimbursement matching is deliberately suggest-then-confirm: a +$12 from a
  friend is indistinguishable from a loan/gift using statement data alone, so a
  human always confirms before any category total changes.
- Personal categorization override rules (corrections that beat the rules engine,
  not just the cache) remain a future feature — see `NOTES.md`.
- Fixture PDFs and `*.db` files are gitignored — real data never enters version control.