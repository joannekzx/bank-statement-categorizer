import os
import tempfile

from dotenv import load_dotenv

load_dotenv()  # must run before importing modules that read env vars

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.parsers.uob import UOBParser
from backend.categorizer.pipeline import Categorizer
from backend.aggregator import aggregate
from backend.models import AnalysisResult

app = FastAPI(title="Bank Statement Categorizer")

# CORS so a local frontend (later) can call this API from the browser.
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
        agg = aggregate(transactions)

        return AnalysisResult(
            bank="UOB",
            period_start=period_start,
            period_end=period_end,
            transactions=transactions,
            **agg,
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)