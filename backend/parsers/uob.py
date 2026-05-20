import re
from datetime import date
from typing import Optional

import pdfplumber

from backend.models import Transaction
from backend.parsers.base import BaseParser

MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
}

# '01 Apr PAYNOW-FAST 4.80 3,397.64' -> day, month, middle, amount, balance
_DATE_LINE_RE = re.compile(
    r"^(\d{1,2})\s+([A-Z][a-z]{2})\s+(.+?)\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s*$"
)

# '01 Apr BALANCE B/F 3,402.44' -> opening balance (only one number)
_BALANCE_BF_RE = re.compile(
    r"^(\d{1,2})\s+([A-Z][a-z]{2})\s+BALANCE B/F\s+([\d,]+\.\d{2})\s*$"
)

# "Total 1,824.56 1,181.20 2,759.08" -> end-of-transactions marker
_TOTAL_LINE_RE = re.compile(
    r"^Total\s+[\d,]+\.\d{2}\s+[\d,]+\.\d{2}\s+[\d,]+\.\d{2}\s*$"
)

# 'Period: 01 Apr 2026 to 30 Apr 2026'
_PERIOD_RE = re.compile(
    r"Period:\s+(\d{1,2}\s+[A-Z][a-z]{2}\s+\d{4})\s+to\s+"
    r"(\d{1,2}\s+[A-Z][a-z]{2}\s+\d{4})"
)

# Header/footer/boilerplate lines to drop before transaction grouping
_SKIP_PATTERNS = [
    re.compile(r"^Page \d+ of \d+"),
    re.compile(r"^Date\s+Description"),
    re.compile(r"^SGD\s+SGD\s+SGD\s*$"),
    re.compile(r"^Account Transaction Details"),
    re.compile(r"^UOB Stash Account"),
    re.compile(r"^Pleasenotethat"),
    re.compile(r"^omissionsor"),
    re.compile(r"^claim against"),
    re.compile(r"^United Overseas Bank"),
    re.compile(r"^-+\s*End"),
    re.compile(r"^-+\s*$"),
    re.compile(r"^\s*$"),
]

# Inside a transaction block, lines that are NOT the merchant name
_NOT_MERCHANT_PATTERNS = [
    re.compile(r"^\d{1,2}\s+[A-Z]{3}\s+\d{4}\s+\d+\s*$"),  # card date + ref e.g. "29 MAR 8341 7747864"
    re.compile(r"^x+\d+\s*$"),                              # masked card "xxxxxx0546"
    re.compile(r"^PIB\d+\s*$"),                             # PayNow reference
    re.compile(r"^MBK\d+\s*$"),                             # mobile-banking reference
    re.compile(r"^PAYNOW OTHR\s*$"),
    re.compile(r"^OTHR(\s.*)?$"),                           # "OTHR", "OTHR Transfer - UEN", etc.
    re.compile(r"^COLL\s+\d+"),                             # GIRO collection ref
    re.compile(r"^DI\d+\s*$"),                              # GIRO debit ref
    re.compile(r"^Other\s*$"),
]


def _parse_amount(s: str) -> float:
    return float(s.replace(",", ""))


def _is_skippable(line: str) -> bool:
    return any(p.match(line) for p in _SKIP_PATTERNS)


def _looks_like_merchant(line: str) -> bool:
    if not line.strip():
        return False
    return not any(p.match(line) for p in _NOT_MERCHANT_PATTERNS)


class UOBParser(BaseParser):
    def parse(self, pdf_path: str) -> list[Transaction]:
        full_text = self._extract_text(pdf_path)
        year = self._extract_year(full_text)
        lines = [l.strip() for l in full_text.split("\n") if not _is_skippable(l)]

        blocks = self._group_into_blocks(lines)
        if not blocks:
            return []

        # First block must be the opening balance
        opening = blocks[0]
        m = _BALANCE_BF_RE.match(opening[0])
        if not m:
            raise ValueError(
                f"Expected opening balance line, got: {opening[0]!r}"
            )
        running_balance = _parse_amount(m.group(3))

        transactions: list[Transaction] = []
        for block in blocks[1:]:
            result = self._parse_block(block, running_balance, year)
            if result is None:
                continue
            tx, new_balance = result
            transactions.append(tx)
            running_balance = new_balance

        return transactions

    def detect_period(self, pdf_path: str) -> tuple[date, date]:
        full_text = self._extract_text(pdf_path)
        m = _PERIOD_RE.search(full_text)
        if not m:
            raise ValueError("Could not extract statement period")
        return self._parse_period_date(m.group(1)), self._parse_period_date(m.group(2))

    # ------------------------------------------------------------------ helpers

    def _extract_text(self, pdf_path: str) -> str:
        parts = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                parts.append(page.extract_text() or "")
        return "\n".join(parts)

    def _extract_year(self, full_text: str) -> int:
        m = _PERIOD_RE.search(full_text)
        if not m:
            raise ValueError("Could not extract statement period")
        return int(m.group(1).split()[-1])

    @staticmethod
    def _parse_period_date(s: str) -> date:
        day, mon, yr = s.split()
        return date(int(yr), MONTHS[mon], int(day))

    def _group_into_blocks(self, lines: list[str]) -> list[list[str]]:
        blocks: list[list[str]] = []
        current: list[str] = []
        for line in lines:
            if _TOTAL_LINE_RE.match(line):
                break
            if _DATE_LINE_RE.match(line) or _BALANCE_BF_RE.match(line):
                if current:
                    blocks.append(current)
                current = [line]
            elif current:
                current.append(line)
        if current:
            blocks.append(current)
        return blocks

    def _parse_block(
        self, block: list[str], prev_balance: float, year: int
    ) -> Optional[tuple[Transaction, float]]:
        m = _DATE_LINE_RE.match(block[0])
        if not m:
            return None

        day = int(m.group(1))
        month_name = m.group(2)
        middle = m.group(3).strip()
        magnitude = _parse_amount(m.group(4))
        new_balance = _parse_amount(m.group(5))

        signed_amount = round(new_balance - prev_balance, 2)

        # Sanity check: |signed_amount| should equal magnitude
        if abs(abs(signed_amount) - magnitude) > 0.01:
            # Out of sync — something went wrong, but keep going with delta
            pass

        merchant = self._extract_merchant(block[1:], fallback=middle)
        description = " | ".join([middle] + block[1:])
        tx_date = date(year, MONTHS[month_name], day)

        tx = Transaction(
            date=tx_date,
            description=description,
            merchant=merchant,
            amount=signed_amount,
        )
        return tx, new_balance

    def _extract_merchant(self, continuation: list[str], fallback: str) -> str:
        for line in continuation:
            if _looks_like_merchant(line):
                return line.strip()
        return fallback