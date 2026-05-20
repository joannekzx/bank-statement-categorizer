import json
import os
import re
from anthropic import Anthropic, APIError


VALID_CATEGORIES = {
    "Food", "Groceries", "Transport", "Shopping", "Subscriptions",
    "Bills & Utilities", "Health", "Entertainment", "Travel",
    "Investments", "Transfers", "Income", "Other",
}

SYSTEM_PROMPT = """You are a transaction categorizer for a Singapore-based \
personal finance tool. Categorize each merchant into exactly one of these \
categories:

Food, Groceries, Transport, Shopping, Subscriptions, Bills & Utilities, \
Health, Entertainment, Travel, Investments, Transfers, Income, Other

Guidance for Singapore context:
- Hawker stalls, food courts, cafes, restaurants -> Food
- Supermarkets (NTUC, Sheng Siong, Cold Storage) -> Groceries
- BUS/MRT, Grab, Gojek, EZ-Link -> Transport
- PayNow / bank transfers to a PERSON'S NAME -> Transfers
- PayNow to a company/UEN for goods or services -> categorize by what they sell
- Robo-advisors and brokerages (Syfe, Endowus, Tiger) -> Investments
- Salary, interest, refunds, incoming payments for services -> Income
- If genuinely unclear -> Other

Return ONLY valid JSON mapping each merchant to its category. No markdown, \
no explanation, no code fences. Format: {"merchant name": "Category", ...}
Use the merchant strings EXACTLY as given as the JSON keys."""


class LLMCategorizer:
    def __init__(self, model: str = "claude-haiku-4-5"):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY not set. Add it to your .env file."
            )
        self.client = Anthropic(api_key=api_key)
        self.model = model

    def categorize_batch(self, merchants: list[str]) -> dict[str, str]:
        """Categorize merchant strings. Returns a complete {merchant: category}
        mapping; anything the model omits, mis-categorizes, or any API failure
        falls back to 'Other'."""
        if not merchants:
            return {}

        user_prompt = (
            f"Categorize these {len(merchants)} merchants:\n"
            f"{json.dumps(merchants, ensure_ascii=False)}"
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            raw = self._extract_text(response)
            parsed = self._parse_json(raw)
        except APIError as e:
            print(f"LLM API unavailable ({e}); categorizing batch as Other")
            parsed = {}

        result: dict[str, str] = {}
        for merchant in merchants:
            category = parsed.get(merchant)
            if category not in VALID_CATEGORIES:
                category = "Other"
            result[merchant] = category
        return result

    @staticmethod
    def _extract_text(response) -> str:
        return "".join(
            block.text for block in response.content
            if getattr(block, "type", None) == "text"
        ).strip()

    @staticmethod
    def _parse_json(text: str) -> dict:
        """Extract a JSON object from the model's text, tolerating markdown
        code fences or surrounding prose by grabbing the first {...} block."""
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return {}
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}