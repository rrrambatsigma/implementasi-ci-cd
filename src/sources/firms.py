"""Sumber data titik panas NASA FIRMS (CSV)."""

from __future__ import annotations

import logging
from io import StringIO

import pandas as pd
import requests

from src.config import (
    DATA_DIR,
    FIRMS_DAY_RANGE,
    FIRMS_MAP_KEY,
    FIRMS_SENSORS,
    INDONESIA_BBOX,
    REQUEST_TIMEOUT,
    USER_AGENT,
)
from src.utils.http import build_session
from src.utils.ingestion_utils import upsert_csv

LOGGER = logging.getLogger(__name__)

BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"

KEY_COLUMNS = (
    "source_sensor",
    "latitude",
    "longitude",
    "acq_date",
    "acq_time",
    "satellite",
    "instrument",
)


def parse_firms_csv(text: str, sensor: str) -> pd.DataFrame | None:
    """Ubah respons CSV FIRMS menjadi DataFrame, atau None bila kosong.

    FIRMS mengembalikan CSV berisi header saja ketika tidak ada hotspot, dan
    teks biasa ketika MAP_KEY tidak valid. Keduanya bukan kegagalan fatal.
    """
    if not text.strip():
        return None

    try:
        df = pd.read_csv(StringIO(text))
    except pd.errors.EmptyDataError:
        return None

    if df.empty or "latitude" not in df.columns:
        return None

    df["source_sensor"] = sensor

    # Jaga kompatibilitas bila FIRMS mengubah skema kolomnya.
    for column in KEY_COLUMNS:
        if column not in df.columns:
            df[column] = None

    # Turunkan waktu observasi UTC dari acq_date + acq_time (HHMM).
    acq_time = (
        df["acq_time"]
        .astype("string")
        .str.replace(r"\.0$", "", regex=True)
        .str.zfill(4)
    )

    df["observed_at_utc"] = pd.to_datetime(
        df["acq_date"].astype("string") + acq_time,
        format="%Y-%m-%d%H%M",
        utc=True,
        errors="coerce",
    ).dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    return df


def fetch_firms() -> object:
    """Ambil hotspot dari seluruh sensor FIRMS lalu simpan sebagai CSV."""
    if not FIRMS_MAP_KEY:
        raise ValueError("FIRMS_MAP_KEY belum tersedia di environment.")

    session = build_session(user_agent=USER_AGENT)

    frames: list[pd.DataFrame] = []
    empty_sensors: list[str] = []

    try:
        for sensor in FIRMS_SENSORS:
            url = (
                f"{BASE_URL}/{FIRMS_MAP_KEY}/"
                f"{sensor}/{INDONESIA_BBOX}/{FIRMS_DAY_RANGE}"
            )

            try:
                response = session.get(url, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
            except requests.RequestException as error:
                # Pesan sengaja tidak menyertakan URL karena berisi MAP_KEY.
                raise RuntimeError(
                    f"Gagal mengambil data FIRMS untuk sensor {sensor}."
                ) from error

            if "Invalid MAP_KEY" in response.text:
                raise ValueError("NASA FIRMS MAP_KEY tidak valid.")

            df = parse_firms_csv(response.text, sensor)

            if df is None:
                empty_sensors.append(sensor)
                LOGGER.info("FIRMS %s tidak mengembalikan hotspot.", sensor)
                continue

            frames.append(df)
            LOGGER.info("FIRMS %s: %s hotspot.", sensor, len(df))
    finally:
        session.close()

    if not frames:
        LOGGER.warning(
            "Tidak ada hotspot FIRMS dari %s sensor pada jendela %s hari.",
            len(FIRMS_SENSORS),
            FIRMS_DAY_RANGE,
        )
        return None

    result = pd.concat(frames, ignore_index=True)

    latest_path, history_path = upsert_csv(
        new_data=result,
        output_dir=DATA_DIR / "firms",
        filename="hotspots.csv",
        key_columns=list(KEY_COLUMNS),
    )

    LOGGER.info(
        "FIRMS total: %s hotspot (%s sensor kosong).",
        len(result),
        len(empty_sensors),
    )
    LOGGER.info("FIRMS latest: %s", latest_path)
    LOGGER.info("FIRMS history: %s", history_path)

    return latest_path
