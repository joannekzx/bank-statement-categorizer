import os
import tempfile
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()  # must run before importing modules that read env vars

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.parsers.uob import UOBParser
from backend.categorizer.pipeline import Categorizer
from backend.categorizer.llm_fallback import VALID_CATEGORIES
from backend.aggregator import aggregate
from backend.models import (
    AnalysisResult,
    Correction,
    OffsetRequest,
    OffsetResponse,
    ReimbursementSuggestion,
    StatementSummary,
)
from backend.db.engine import init_db
from backend.db import repository
from backend.trends import category_trends
from backend.reimbursements import find_candidates

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # create tables if the DB file is new; idempotent otherwise
    yield


app = FastAPI(title="Bank Statement Categorizer", lifespan=lifespan)

# CORS so the local frontend can call this API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Built once at startup, reused across requests. The Categorizer holds the
# rules, cache connection, and LLM client — no reason to rebuild per request.
categorizer = Categorizer()


@app.get("/")
def health():
    return {"status": "ok"}


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    # pdfplumber needs a real path, so write the upload to a temp file.
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            contents = await file.read()
            if not contents:
                raise HTTPException(status_code=400, detail="Uploaded file is empty")
            tmp.write(contents)
            tmp_path = tmp.name

        parser = UOBParser()  # later: auto-detect bank
        try:
            transactions = parser.parse(tmp_path)
            period_start, period_end = parser.detect_period(tmp_path)
        except Exception as e:
            # Parsing failed — almost always a non-UOB or unexpected PDF layout.
            raise HTTPException(
                status_code=422,
                detail=f"Could not parse statement: {e}",
            )

        if not transactions:
            raise HTTPException(
                status_code=422, detail="No transactions found in PDF"
            )

        transactions = categorizer.categorize_transactions(transactions)

        # Persist (dedupe by content hash), then reload so the response carries
        # stored ids and any previously-confirmed offsets for this statement.
        statement_id = repository.save_statement(
            bank="UOB",
            period_start=period_start,
            period_end=period_end,
            pdf_bytes=contents,
            transactions=transactions,
        )
        stored = repository.get_statement_transactions(statement_id)
        agg = aggregate(stored)

        return AnalysisResult(
            id=statement_id,
            bank="UOB",
            period_start=period_start,
            period_end=period_end,
            transactions=stored,
            **agg,
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@app.post("/correct")
def correct(c: Correction):
    """Persist a manual category correction for a merchant.

    Writes to the categorizer cache, so future /analyze runs pick it up on the
    cache pass. Note the cascade is rules -> cache -> LLM: this beats the LLM
    and 'Other' fallback, but a rule-matched merchant still wins (see NOTES.md).
    """
    if c.category not in VALID_CATEGORIES:
        raise HTTPException(400, f"Unknown category: {c.category}")
    categorizer.cache.set_many({c.merchant: c.category})
    return {"ok": True}


@app.get("/statements", response_model=list[StatementSummary])
def list_statements():
    return repository.list_statements()


@app.get("/statements/{statement_id}", response_model=AnalysisResult)
def get_statement(statement_id: int):
    meta = repository.get_statement_meta(statement_id)
    if meta is None:
        raise HTTPException(404, "Statement not found")
    transactions = repository.get_statement_transactions(statement_id)
    agg = aggregate(transactions)
    return AnalysisResult(
        id=meta["id"],
        bank=meta["bank"],
        period_start=meta["period_start"],
        period_end=meta["period_end"],
        transactions=transactions,
        **agg,
    )


@app.get("/trends")
def trends():
    """{category: {"2026-03": 180.5, ...}} across all stored statements."""
    return category_trends()


@app.get(
    "/statements/{statement_id}/reimbursements",
    response_model=list[ReimbursementSuggestion],
)
def reimbursement_suggestions(statement_id: int):
    transactions = repository.get_statement_transactions(statement_id)
    if transactions is None:
        raise HTTPException(404, "Statement not found")
    return find_candidates(transactions)


@app.post("/offsets", response_model=OffsetResponse)
def create_offset(req: OffsetRequest):
    """Confirm a reimbursement: link an inbound transfer to a spend it offsets.

    The amount is capped so summed offsets never exceed the spend magnitude.
    """
    try:
        return repository.create_offset(
            req.transfer_tx_id, req.spend_tx_id, req.amount
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
