from pathlib import Path

import pytest
from fastapi.testclient import TestClient

FIXTURE = Path(__file__).parent / "fixtures" / "uob_sample.pdf"


@pytest.fixture
def client(monkeypatch):
    # Stub the API key so module import doesn't fail constructing the LLM client.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-testing")
    from backend import main

    # Replace the LLM with a deterministic stub so tests never hit the API.
    # Anything rules+cache can't categorize just becomes "Other" here.
    class StubLLM:
        def categorize_batch(self, merchants):
            return {m: "Other" for m in merchants}

    main.categorizer.llm = StubLLM()
    return TestClient(main.app)


def test_health(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.skipif(not FIXTURE.exists(), reason="local fixture only")
def test_analyze_returns_full_shape(client):
    with open(FIXTURE, "rb") as f:
        resp = client.post(
            "/analyze",
            files={"file": ("uob_sample.pdf", f, "application/pdf")},
        )
    assert resp.status_code == 200
    data = resp.json()

    # Top-level shape
    assert data["bank"] == "UOB"
    assert data["period_start"] == "2026-04-01"
    assert data["period_end"] == "2026-04-30"
    assert "total_spend" in data
    assert len(data["transactions"]) == 62
    assert len(data["by_category"]) > 0
    assert len(data["top_merchants"]) > 0

    # Every transaction has a category set (none left None)
    assert all(tx["category"] is not None for tx in data["transactions"])

    # Spend is positive and below total withdrawals (transfers excluded)
    assert 0 < data["total_spend"] < 1824.56


def test_rejects_non_pdf(client):
    resp = client.post(
        "/analyze",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 400


def test_rejects_unparseable_pdf(client):
    resp = client.post(
        "/analyze",
        files={"file": ("fake.pdf", b"not really a pdf", "application/pdf")},
    )
    assert resp.status_code == 422