import pytest

from backend.categorizer.engine import RulesEngine


@pytest.fixture
def engine():
    return RulesEngine()


def test_basic_matches(engine):
    assert engine.categorize("SHENG SIONG SUPERMARKE SINGAPORE SG") == "Groceries"
    assert engine.categorize("BUS/MRT 824198340 SINGAPORE SG") == "Transport"
    assert engine.categorize("Spotify P41D74396D Stockholm SE") == "Subscriptions"
    assert engine.categorize("TAOBAO 125 LONDON WAGB") == "Shopping"
    assert engine.categorize("Traveloka*1344849837 SINGAPORE SG") == "Travel"


def test_case_insensitive(engine):
    assert engine.categorize("starbucks reserve") == "Food"
    assert engine.categorize("STARBUCKS RESERVE") == "Food"


def test_specific_beats_generic(engine):
    # AWS should hit Subscriptions, not the more general AMAZON shopping rule
    assert engine.categorize("AMAZON WEB SERVICES SINGAPORE SG") == "Subscriptions"


def test_unmatched_returns_none(engine):
    assert engine.categorize("RANDOM MERCHANT XYZ") is None
    assert engine.categorize("john") is None  # person-name PayNow


def test_user_income(engine):
    assert engine.categorize("LEE HUAY LING (LI HU") == "Income"


def test_validation_catches_typos(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "categories: [Food, Other]\n"
        "rules:\n"
        "  - {pattern: TEST, category: Fod}\n"  # typo
    )
    with pytest.raises(ValueError, match="unknown category"):
        RulesEngine(rules_path=bad)