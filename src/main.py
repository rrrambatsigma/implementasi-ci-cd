"""Orkestrator pipeline scraping: FIRMS, MAGMA, kualitas udara, dan cuaca."""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
from datetime import UTC, datetime
from pathlib import Path

from src.sources.air_quality import fetch_air_quality
from src.sources.firms import fetch_firms
from src.sources.magma import fetch_magma
from src.sources.weather import fetch_weather
from src.utils.storage import build_run_prefix, write_manifest

LOGGER = logging.getLogger("pipeline")

TASKS = {
    "firms": ("NASA FIRMS", fetch_firms),
    "magma": ("MAGMA Indonesia", fetch_magma),
    "air_quality": ("Open-Meteo Air Quality", fetch_air_quality),
    "weather": ("Open-Meteo Weather", fetch_weather),
}


def _count_records(output: object) -> int | None:
    """Hitung jumlah record dari file hasil scraping (CSV atau JSON)."""
    if output is None:
        return 0

    path = Path(output)

    if not path.exists():
        return None

    if path.suffix == ".csv":
        with path.open(encoding="utf-8") as file:
            return max(sum(1 for _ in file) - 1, 0)

    if path.suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))

        if isinstance(payload, dict):
            return payload.get("metadata", {}).get("total_records")

        if isinstance(payload, list):
            return len(payload)

    return None


def _relative_output(output: object) -> str | None:
    """Ubah path output menjadi relatif terhadap working directory bila memungkinkan."""
    if output is None:
        return None

    path = Path(output)

    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def _github_context() -> dict[str, str | None]:
    """Metadata run GitHub Actions, None saat dijalankan lokal."""
    keys = {
        "repository": "GITHUB_REPOSITORY",
        "run_id": "GITHUB_RUN_ID",
        "run_attempt": "GITHUB_RUN_ATTEMPT",
        "sha": "GITHUB_SHA",
        "ref": "GITHUB_REF",
        "actor": "GITHUB_ACTOR",
    }

    return {name: os.getenv(env) for name, env in keys.items()}


def run_pipeline(strict: bool = False) -> int:
    """Jalankan semua sumber data, tulis manifest, dan kembalikan exit code."""
    started_at = datetime.now(UTC)
    results: dict[str, dict] = {}

    LOGGER.info("=" * 65)
    LOGGER.info("KARHUTLA INDONESIA - DATA INGESTION PIPELINE")
    LOGGER.info("=" * 65)

    for key, (label, task) in TASKS.items():
        LOGGER.info("Mulai: %s", label)
        started = time.perf_counter()

        try:
            output = task()
            status = "SUCCESS" if output is not None else "EMPTY"
            error_message = None
        except Exception as error:  # noqa: BLE001 - satu sumber gagal tidak menghentikan lainnya
            output = None
            status = "FAILED"
            error_message = f"{type(error).__name__}: {error}"
            LOGGER.exception("Gagal: %s", label)

        results[key] = {
            "label": label,
            "status": status,
            "records": _count_records(output),
            "output": _relative_output(output),
            "duration_seconds": round(time.perf_counter() - started, 2),
            "error": error_message,
        }

    success = sum(1 for item in results.values() if item["status"] in {"SUCCESS", "EMPTY"})
    failed = [key for key, item in results.items() if item["status"] == "FAILED"]

    manifest = {
        "run_slot": build_run_prefix(started_at),
        "generated_at": started_at.isoformat(),
        "duration_seconds": round((datetime.now(UTC) - started_at).total_seconds(), 2),
        "github": _github_context(),
        "summary": {
            "total_sources": len(results),
            "succeeded": success,
            "failed": len(failed),
        },
        "sources": results,
    }

    manifest_file = write_manifest(manifest)

    LOGGER.info("-" * 65)
    LOGGER.info("RINGKASAN PIPELINE")

    for item in results.values():
        LOGGER.info(
            "%-24s %-8s record=%-6s %.2fs",
            item["label"],
            item["status"],
            item["records"],
            item["duration_seconds"],
        )

    LOGGER.info("Manifest: %s", manifest_file)

    if failed:
        LOGGER.warning("Sumber gagal: %s", ", ".join(failed))

    if len(failed) == len(results):
        LOGGER.error("Semua sumber gagal. Pipeline dihentikan dengan exit code 1.")
        return 1

    if strict and failed:
        LOGGER.error("Mode strict aktif dan ada sumber gagal. Exit code 1.")
        return 1

    LOGGER.info("Pipeline selesai: %s/%s sumber berhasil.", success, len(results))

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pipeline scraping data karhutla Indonesia")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Keluar dengan kode 1 bila ada sumber yang gagal.",
    )
    parser.add_argument(
        "--log-level",
        default=os.getenv("LOG_LEVEL", "INFO"),
        help="Level logging (default: INFO).",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    )

    return run_pipeline(strict=args.strict)


if __name__ == "__main__":
    raise SystemExit(main())
