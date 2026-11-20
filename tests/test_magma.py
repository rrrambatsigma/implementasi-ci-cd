"""Tes parser MAGMA memakai fixture HTML asli (tanpa jaringan)."""

from pathlib import Path

from src.sources.magma import extract_report_detail, extract_volcanoes

FIXTURES = Path(__file__).parent / "fixtures"

REPORT_ID = "331210"

VOLCANO = {
    "volcano_name": "Anak Krakatau",
    "location": "Lampung",
    "activity_level": "Level III (Siaga)",
    "report_url": f"https://magma.esdm.go.id/v1/gunung-api/laporan/{REPORT_ID}",
    "report_id": REPORT_ID,
}


class FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        return None


class FakeSession:
    def __init__(self, text: str) -> None:
        self.text = text

    def get(self, url: str, timeout: int | None = None) -> FakeResponse:
        return FakeResponse(self.text)


def test_extract_volcanoes_dari_halaman_aktivitas() -> None:
    html = (FIXTURES / "magma_activity.html").read_text(encoding="utf-8")

    volcanoes = extract_volcanoes(html)

    assert len(volcanoes) >= 30

    names = {volcano["volcano_name"] for volcano in volcanoes}

    assert "Merapi" in names
    assert "Semeru" in names

    for volcano in volcanoes:
        assert volcano["activity_level"].startswith("Level ")
        assert volcano["report_url"].startswith("https://magma.esdm.go.id/")

    # Tidak ada duplikasi berdasarkan URL canonical.
    canonical_urls = {volcano["report_url"].split("?")[0] for volcano in volcanoes}

    assert len(canonical_urls) == len(volcanoes)


def test_extract_report_detail_mengisi_field_utama() -> None:
    html = (FIXTURES / "magma_report.html").read_text(encoding="utf-8")

    report = extract_report_detail(FakeSession(html), VOLCANO)

    assert report["report_id"] == REPORT_ID
    assert report["volcano_name"] == "Anak Krakatau"
    assert report["title"]
    assert report["visual_observation"]
    assert report["report_url_canonical"].endswith(f"/laporan/{REPORT_ID}")
