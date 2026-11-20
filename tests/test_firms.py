"""Tes parsing CSV NASA FIRMS tanpa memanggil jaringan."""

from src.sources.firms import KEY_COLUMNS, parse_firms_csv

SAMPLE_CSV = (
    "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,"
    "instrument,confidence,version,bright_ti5,frp,daynight\n"
    "-4.84028,121.70298,311.49,3.13,1.68,2026-11-20,54,Terra,MODIS,0,"
    "6.1NRT,293.42,40,D\n"
)


def test_csv_kosong_dikembalikan_sebagai_none() -> None:
    assert parse_firms_csv("", "MODIS_NRT") is None
    assert parse_firms_csv("   \n", "MODIS_NRT") is None


def test_csv_hanya_header_dikembalikan_sebagai_none() -> None:
    header = SAMPLE_CSV.splitlines()[0]

    assert parse_firms_csv(header, "MODIS_NRT") is None


def test_record_dinormalisasi_dengan_sensor_dan_waktu_utc() -> None:
    df = parse_firms_csv(SAMPLE_CSV, "MODIS_NRT")

    assert df is not None
    assert len(df) == 1

    row = df.iloc[0]

    assert row["source_sensor"] == "MODIS_NRT"
    assert row["observed_at_utc"] == "2026-11-20T00:54:00Z"
    assert all(column in df.columns for column in KEY_COLUMNS)
