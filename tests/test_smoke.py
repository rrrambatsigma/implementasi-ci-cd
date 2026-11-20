"""Tes smoke untuk memastikan struktur proyek dan konfigurasi valid."""

from src.config import INDONESIA_BBOX, LOCATIONS


def test_bbox_mengandung_indonesia() -> None:
    west, south, east, north = INDONESIA_BBOX
    assert west < east
    assert south < north
    assert -180 <= west <= 180
    assert -90 <= south <= 90


def test_setiap_lokasi_punya_koordinat_valid() -> None:
    assert LOCATIONS
    for location in LOCATIONS:
        assert -90 <= location["latitude"] <= 90
        assert -180 <= location["longitude"] <= 180
