"""Tes kontrak workflow CI/CD tanpa menjalankan Actions."""

from __future__ import annotations

from pathlib import Path

import yaml

WORKFLOWS = Path(".github/workflows")
CD_FILE = WORKFLOWS / "ingestion.yml"
CI_FILE = WORKFLOWS / "ci.yml"

VARIABLES = (
    "AZURE_CLIENT_ID",
    "AZURE_TENANT_ID",
    "AZURE_SUBSCRIPTION_ID",
    "AZURE_STORAGE_ACCOUNT",
    "AZURE_STORAGE_CONTAINER",
)


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _triggers(document: dict) -> dict:
    # PyYAML 1.1 membaca key "on" sebagai boolean True.
    return document.get("on") or document.get(True)


def _steps(document: dict) -> list[dict]:
    return document["jobs"]["deploy"]["steps"]


def test_cd_trigger_manual_schedule_dan_push_main() -> None:
    triggers = _triggers(_load(CD_FILE))

    assert "workflow_dispatch" in triggers
    assert triggers["schedule"] == [{"cron": "0 */6 * * *"}]
    assert triggers["push"] == {"branches": ["main"]}


def test_cd_permission_oidc() -> None:
    document = _load(CD_FILE)

    assert document["permissions"]["contents"] == "read"
    assert document["permissions"]["id-token"] == "write"


def test_cd_login_memakai_variables_tanpa_secret() -> None:
    document = _load(CD_FILE)

    login = next(
        step for step in _steps(document) if str(step.get("uses", "")).startswith("azure/login")
    )

    assert login["uses"] == "azure/login@v2"
    assert login["with"] == {
        "client-id": "${{ vars.AZURE_CLIENT_ID }}",
        "tenant-id": "${{ vars.AZURE_TENANT_ID }}",
        "subscription-id": "${{ vars.AZURE_SUBSCRIPTION_ID }}",
    }
    assert "creds" not in login["with"]

    text = CD_FILE.read_text(encoding="utf-8")

    assert "AZURE_CLIENT_SECRET" not in text
    assert "account-key" not in text.lower()


def test_cd_memakai_variabel_dan_secret_yang_benar() -> None:
    text = CD_FILE.read_text(encoding="utf-8")

    for name in VARIABLES:
        assert f"vars.{name}" in text

    assert "secrets.FIRMS_API_KEY" in text
    assert "FIRMS_MAP_KEY" in text


def test_cd_menjalankan_scraper_strict_dan_upload_login() -> None:
    text = CD_FILE.read_text(encoding="utf-8")

    assert "python -m src.main --strict" in text
    assert "scripts/cd_helpers.py validate" in text
    assert "az storage blob upload-batch" in text
    assert "--auth-mode login" in text
    assert "--overwrite" in text

    document = _load(CD_FILE)
    upload = next(step for step in _steps(document) if step.get("id") == "upload")

    assert "shell" not in upload or upload["shell"] == "bash"


def test_ci_scraper_hanya_di_branch_dev() -> None:
    document = _load(CI_FILE)

    scrape_condition = document["jobs"]["scrape"]["if"]

    assert "refs/heads/dev" in scrape_condition
    assert "refs/heads/main" not in scrape_condition


def test_cd_guard_staging_dan_file_sensitif() -> None:
    text = CD_FILE.read_text(encoding="utf-8")

    assert "Staging kosong" in text

    for extension in (".p12", ".pfx", ".pem", ".key"):
        assert extension in text

    assert "File sensitif terdeteksi" in text


def test_cd_verifikasi_nama_dan_ukuran_blob() -> None:
    text = CD_FILE.read_text(encoding="utf-8")

    assert "properties.contentLength" in text
    assert "verify-blobs" in text
    assert '--prefix "${PREFIX}/"' in text
    assert '--prefix "$PREFIX"' in text


def test_cd_summary_menerima_status_semua_tahap() -> None:
    text = CD_FILE.read_text(encoding="utf-8")

    for step_id in ("scrape", "validate", "azure-login", "prepare", "upload", "verify"):
        assert f"steps.{step_id}.outcome" in text
