"""Konfigurasi global pipeline scraping."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

load_dotenv(PROJECT_ROOT / ".env")

# Bounding box Indonesia: west, south, east, north (derajat desimal).
INDONESIA_BBOX = (94.0, -11.0, 141.0, 6.0)

# Sumber FIRMS yang dipakai (VIIRS Suomi-NPP + MODIS, near real-time).
FIRMS_SOURCES = ("VIIRS_SNPP_NRT", "MODIS_NRT")
FIRMS_DAY_RANGE = 1

# Titik pantau cuaca dan kualitas udara (satu request Open-Meteo untuk semua titik).
LOCATIONS = (
    {"name": "Jakarta", "latitude": -6.2088, "longitude": 106.8456},
    {"name": "Surabaya", "latitude": -7.2575, "longitude": 112.7521},
    {"name": "Medan", "latitude": 3.5952, "longitude": 98.6722},
    {"name": "Balikpapan", "latitude": -1.2379, "longitude": 116.8529},
    {"name": "Jayapura", "latitude": -2.5916, "longitude": 140.6690},
)


def get_env(name: str, default: str | None = None) -> str | None:
    """Ambil environment variable, kembalikan default bila kosong."""
    value = os.getenv(name, default)
    if value is not None:
        value = value.strip()
    return value or default
