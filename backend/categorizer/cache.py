import sqlite3
from pathlib import Path
from typing import Optional, Union


DEFAULT_DB_PATH = Path("cache.db")


class CategoryCache:
    """SQLite-backed cache of merchant → category mappings.

    Merchant names are normalized (lowercased, stripped) before storage and
    lookup so that "SHENG SIONG" and "sheng siong " resolve to the same key.
    """

    def __init__(self, db_path: Union[Path, str] = DEFAULT_DB_PATH):
        self.db_path = str(db_path)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS merchant_categories (
                    merchant_normalized TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    @staticmethod
    def _normalize(merchant: str) -> str:
        return merchant.lower().strip()

    def get(self, merchant: str) -> Optional[str]:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT category FROM merchant_categories WHERE merchant_normalized = ?",
                (self._normalize(merchant),),
            ).fetchone()
            return row[0] if row else None

    def get_many(self, merchants: list[str]) -> dict[str, str]:
        """Look up multiple merchants. Returns {original_merchant: category}
        only for those found. Missing merchants are simply absent from the dict."""
        if not merchants:
            return {}
        normalized_to_original = {self._normalize(m): m for m in merchants}
        placeholders = ",".join("?" * len(normalized_to_original))
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                f"SELECT merchant_normalized, category FROM merchant_categories "
                f"WHERE merchant_normalized IN ({placeholders})",
                tuple(normalized_to_original.keys()),
            ).fetchall()
        return {
            normalized_to_original[norm]: cat
            for norm, cat in rows
            if norm in normalized_to_original
        }

    def set_many(self, merchant_to_category: dict[str, str]) -> None:
        if not merchant_to_category:
            return
        with sqlite3.connect(self.db_path) as conn:
            conn.executemany(
                "INSERT OR REPLACE INTO merchant_categories "
                "(merchant_normalized, category) VALUES (?, ?)",
                [(self._normalize(m), c) for m, c in merchant_to_category.items()],
            )