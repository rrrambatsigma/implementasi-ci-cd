"""Sumber data aktivitas gunung api MAGMA (HTML). Implementasi pada Tahap 2."""

from __future__ import annotations

from src.sources.base import FetchResult

SOURCE_NAME = "magma"


def fetch() -> FetchResult:
    raise NotImplementedError("Implementasi MAGMA masuk Tahap 2")
