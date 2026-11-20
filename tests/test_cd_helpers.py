"""Tes validator manifest dan ringkasan CD."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.cd_helpers import (
    _prefix_problem,
    build_summary,
    collect_staging_files,
    compare_blob_listing,
    main,
    validate_output,
)

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


PREFIX = "runs/2026/11/20/0600"

STAGING_FILES = {
    "manifest.json": 10,
    "firms/latest_hotspots.csv": 20,
    "firms/history/20261120T060000Z_hotspots.csv": 20,
    "magma/latest.json": 30,
    "magma/history/magma_20261120T060000Z.json": 30,
    "air_quality/latest_air_quality.csv": 40,
    "air_quality/history/20261120T060000Z_air_quality.csv": 40,
    "weather/latest_weather.csv": 50,
    "weather/history/20261120T060000Z_weather.csv": 50,
}

DIRECTORY_PLACEHOLDERS = (
    "air_quality",
    "air_quality/history",
    "firms",
    "firms/history",
    "magma",
    "magma/history",
    "weather",
    "weather/history",
)


def _make_staging(root: Path) -> dict[str, int]:
    for name, size in STAGING_FILES.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x" * size)

    return dict(STAGING_FILES)


def _blob_entries(files: dict[str, int]) -> list[dict[str, object]]:
    return [
        {"name": f"{PREFIX}/{name}", "size": size}
        for name, size in files.items()
    ]


def test_verifikasi_sembilan_file_cocok(tmp_path: Path) -> None:
    expected = _make_staging(tmp_path)

    result = compare_blob_listing(expected, _blob_entries(expected), PREFIX)

    assert result.ok
    assert result.blob_files == 9
    assert result.ignored_directories == 0


def test_placeholder_direktori_tidak_menyebabkan_gagal(tmp_path: Path) -> None:
    expected = _make_staging(tmp_path)

    blobs = _blob_entries(expected) + [
        {"name": f"{PREFIX}/{name}", "size": 0}
        for name in DIRECTORY_PLACEHOLDERS
    ]

    result = compare_blob_listing(expected, blobs, PREFIX)

    assert result.ok
    assert result.blob_files == 9
    assert result.ignored_directories == len(DIRECTORY_PLACEHOLDERS)


def test_placeholder_trailing_slash_diabaikan(tmp_path: Path) -> None:
    expected = _make_staging(tmp_path)
    blobs = _blob_entries(expected) + [{"name": f"{PREFIX}/firms/", "size": 0}]

    result = compare_blob_listing(expected, blobs, PREFIX)

    assert result.ok
    assert result.ignored_directories == 1


def test_file_yang_hilang_ditolak(tmp_path: Path) -> None:
    expected = _make_staging(tmp_path)
    blobs = [
        blob
        for blob in _blob_entries(expected)
        if not str(blob["name"]).endswith("weather/latest_weather.csv")
    ]

    result = compare_blob_listing(expected, blobs, PREFIX)

    assert not result.ok
    assert "weather/latest_weather.csv" in result.missing
    assert result.extra == []


def test_blob_file_tambahan_ditolak(tmp_path: Path) -> None:
    expected = _make_staging(tmp_path)
    blobs = _blob_entries(expected) + [
        {"name": f"{PREFIX}/catatan-ekstra.csv", "size": 5}
    ]

    result = compare_blob_listing(expected, blobs, PREFIX)

    assert not result.ok
    assert "catatan-ekstra.csv" in result.extra


def test_ukuran_file_berbeda_ditolak(tmp_path: Path) -> None:
    expected = _make_staging(tmp_path)
    blobs = _blob_entries(expected)

    for blob in blobs:
        if str(blob["name"]).endswith("magma/latest.json"):
            blob["size"] = int(blob["size"]) + 1

    result = compare_blob_listing(expected, blobs, PREFIX)

    assert not result.ok
    assert "magma/latest.json" in result.mismatched


def test_blob_kosong_bukan_direktori_tetap_ditolak(tmp_path: Path) -> None:
    expected = _make_staging(tmp_path)
    blobs = _blob_entries(expected) + [
        {"name": f"{PREFIX}/catatan-kosong.txt", "size": 0}
    ]

    result = compare_blob_listing(expected, blobs, PREFIX)

    assert not result.ok
    assert "catatan-kosong.txt" in result.extra


def test_blob_di_prefix_lain_tidak_dihitung(tmp_path: Path) -> None:
    expected = _make_staging(tmp_path)
    blobs = _blob_entries(expected) + [
        {"name": "runs/2026/11/20/1200/lain.csv", "size": 7}
    ]

    result = compare_blob_listing(expected, blobs, PREFIX)

    assert result.ok
    assert result.blob_files == 9


def test_collect_staging_files_menghitung_sembilan_file(tmp_path: Path) -> None:
    _make_staging(tmp_path)

    files = collect_staging_files(tmp_path)

    assert len(files) == 9
    assert files["manifest.json"] == 10


def test_cli_verify_blobs_pass(tmp_path: Path, capsys) -> None:
    expected = _make_staging(tmp_path / "blob")
    listing = tmp_path / "listing.json"
    listing.write_text(
        json.dumps(_blob_entries(expected)),
        encoding="utf-8",
    )

    code = main(
        [
            "verify-blobs",
            "--staging",
            str(tmp_path / "blob"),
            "--prefix",
            PREFIX,
            "--input",
            str(listing),
        ]
    )

    captured = capsys.readouterr()

    assert code == 0
    assert "Verifikasi upload: PASS" in captured.out


def test_cli_verify_blobs_gagal_saat_file_hilang(tmp_path: Path, capsys) -> None:
    expected = _make_staging(tmp_path / "blob")
    blobs = _blob_entries(expected)[:-1]
    listing = tmp_path / "listing.json"
    listing.write_text(json.dumps(blobs), encoding="utf-8")

    code = main(
        [
            "verify-blobs",
            "--staging",
            str(tmp_path / "blob"),
            "--prefix",
            PREFIX,
            "--input",
            str(listing),
        ]
    )

    captured = capsys.readouterr()

    assert code == 1
    assert "File hilang di blob" in captured.out


def test_cli_verify_blobs_menolak_prefix_di_luar_runs(tmp_path: Path, capsys) -> None:
    expected = _make_staging(tmp_path / "blob")
    listing = tmp_path / "listing.json"
    listing.write_text(json.dumps(_blob_entries(expected)), encoding="utf-8")

    code = main(
        [
            "verify-blobs",
            "--staging",
            str(tmp_path / "blob"),
            "--prefix",
            "arsip/2026/11/20/0600",
            "--input",
            str(listing),
        ]
    )

    captured = capsys.readouterr()

    assert code == 1
    assert "runs/YYYY/MM/DD/HHMM" in captured.out


@pytest.mark.parametrize(
    "prefix",
    [
        "runs/2026/11/20/0600",
        "runs/2024/02/29/2359",
        "runs/2026/01/01/0000",
    ],
)
def test_prefix_verifikasi_valid(prefix: str) -> None:
    assert _prefix_problem(prefix) is None


@pytest.mark.parametrize(
    "prefix",
    [
        "runs/",
        "runs",
        "runs/sembarang",
        "runs/../../folder-lain",
        "runs/2026/02/30/0600",
        "runs/2026/13/01/0600",
        "runs/2026/11/20/2400",
        "runs/2026/11/20/0060",
        "runs/2026/11/20/060",
        "arsip/2026/11/20/0600",
    ],
)
def test_prefix_verifikasi_tidak_valid(prefix: str) -> None:
    assert _prefix_problem(prefix) is not None


def test_cli_verify_blobs_menolak_prefix_runs_tidak_lengkap(tmp_path: Path, capsys) -> None:
    expected = _make_staging(tmp_path / "blob")
    listing = tmp_path / "listing.json"
    listing.write_text(json.dumps(_blob_entries(expected)), encoding="utf-8")

    code = main(
        [
            "verify-blobs",
            "--staging",
            str(tmp_path / "blob"),
            "--prefix",
            "runs/sembarang",
            "--input",
            str(listing),
        ]
    )

    captured = capsys.readouterr()

    assert code == 1
    assert "prefix verifikasi tidak valid" in captured.out
