"""Sumber data kualitas udara Open-Meteo Air Quality API (JSON)."""

from __future__ import annotations

from pathlib import Path

from src.sources.open_meteo_client import fetch_hourly_series

API_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

HOURLY_VARIABLES = [
    "pm2_5",
    "pm10",
    "carbon_monoxide",
    "nitrogen_dioxide",
    "sulphur_dioxide",
    "ozone",
    "european_aqi",
    "us_aqi",
]


def fetch_air_quality() -> Path:
    return fetch_hourly_series(
        api_url=API_URL,
        variables=HOURLY_VARIABLES,
        output_dir=Path("air_quality"),
        filename="air_quality.csv",
        label="AIR QUALITY",
    )
