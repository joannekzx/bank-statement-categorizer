import pytest

from backend.categorizer.cache import CategoryCache


@pytest.fixture
def cache(tmp_path):
    """Fresh cache backed by a tmp file — does not touch the real cache.db."""
    return CategoryCache(db_path=tmp_path / "test_cache.db")


def test_get_missing_returns_none(cache):
    assert cache.get("NEVER SEEN BEFORE") is None


def test_set_and_get_roundtrip(cache):
    cache.set_many({"SHENG SIONG": "Groceries"})
    assert cache.get("SHENG SIONG") == "Groceries"


def test_normalization(cache):
    cache.set_many({"SHENG SIONG": "Groceries"})
    assert cache.get("sheng siong") == "Groceries"
    assert cache.get("  Sheng Siong  ") == "Groceries"


def test_get_many(cache):
    cache.set_many({
        "SHENG SIONG": "Groceries",
        "GRAB": "Transport",
        "SPOTIFY": "Subscriptions",
    })
    result = cache.get_many(["SHENG SIONG", "GRAB", "UNKNOWN MERCHANT"])
    assert result == {"SHENG SIONG": "Groceries", "GRAB": "Transport"}


def test_get_many_empty(cache):
    assert cache.get_many([]) == {}


def test_overwrites_existing(cache):
    cache.set_many({"FOO": "Food"})
    cache.set_many({"FOO": "Shopping"})  # user corrected the category
    assert cache.get("FOO") == "Shopping"


def test_persists_across_instances(tmp_path):
    db = tmp_path / "persistent.db"
    cache1 = CategoryCache(db_path=db)
    cache1.set_many({"PERSIST ME": "Food"})

    cache2 = CategoryCache(db_path=db)
    assert cache2.get("PERSIST ME") == "Food"