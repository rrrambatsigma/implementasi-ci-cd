"""Sumber data cuaca Open-Meteo Weather API (JSON)."""

from __future__ import annotations

from pathlib import Path

from src.sources.open_meteo_client import fetch_hourly_series

API_URL = "https://api.open-meteo.com/v1/forecast"

HOURLY_VARIABLES = [
    "temperature_2m",
    "precipitation",
    "rain",
    "wind_speed_10m",
    "wind_direction_10m",
    "relative_humidity_2m",
]


def fetch_weather() -> Path:
    return fetch_hourly_series(
        api_url=API_URL,
        variables=HOURLY_VARIABLES,
        output_dir=Path("weather"),
        filename="weather.csv",
        label="WEATHER",
    )
