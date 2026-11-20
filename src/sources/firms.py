"""Sumber data titik panas NASA FIRMS (CSV). Implementasi pada Tahap 2."""

from __future__ import annotations

from src.sources.base import FetchResult

SOURCE_NAME = "firms"


def fetch() -> FetchResult:
    raise NotImplementedError("Implementasi FIRMS masuk Tahap 2")
