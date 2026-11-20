"""Tes validator manifest dan ringkasan CD."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.cd_helpers import build_summary, validate_output

SOURCES = ("firms", "magma", "air_quality", "weather")

FILES = {
    "firms": "firms/latest_hotspots.csv",
    "magma": "magma/latest.json",
    "air_quality": "air_quality/latest_air_quality.csv",
    "weather": "weather/latest_weather.csv",
}


def _write_dataset(root: Path, *, failed_source: str | None = None) -> None:
    sources = {}

    for key in SOURCES:
        sources[key] = {
            "label": key.title(),
            "status": "FAILED" if key == failed_source else "SUCCESS",
            "records": 10,
            "duration_seconds": 1.0,
        }

        file_path = root / FILES[key]
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text("value\n1\n", encoding="utf-8")

    failed = 1 if failed_source else 0

    manifest = {
        "run_slot": "2026/11/20/0600",
        "summary": {
            "total_sources": len(SOURCES),
            "succeeded": len(SOURCES) - failed,
            "failed": failed,
        },
        "sources": sources,
    }

    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_valid_dataset_lolos(tmp_path: Path) -> None:
    _write_dataset(tmp_path)

    assert validate_output(tmp_path) == []


def test_sumber_gagal_ditolak(tmp_path: Path) -> None:
    _write_dataset(tmp_path, failed_source="magma")

    problems = validate_output(tmp_path)

    assert any("magma" in problem for problem in problems)


def test_file_hasil_hilang_ditolak(tmp_path: Path) -> None:
    _write_dataset(tmp_path)
    (tmp_path / FILES["weather"]).unlink()

    problems = validate_output(tmp_path)

    assert any("weather" in problem for problem in problems)


def test_record_nol_ditolak(tmp_path: Path) -> None:
    _write_dataset(tmp_path)

    manifest_path = tmp_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["sources"]["firms"]["records"] = 0
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    problems = validate_output(tmp_path)

    assert any("firms" in problem for problem in problems)


def test_manifest_tidak_ada_ditolak(tmp_path: Path) -> None:
    problems = validate_output(tmp_path)

    assert problems
    assert "Manifest" in problems[0]


def test_summary_menampilkan_status_dan_penyimpanan(tmp_path: Path) -> None:
    _write_dataset(tmp_path)

    summary = build_summary(
        tmp_path / "manifest.json",
        prefix="runs/2026/11/20/0600",
        files_dir=tmp_path,
        scrape="success",
        validate="success",
        login="success",
        stage="success",
        upload="success",
        verify="success",
        account="rrrambatsigmacicd",
        container="scraping-results",
    )

    assert "rrrambatsigmacicd" in summary
    assert "scraping-results" in summary
    assert "runs/2026/11/20/0600" in summary
    assert "**PASS**" in summary
    assert "firms/latest_hotspots.csv" in summary


def test_summary_tetap_jalan_tanpa_manifest(tmp_path: Path) -> None:
    summary = build_summary(
        tmp_path / "manifest.json",
        prefix="",
        files_dir=tmp_path,
        account="rrrambatsigmacicd",
        container="scraping-results",
    )

    assert "Manifest tidak tersedia" in summary
    assert "rrrambatsigmacicd" in summary
    assert "**FAILED**" in summary


def test_summary_failed_ketika_upload_gagal(tmp_path: Path) -> None:
    _write_dataset(tmp_path)

    summary = build_summary(
        tmp_path / "manifest.json",
        prefix="runs/2026/11/20/0600",
        files_dir=tmp_path,
        scrape="success",
        validate="success",
        login="success",
        stage="success",
        upload="failure",
        verify="skipped",
        account="rrrambatsigmacicd",
        container="scraping-results",
    )

    assert "**FAILED**" in summary
    assert "Tahap gagal:" in summary


def test_summary_failed_ketika_verifikasi_gagal(tmp_path: Path) -> None:
    _write_dataset(tmp_path)

    summary = build_summary(
        tmp_path / "manifest.json",
        prefix="runs/2026/11/20/0600",
        files_dir=tmp_path,
        scrape="success",
        validate="success",
        login="success",
        stage="success",
        upload="success",
        verify="failure",
        account="rrrambatsigmacicd",
        container="scraping-results",
    )

    assert "**FAILED**" in summary
    assert "Verifikasi upload (fail)" in summary


def test_summary_failed_ketika_tahap_tidak_dijalankan(tmp_path: Path) -> None:
    _write_dataset(tmp_path)

    summary = build_summary(
        tmp_path / "manifest.json",
        prefix="runs/2026/11/20/0600",
        files_dir=tmp_path,
        scrape="success",
        validate="success",
        login="skipped",
        stage="skipped",
        upload="skipped",
        verify="skipped",
        account="rrrambatsigmacicd",
        container="scraping-results",
    )

    assert "**FAILED**" in summary


def test_manifest_dengan_summary_bukan_dict(tmp_path: Path) -> None:
    _write_dataset(tmp_path)

    manifest_path = tmp_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["summary"] = ["tidak", "valid"]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    problems = validate_output(tmp_path)

    assert any("summary" in problem for problem in problems)
    assert not any("AttributeError" in problem for problem in problems)


def test_succeeded_tidak_sesuai_ditolak(tmp_path: Path) -> None:
    _write_dataset(tmp_path)

    manifest_path = tmp_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["summary"]["succeeded"] = 3
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    problems = validate_output(tmp_path)

    assert any("succeeded" in problem for problem in problems)


def test_failed_bukan_nol_ditolak(tmp_path: Path) -> None:
    _write_dataset(tmp_path)

    manifest_path = tmp_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["summary"]["failed"] = 1
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    problems = validate_output(tmp_path)

    assert any("failed" in problem for problem in problems)


def test_run_slot_tidak_valid_ditolak(tmp_path: Path) -> None:
    _write_dataset(tmp_path)

    manifest_path = tmp_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["run_slot"] = "2026-11-20 06:00"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    problems = validate_output(tmp_path)

    assert any("run_slot" in problem for problem in problems)


def test_records_boolean_ditolak(tmp_path: Path) -> None:
    _write_dataset(tmp_path)

    manifest_path = tmp_path / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["sources"]["firms"]["records"] = True
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    problems = validate_output(tmp_path)

    assert any("firms" in problem for problem in problems)


def test_file_output_kosong_ditolak(tmp_path: Path) -> None:
    _write_dataset(tmp_path)
    (tmp_path / FILES["air_quality"]).write_text("", encoding="utf-8")

    problems = validate_output(tmp_path)

    assert any("kosong" in problem for problem in problems)
