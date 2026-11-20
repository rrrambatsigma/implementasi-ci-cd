"""Tes smoke untuk konfigurasi dasar pipeline."""

from src.config import INDONESIA_BBOX, MONITORING_POINTS


def test_bbox_indonesia_valid() -> None:
    parts = [float(value) for value in INDONESIA_BBOX.split(",")]

    assert len(parts) == 4

    west, south, east, north = parts

    assert west < east
    assert south < north
    assert -180 <= west <= 180
    assert -90 <= south <= 90


def test_setiap_lokasi_punya_koordinat_valid() -> None:
    assert MONITORING_POINTS

    for point in MONITORING_POINTS:
        assert point["province"]
        assert point["city"]
        assert -90 <= point["lat"] <= 90
        assert -180 <= point["lon"] <= 180
