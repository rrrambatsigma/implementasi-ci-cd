"""Utilitas penyimpanan: prefix path berbasis slot dan lokasi manifest."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from src.config import DATA_DIR
from src.utils.io import atomic_write_json


def get_run_slot(now: datetime | None = None) -> datetime:
    """Awal slot enam jam UTC untuk waktu tertentu."""
    now = now or datetime.now(UTC)

    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)

    now = now.astimezone(UTC)

    return now.replace(hour=(now.hour // 6) * 6, minute=0, second=0, microsecond=0)


def build_run_prefix(run_at: datetime | None = None) -> str:
    """Prefix path berbasis slot, contoh 2026/11/20/0600."""
    return get_run_slot(run_at).strftime("%Y/%m/%d/%H%M")


def get_run_slot_id(now: datetime | None = None) -> str:
    """ID slot enam jam UTC, contoh 20261120T060000Z."""
    return get_run_slot(now).strftime("%Y%m%dT%H%M%SZ")


def manifest_path() -> Path:
    return DATA_DIR / "manifest.json"


def write_manifest(payload: dict) -> Path:
    """Tulis manifest eksekusi ke data/manifest.json."""
    return atomic_write_json(payload, manifest_path())
