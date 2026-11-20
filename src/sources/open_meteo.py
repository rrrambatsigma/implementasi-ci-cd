"""Sumber data cuaca dan kualitas udara Open-Meteo (JSON). Tahap 2."""

from __future__ import annotations

from src.sources.base import FetchResult

SOURCE_NAME = "open_meteo"


def fetch_air_quality() -> FetchResult:
    raise NotImplementedError("Implementasi Open-Meteo Air Quality masuk Tahap 2")


def fetch_weather() -> FetchResult:
    raise NotImplementedError("Implementasi Open-Meteo Weather masuk Tahap 2")
