"""Kontrak seragam untuk semua sumber data scraping."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class FetchResult:
    """Hasil satu sumber data dalam satu kali eksekusi."""

    source: str
    records: list[dict[str, Any]] = field(default_factory=list)
    fetched_at: str = ""
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


class Source(Protocol):
    """Setiap sumber data wajib punya atribut name dan method fetch()."""

    name: str

    def fetch(self) -> FetchResult: ...
