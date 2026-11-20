"""Utilitas upsert data scraping berbasis natural key."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.utils.io import atomic_write_csv
from src.utils.storage import get_run_slot_id


def upsert_csv(
    new_data: pd.DataFrame,
    output_dir: str | Path,
    filename: str,
    key_columns: list[str] | tuple[str, ...],
) -> tuple[Path, Path]:
    """Gabungkan data baru dengan data terbaru tanpa duplikasi natural key.

    Record dengan key sama akan diperbarui oleh data terbaru. Hasil disimpan
    sebagai ``latest_<filename>`` dan snapshot slot di ``history/``.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if new_data is None or new_data.empty:
        raise ValueError("Data baru kosong.")

    missing = set(key_columns) - set(new_data.columns)

    if missing:
        raise ValueError(f"Natural key tidak tersedia: {sorted(missing)}")

    latest_path = output_dir / f"latest_{filename}"

    if latest_path.exists():
        old_data = pd.read_csv(latest_path)
        combined = pd.concat([old_data, new_data], ignore_index=True)
    else:
        combined = new_data.copy()

    latest = (
        combined.drop_duplicates(subset=list(key_columns), keep="last")
        .sort_values(list(key_columns))
        .reset_index(drop=True)
    )

    atomic_write_csv(latest, latest_path)

    slot = get_run_slot_id()
    history_dir = output_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    history_path = history_dir / f"{slot}_{filename}"

    if history_path.exists():
        old_history = pd.read_csv(history_path)
        history = pd.concat([old_history, new_data], ignore_index=True)
    else:
        history = new_data.copy()

    history = (
        history.drop_duplicates(subset=list(key_columns), keep="last")
        .sort_values(list(key_columns))
        .reset_index(drop=True)
    )

    atomic_write_csv(history, history_path)

    return latest_path, history_path
