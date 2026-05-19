from pathlib import Path
from typing import Optional, Union

import yaml


DEFAULT_RULES_PATH = Path(__file__).parent / "rules.yaml"


class RulesEngine:
    def __init__(self, rules_path: Union[Path, str] = DEFAULT_RULES_PATH):
        with open(rules_path) as f:
            data = yaml.safe_load(f)
        self.rules = data["rules"]
        self.categories = data["categories"]
        self._validate()

    def _validate(self) -> None:
        """Fail loudly if YAML has a typo'd category name."""
        known = set(self.categories)
        for rule in self.rules:
            if rule["category"] not in known:
                raise ValueError(
                    f"Rule pattern {rule['pattern']!r} uses unknown category "
                    f"{rule['category']!r}. Known categories: {sorted(known)}"
                )

    def categorize(self, merchant: str) -> Optional[str]:
        """Return category name if any rule matches, else None.

        First-match-wins: rules are checked in YAML order. Matching is
        case-insensitive substring containment.
        """
        merchant_lower = merchant.lower()
        for rule in self.rules:
            if rule["pattern"].lower() in merchant_lower:
                return rule["category"]
        return None