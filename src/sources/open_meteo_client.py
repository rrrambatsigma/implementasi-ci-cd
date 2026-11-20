"""Klien bersama Open-Meteo untuk data hourly (kualitas udara dan cuaca)."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import requests

from src.config import DATA_DIR, FORECAST_DAYS, MONITORING_POINTS, REQUEST_TIMEOUT, USER_AGENT
from src.utils.http import build_session
from src.utils.ingestion_utils import upsert_csv

LOGGER = logging.getLogger(__name__)


def fetch_hourly_series(
    api_url: str,
    variables: list[str],
    output_dir: Path,
    filename: str,
    label: str,
) -> Path:
    """Ambil satu seri hourly untuk semua titik pantau dalam satu request."""
    params = {
        "latitude": ",".join(str(point["lat"]) for point in MONITORING_POINTS),
        "longitude": ",".join(str(point["lon"]) for point in MONITORING_POINTS),
        "hourly": ",".join(variables),
        "forecast_days": FORECAST_DAYS,
        # Waktu disimpan dalam UTC agar sebanding dengan sumber lain.
        "timezone": "UTC",
    }

    session = build_session(user_agent=USER_AGENT)

    try:
        response = session.get(
            api_url,
            params=params,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        raise RuntimeError(f"Gagal mengambil data {label}.") from error
    finally:
        session.close()

    raw = response.json()

    if isinstance(raw, dict):
        raw = [raw]

    if len(raw) != len(MONITORING_POINTS):
        raise ValueError(
            f"Jumlah lokasi respons {label} ({len(raw)}) "
            f"tidak sama dengan jumlah titik pantau ({len(MONITORING_POINTS)})."
        )

    records: list[dict] = []

    for point, item in zip(MONITORING_POINTS, raw, strict=False):
        hourly = item.get("hourly") or {}
        times = hourly.get("time") or []

        if not times:
            continue

        for index, valid_time in enumerate(times):
            record = {
                "province": point["province"],
                "city": point["city"],
                "latitude": point["lat"],
                "longitude": point["lon"],
                "valid_time_utc": valid_time,
            }

            for variable in variables:
                values = hourly.get(variable) or []
                record[variable] = values[index] if index < len(values) else None

            records.append(record)

    if not records:
        raise ValueError(f"Data {label} kosong.")

    df = pd.DataFrame(records)
    df["valid_time_utc"] = pd.to_datetime(
        df["valid_time_utc"], utc=True
    ).dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    latest_path, history_path = upsert_csv(
        new_data=df,
        output_dir=DATA_DIR / output_dir,
        filename=filename,
        key_columns=["province", "valid_time_utc"],
    )

    LOGGER.info("%s record: %s", label, len(df))
    LOGGER.info("%s latest: %s", label, latest_path)
    LOGGER.info("%s history: %s", label, history_path)

    return latest_path
