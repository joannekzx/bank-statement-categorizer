from abc import ABC, abstractmethod
from datetime import date
from backend.models import Transaction

class BaseParser(ABC):
    @abstractmethod
    def parse(self, pdf_path: str) -> list[Transaction]:
        ...

    @abstractmethod
    def detect_period(self, pdf_path: str) -> tuple[date, date]:
        ...

        