"""Helper CD: validasi hasil scraping dan ringkasan GitHub Actions.

Dipakai oleh ``.github/workflows/ingestion.yml``:

    python scripts/cd_helpers.py validate --data-dir data
    python scripts/cd_helpers.py summary --manifest data/manifest.json ...

Hanya memakai standard library agar tidak menambah dependensi runtime.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

REQUIRED_SOURCES = ("firms", "magma", "air_quality", "weather")

REQUIRED_FILES = {
    "firms": Path("firms") / "latest_hotspots.csv",
    "magma": Path("magma") / "latest.json",
    "air_quality": Path("air_quality") / "latest_air_quality.csv",
    "weather": Path("weather") / "latest_weather.csv",
}

RUN_SLOT_PATTERN = re.compile(r"^\d{4}/\d{2}/\d{2}/\d{4}$")

STATUS_LABELS = {
    "success": "PASS",
    "failure": "FAIL",
    "cancelled": "CANCELLED",
    "skipped": "SKIPPED",
}

DEPLOYMENT_STAGES = (
    ("Scraping", "scrape"),
    ("Validasi manifest", "validate"),
    ("Autentikasi Azure", "login"),
    ("Staging", "stage"),
    ("Upload", "upload"),
    ("Verifikasi upload", "verify"),
)


def _status_label(value: str) -> str:
    return STATUS_LABELS.get(value, value or "SKIPPED")


def load_manifest(path: str | Path) -> dict:
    """Baca manifest JSON dan pastikan berbentuk objek."""
    manifest_path = Path(path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise ValueError("Manifest harus berupa objek JSON.")

    return payload


def _run_slot_problem(value: object) -> str | None:
    """Kembalikan pesan bila run_slot tidak sesuai format YYYY/MM/DD/HHMM."""
    if not isinstance(value, str) or not RUN_SLOT_PATTERN.fullmatch(value):
        return "run_slot harus tersedia dengan format YYYY/MM/DD/HHMM."

    try:
        datetime.strptime(value, "%Y/%m/%d/%H%M")
    except ValueError:
        return f"run_slot {value!r} bukan tanggal/jam yang valid."

    return None


def validate_output(data_dir: str | Path = "data") -> list[str]:
    """Kembalikan daftar masalah; list kosong berarti valid."""
    data_dir = Path(data_dir)
    manifest_path = data_dir / "manifest.json"

    if not manifest_path.is_file():
        return [f"Manifest tidak ditemukan: {manifest_path}"]

    try:
        manifest = load_manifest(manifest_path)
    except (json.JSONDecodeError, ValueError, OSError, UnicodeDecodeError) as error:
        return [f"Manifest tidak valid: {error}"]

    problems: list[str] = []

    slot_problem = _run_slot_problem(manifest.get("run_slot"))

    if slot_problem:
        problems.append(slot_problem)

    summary = manifest.get("summary")

    if not isinstance(summary, dict):
        problems.append("Bagian 'summary' manifest harus berupa objek.")
        summary = {}

    total_sources = summary.get("total_sources")

    if total_sources != len(REQUIRED_SOURCES):
        problems.append(
            "summary.total_sources harus "
            f"{len(REQUIRED_SOURCES)}, ditemukan {total_sources!r}."
        )

    succeeded = summary.get("succeeded")

    if succeeded != len(REQUIRED_SOURCES):
        problems.append(
            f"summary.succeeded harus {len(REQUIRED_SOURCES)}, ditemukan {succeeded!r}."
        )

    failed = summary.get("failed")

    if failed != 0:
        problems.append(f"summary.failed harus 0, ditemukan {failed!r}.")

    sources = manifest.get("sources")

    if not isinstance(sources, dict):
        problems.append("Bagian 'sources' pada manifest harus berupa objek.")
        sources = {}

    for key in REQUIRED_SOURCES:
        item = sources.get(key)

        if not isinstance(item, dict):
            problems.append(f"Sumber wajib '{key}' tidak ada di manifest.")
            continue

        status = item.get("status")

        if status != "SUCCESS":
            problems.append(f"Sumber '{key}' berstatus {status!r}, bukan SUCCESS.")

        records = item.get("records")

        if isinstance(records, bool) or not isinstance(records, int) or records <= 0:
            problems.append(
                f"Sumber '{key}' harus memiliki records berupa integer positif "
                f"(ditemukan {records!r})."
            )

        file_path = data_dir / REQUIRED_FILES[key]

        if not file_path.is_file():
            problems.append(f"File hasil untuk '{key}' tidak ditemukan: {file_path}")
        elif file_path.stat().st_size == 0:
            problems.append(f"File hasil untuk '{key}' kosong: {file_path}")

    return problems


def build_summary(
    manifest_path: str | Path,
    *,
    prefix: str = "",
    files_dir: str | Path = "build/blob",
    scrape: str = "skipped",
    validate: str = "skipped",
    login: str = "skipped",
    stage: str = "skipped",
    upload: str = "skipped",
    verify: str = "skipped",
    account: str = "",
    container: str = "",
) -> str:
    """Bangun Markdown ringkasan untuk $GITHUB_STEP_SUMMARY."""
    manifest: dict = {}
    manifest_ok = False

    try:
        manifest = load_manifest(manifest_path)
        sources = manifest.get("sources")
        manifest_ok = (
            isinstance(sources, dict)
            and all(
                isinstance(sources.get(key), dict) and sources[key].get("status") == "SUCCESS"
                for key in REQUIRED_SOURCES
            )
            and isinstance(manifest.get("summary"), dict)
            and _run_slot_problem(manifest.get("run_slot")) is None
        )
    except (OSError, json.JSONDecodeError, ValueError, UnicodeDecodeError):
        manifest = {}

    stage_values = {
        "scrape": scrape,
        "validate": validate,
        "login": login,
        "stage": stage,
        "upload": upload,
        "verify": verify,
    }

    failed_stages = [
        f"{label} ({_status_label(stage_values[key]).lower()})"
        for label, key in DEPLOYMENT_STAGES
        if stage_values[key] != "success"
    ]

    deployment_ok = manifest_ok and not failed_stages
    deployment_status = "PASS" if deployment_ok else "FAILED"

    lines: list[str] = ["### Continuous Deployment — Azure Blob Storage", ""]

    if not manifest:
        lines.append("> Manifest tidak tersedia atau tidak valid; ringkasan dibatasi.")
        lines.append("")

    lines.extend(
        [
            "| Item | Nilai |",
            "| --- | --- |",
            f"| **Status akhir deployment** | **{deployment_status}** |",
            f"| Run slot | {manifest.get('run_slot', '-')} |",
            f"| Storage account | {account or '(belum diset)'} |",
            f"| Blob container | {container or '(belum diset)'} |",
            f"| Prefix blob | {prefix or '-'} |",
        ]
    )

    for label, key in DEPLOYMENT_STAGES:
        lines.append(f"| {label} | {_status_label(stage_values[key])} |")

    lines.append("")

    if failed_stages:
        lines.append(f"**Tahap gagal:** {', '.join(failed_stages)}")
        lines.append("")

    sources = manifest.get("sources")

    if manifest_ok and isinstance(sources, dict):
        lines.extend(
            [
                "| Sumber | Status | Record | Durasi (detik) |",
                "| --- | --- | --- | --- |",
            ]
        )

        for key in REQUIRED_SOURCES:
            item = sources.get(key) or {}
            lines.append(
                "| {label} | {status} | {records} | {duration} |".format(
                    label=item.get("label", key),
                    status=item.get("status", "-"),
                    records=item.get("records", "-"),
                    duration=item.get("duration_seconds", "-"),
                )
            )

        summary = manifest.get("summary")
        summary = summary if isinstance(summary, dict) else {}
        succeeded = summary.get("succeeded", "-")
        failed = summary.get("failed", "-")

        lines.extend(["", f"**Total:** {succeeded} sumber berhasil, {failed} gagal.", ""])
    elif manifest:
        lines.extend(["Sumber: struktur manifest tidak valid.", ""])

    files: list[str] = []
    files_path = Path(files_dir)

    if files_path.is_dir():
        files = sorted(
            str(path.relative_to(files_path)).replace("\\", "/")
            for path in files_path.rglob("*")
            if path.is_file()
        )

    lines.append(f"**File di staging ({len(files)}):**")

    if files:
        lines.extend(f"- `{name}`" for name in files)
    else:
        lines.append("- (tidak ada file staging)")

    lines.append("")

    return "\n".join(lines)


def _command_validate(args: argparse.Namespace) -> int:
    problems = validate_output(args.data_dir)

    if problems:
        for problem in problems:
            print(f"ERROR: {problem}")
        return 1

    print("Validasi output: PASS (4 sumber wajib berhasil dan file tersedia).")
    return 0


def _command_summary(args: argparse.Namespace) -> int:
    print(
        build_summary(
            args.manifest,
            prefix=args.prefix,
            files_dir=args.files_dir,
            scrape=args.scrape,
            validate=args.validate,
            login=args.login,
            stage=args.stage,
            upload=args.upload,
            verify=args.verify,
            account=args.account,
            container=args.container,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Helper CD pipeline scraping")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validasi manifest dan file hasil")
    validate_parser.add_argument("--data-dir", default="data")
    validate_parser.set_defaults(func=_command_validate)

    summary_parser = subparsers.add_parser("summary", help="Tulis ringkasan Markdown")
    summary_parser.add_argument("--manifest", default="data/manifest.json")
    summary_parser.add_argument("--prefix", default="")
    summary_parser.add_argument("--files-dir", default="build/blob")
    summary_parser.add_argument("--scrape", default="skipped")
    summary_parser.add_argument("--validate", default="skipped")
    summary_parser.add_argument("--login", default="skipped")
    summary_parser.add_argument("--stage", default="skipped")
    summary_parser.add_argument("--upload", default="skipped")
    summary_parser.add_argument("--verify", default="skipped")
    summary_parser.add_argument("--account", default="")
    summary_parser.add_argument("--container", default="")
    summary_parser.set_defaults(func=_command_summary)

    args = parser.parse_args(argv)

    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
