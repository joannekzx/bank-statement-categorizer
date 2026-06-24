from pathlib import Path

import pytest
from fastapi.testclient import TestClient

FIXTURE = Path(__file__).parent / "fixtures" / "uob_sample.pdf"


@pytest.fixture
def client(monkeypatch, tmp_path):
    # Stub the API key so module import doesn't fail constructing the LLM client.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-testing")
    from backend import main
    from backend.categorizer.cache import CategoryCache

    # Replace the LLM with a deterministic stub so tests never hit the API.
    # Anything rules+cache can't categorize just becomes "Other" here.
    class StubLLM:
        def categorize_batch(self, merchants):
            return {m: "Other" for m in merchants}

    main.categorizer.llm = StubLLM()
    # Point the merchant cache at a throwaway DB so /correct tests don't touch
    # the real cache.db. (The ORM DB is already isolated by conftest.)
    main.categorizer.cache = CategoryCache(tmp_path / "cache.db")
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


def test_correct_persists_to_cache(client):
    from backend import main

    resp = client.post("/correct", json={"merchant": "MYSTERY CO", "category": "Food"})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    # The correction is written to the categorizer cache, so a future cache pass
    # picks it up before the LLM.
    assert main.categorizer.cache.get("MYSTERY CO") == "Food"


def test_correct_rejects_unknown_category(client):
    resp = client.post("/correct", json={"merchant": "X", "category": "Bogus"})
    assert resp.status_code == 400


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