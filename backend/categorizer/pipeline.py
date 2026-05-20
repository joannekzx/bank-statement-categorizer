from backend.categorizer.engine import RulesEngine
from backend.categorizer.cache import CategoryCache
from backend.categorizer.llm_fallback import LLMCategorizer
from backend.models import Transaction


class Categorizer:
    """Orchestrates rules -> cache -> LLM in a three-pass cascade.

    Each pass only handles transactions the previous pass couldn't, so the
    expensive LLM call runs only for genuinely novel merchants. LLM results
    are cached so future runs skip the API for those merchants."""

    def __init__(
        self,
        rules: RulesEngine | None = None,
        cache: CategoryCache | None = None,
        llm: LLMCategorizer | None = None,
    ):
        # Dependencies are injectable so tests can pass fakes/mocks.
        self.rules = rules if rules is not None else RulesEngine()
        self.cache = cache if cache is not None else CategoryCache()
        self.llm = llm if llm is not None else LLMCategorizer()

    def categorize_transactions(
        self, transactions: list[Transaction]
    ) -> list[Transaction]:
        # Pass 1: rules
        unmatched: list[Transaction] = []
        for tx in transactions:
            category = self.rules.categorize(tx.merchant)
            if category:
                tx.category = category
            else:
                unmatched.append(tx)

        # Pass 2: cache (batched lookup)
        if unmatched:
            cached = self.cache.get_many([tx.merchant for tx in unmatched])
            still_unmatched: list[Transaction] = []
            for tx in unmatched:
                if tx.merchant in cached:
                    tx.category = cached[tx.merchant]
                else:
                    still_unmatched.append(tx)
            unmatched = still_unmatched

        # Pass 3: LLM (batched, deduplicated), then cache the results
        if unmatched:
            unique_merchants = list({tx.merchant for tx in unmatched})
            llm_results = self.llm.categorize_batch(unique_merchants)

            # Only cache confident results — never persist "Other", since that's
            # often a fallback from an API failure and should be retried later.
            to_cache = {m: c for m, c in llm_results.items() if c != "Other"}
            if to_cache:
                self.cache.set_many(to_cache)

            for tx in unmatched:
                tx.category = llm_results.get(tx.merchant, "Other")

        return transactions