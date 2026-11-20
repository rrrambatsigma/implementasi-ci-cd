"""Sumber pembanding OpenWeatherMap Air Pollution API. Tahap 2 (opsional)."""

from __future__ import annotations

from src.sources.base import FetchResult

SOURCE_NAME = "openweather"


def fetch() -> FetchResult:
    raise NotImplementedError("Implementasi OpenWeatherMap masuk Tahap 2")
