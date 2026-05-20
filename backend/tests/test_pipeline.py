from datetime import date

import pytest

from backend.categorizer.pipeline import Categorizer
from backend.categorizer.cache import CategoryCache
from backend.models import Transaction


class FakeRules:
    """Matches only merchants containing 'SHENG SIONG'."""
    def categorize(self, merchant: str):
        return "Groceries" if "SHENG SIONG" in merchant else None


class FakeLLM:
    """Records what it was asked, returns canned answers."""
    def __init__(self, answers: dict[str, str]):
        self.answers = answers
        self.calls: list[list[str]] = []

    def categorize_batch(self, merchants: list[str]) -> dict[str, str]:
        self.calls.append(merchants)
        return {m: self.answers.get(m, "Other") for m in merchants}


def _tx(merchant: str) -> Transaction:
    return Transaction(
        date=date(2026, 4, 1), description=merchant, merchant=merchant, amount=-10.0
    )


@pytest.fixture
def cache(tmp_path):
    return CategoryCache(db_path=tmp_path / "pipeline_test.db")


def test_rules_pass_handles_known(cache):
    llm = FakeLLM({})
    cat = Categorizer(rules=FakeRules(), cache=cache, llm=llm)
    result = cat.categorize_transactions([_tx("SHENG SIONG SUPERMARKE")])
    assert result[0].category == "Groceries"
    assert llm.calls == []  # LLM never called for rule-matched tx


def test_llm_pass_handles_unknown(cache):
    llm = FakeLLM({"TAMMI CHIA": "Transfers"})
    cat = Categorizer(rules=FakeRules(), cache=cache, llm=llm)
    result = cat.categorize_transactions([_tx("TAMMI CHIA")])
    assert result[0].category == "Transfers"
    assert llm.calls == [["TAMMI CHIA"]]


def test_llm_results_get_cached(cache):
    llm = FakeLLM({"TAMMI CHIA": "Transfers"})
    cat = Categorizer(rules=FakeRules(), cache=cache, llm=llm)
    cat.categorize_transactions([_tx("TAMMI CHIA")])
    # Cache now knows TAMMI CHIA
    assert cache.get("TAMMI CHIA") == "Transfers"


def test_cache_pass_skips_llm_on_second_run(cache):
    llm = FakeLLM({"TAMMI CHIA": "Transfers"})
    cat = Categorizer(rules=FakeRules(), cache=cache, llm=llm)
    cat.categorize_transactions([_tx("TAMMI CHIA")])      # first run: hits LLM
    cat.categorize_transactions([_tx("TAMMI CHIA")])      # second run: hits cache
    assert llm.calls == [["TAMMI CHIA"]]  # LLM called exactly once, not twice


def test_other_is_not_cached(cache):
    llm = FakeLLM({})  # returns "Other" for everything
    cat = Categorizer(rules=FakeRules(), cache=cache, llm=llm)
    cat.categorize_transactions([_tx("MYSTERY MERCHANT")])
    assert cache.get("MYSTERY MERCHANT") is None  # not cached


def test_llm_deduplicates_merchants(cache):
    llm = FakeLLM({"BUS/MRT 123": "Transport"})
    cat = Categorizer(rules=FakeRules(), cache=cache, llm=llm)
    # Same merchant three times
    cat.categorize_transactions([_tx("BUS/MRT 123")] * 3)
    # LLM should have been asked for it only once
    assert len(llm.calls) == 1
    assert llm.calls[0].count("BUS/MRT 123") == 1