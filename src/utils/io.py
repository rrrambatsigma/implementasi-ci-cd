"""Penulisan file atomik yang dipakai bersama semua sumber data."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pandas as pd


def atomic_write_json(data: Any, output_path: str | Path) -> Path:
    """Tulis JSON lewat temporary file lalu ganti file tujuan secara atomik."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    temp_path = output_path.with_name(f"{output_path.name}.tmp")

    with temp_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.flush()
        os.fsync(file.fileno())

    os.replace(temp_path, output_path)

    return output_path


def atomic_write_csv(df: pd.DataFrame, output_path: str | Path) -> Path:
    """Tulis CSV lewat temporary file lalu ganti file tujuan secara atomik."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    temp_path = output_path.with_name(f"{output_path.name}.tmp")

    df.to_csv(temp_path, index=False)

    os.replace(temp_path, output_path)

    return output_path
