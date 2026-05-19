from datetime import date
from pathlib import Path

import pytest

from backend.parsers.uob import UOBParser

FIXTURE = Path(__file__).parent / "fixtures" / "uob_sample.pdf"


@pytest.fixture
def parser():
    return UOBParser()


@pytest.mark.skipif(not FIXTURE.exists(), reason="local fixture only")
def test_detect_period(parser):
    start, end = parser.detect_period(str(FIXTURE))
    assert start == date(2026, 4, 1)
    assert end == date(2026, 4, 30)


@pytest.mark.skipif(not FIXTURE.exists(), reason="local fixture only")
def test_parse_transaction_count(parser):
    txs = parser.parse(str(FIXTURE))
    assert len(txs) == 62


@pytest.mark.skipif(not FIXTURE.exists(), reason="local fixture only")
def test_parse_totals_match_statement(parser):
    """Withdrawals/deposits totals must match the PDF's 'Total' line exactly."""
    txs = parser.parse(str(FIXTURE))
    withdrawals = sum(tx.amount for tx in txs if tx.amount < 0)
    deposits = sum(tx.amount for tx in txs if tx.amount > 0)
    assert abs(withdrawals) == pytest.approx(1824.56, abs=0.01)
    assert deposits == pytest.approx(1181.20, abs=0.01)


@pytest.mark.skipif(not FIXTURE.exists(), reason="local fixture only")
def test_parse_first_transaction(parser):
    txs = parser.parse(str(FIXTURE))
    first = txs[0]
    assert first.date == date(2026, 4, 1)
    assert first.amount == pytest.approx(-4.80)
    assert "EIGHT STAR" in first.merchant