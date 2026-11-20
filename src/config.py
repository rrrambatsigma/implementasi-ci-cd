"""Konfigurasi global pipeline scraping."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

load_dotenv(BASE_DIR / ".env")


def _env_int(name: str, default: int) -> int:
    """Baca environment variable sebagai int dengan fallback aman."""
    raw = os.getenv(name)

    if raw is None or not raw.strip():
        return default

    try:
        return int(raw)
    except ValueError:
        return default


FIRMS_MAP_KEY = os.getenv("FIRMS_MAP_KEY")
REQUEST_TIMEOUT = _env_int("REQUEST_TIMEOUT", 60)
FORECAST_DAYS = _env_int("FORECAST_DAYS", 1)
FIRMS_DAY_RANGE = _env_int("FIRMS_DAY_RANGE", 2)
MAGMA_REQUEST_DELAY = _env_int("MAGMA_REQUEST_DELAY", 1)

# Bounding box Indonesia: west, south, east, north (derajat desimal).
INDONESIA_BBOX = "94.5,-11.1,141.1,6.1"

# Sensor FIRMS yang dipakai. MODIS disertakan karena VIIRS NRT bisa kosong
# sementara MODIS tetap tersedia pada hari yang sama.
FIRMS_SENSORS = (
    "VIIRS_SNPP_NRT",
    "VIIRS_NOAA20_NRT",
    "VIIRS_NOAA21_NRT",
    "MODIS_NRT",
)

USER_AGENT = (
    "KarhutlaDataIngestion/1.0 "
    "(+https://github.com/rrrambatsigma/implementasi-ci-cd)"
)

# Koordinat representatif ibu kota provinsi (latitude, longitude).
MONITORING_POINTS = [
    {"province": "Aceh", "city": "Banda Aceh", "lat": 5.55, "lon": 95.32},
    {"province": "Sumatera Utara", "city": "Medan", "lat": 3.59, "lon": 98.67},
    {"province": "Sumatera Barat", "city": "Padang", "lat": -0.95, "lon": 100.35},
    {"province": "Riau", "city": "Pekanbaru", "lat": 0.51, "lon": 101.45},
    {"province": "Kepulauan Riau", "city": "Tanjung Pinang", "lat": 0.92, "lon": 104.45},
    {"province": "Jambi", "city": "Jambi", "lat": -1.61, "lon": 103.61},
    {"province": "Sumatera Selatan", "city": "Palembang", "lat": -2.99, "lon": 104.76},
    {"province": "Bengkulu", "city": "Bengkulu", "lat": -3.80, "lon": 102.26},
    {"province": "Lampung", "city": "Bandar Lampung", "lat": -5.43, "lon": 105.26},
    {
        "province": "Kepulauan Bangka Belitung",
        "city": "Pangkal Pinang",
        "lat": -2.13,
        "lon": 106.11,
    },
    {"province": "DKI Jakarta", "city": "Jakarta", "lat": -6.21, "lon": 106.85},
    {"province": "Banten", "city": "Serang", "lat": -6.12, "lon": 106.15},
    {"province": "Jawa Barat", "city": "Bandung", "lat": -6.91, "lon": 107.61},
    {"province": "Jawa Tengah", "city": "Semarang", "lat": -6.97, "lon": 110.42},
    {"province": "DI Yogyakarta", "city": "Yogyakarta", "lat": -7.80, "lon": 110.37},
    {"province": "Jawa Timur", "city": "Surabaya", "lat": -7.25, "lon": 112.75},
    {"province": "Bali", "city": "Denpasar", "lat": -8.65, "lon": 115.22},
    {"province": "Nusa Tenggara Barat", "city": "Mataram", "lat": -8.58, "lon": 116.10},
    {"province": "Nusa Tenggara Timur", "city": "Kupang", "lat": -10.17, "lon": 123.61},
    {"province": "Kalimantan Barat", "city": "Pontianak", "lat": -0.02, "lon": 109.34},
    {"province": "Kalimantan Tengah", "city": "Palangka Raya", "lat": -2.21, "lon": 113.92},
    {"province": "Kalimantan Selatan", "city": "Banjarbaru", "lat": -3.44, "lon": 114.83},
    {"province": "Kalimantan Timur", "city": "Samarinda", "lat": -0.50, "lon": 117.15},
    {"province": "Kalimantan Utara", "city": "Tanjung Selor", "lat": 2.84, "lon": 117.37},
    {"province": "Sulawesi Utara", "city": "Manado", "lat": 1.49, "lon": 124.85},
    {"province": "Gorontalo", "city": "Gorontalo", "lat": 0.54, "lon": 123.06},
    {"province": "Sulawesi Tengah", "city": "Palu", "lat": -0.89, "lon": 119.87},
    {"province": "Sulawesi Barat", "city": "Mamuju", "lat": -2.67, "lon": 118.89},
    {"province": "Sulawesi Selatan", "city": "Makassar", "lat": -5.14, "lon": 119.41},
    {"province": "Sulawesi Tenggara", "city": "Kendari", "lat": -3.99, "lon": 122.51},
    {"province": "Maluku", "city": "Ambon", "lat": -3.70, "lon": 128.18},
    {"province": "Maluku Utara", "city": "Sofifi", "lat": 0.73, "lon": 127.56},
    {"province": "Papua", "city": "Jayapura", "lat": -2.53, "lon": 140.72},
    {"province": "Papua Barat", "city": "Manokwari", "lat": -0.86, "lon": 134.06},
    {"province": "Papua Barat Daya", "city": "Sorong", "lat": -0.88, "lon": 131.25},
    {"province": "Papua Tengah", "city": "Nabire", "lat": -3.36, "lon": 135.50},
    {"province": "Papua Pegunungan", "city": "Wamena", "lat": -4.10, "lon": 138.95},
    {"province": "Papua Selatan", "city": "Merauke", "lat": -8.49, "lon": 140.40},
]
