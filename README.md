# Bank Statement Categorizer

Parses Singapore bank PDF statements (UOB) and returns categorized spending
data: total spend, per-category breakdown, and top merchants.

## How it works

PDF → parser → categorizer (rules → cache → LLM cascade) → aggregator → JSON.

- **Parser** extracts transactions using running-balance deltas for correct signs.
- **Categorizer** tries fast rules first, then a SQLite cache of past results,
  then falls back to Claude Haiku for novel merchants (and caches the answer).
- **Aggregator** computes spend, netting refunds and excluding transfers/income/
  investments.

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

## Test

```bash
pytest -v
```

## Notes

- Currently supports UOB savings statements only. See `backend/parsers/` for
  adding banks.
- Personal categorization rules: see `NOTES.md` for the planned local-overrides
  and manual-correction features.
- Fixture PDFs are gitignored — real statements never enter version control.