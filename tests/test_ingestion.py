"""Tes upsert berbasis natural key dan penentuan slot waktu."""

from datetime import UTC, datetime

import pandas as pd

from src.utils.ingestion_utils import upsert_csv
from src.utils.storage import build_run_prefix, get_run_slot


def test_slot_enam_jam_utc() -> None:
    moment = datetime(2026, 11, 20, 14, 37, 12, tzinfo=UTC)

    assert get_run_slot(moment) == datetime(2026, 11, 20, 12, 0, 0, tzinfo=UTC)
    assert build_run_prefix(moment) == "2026/11/20/1200"


def test_upsert_memperbarui_record_dengan_key_sama(tmp_path) -> None:
    first = pd.DataFrame(
        [
            {"id": 1, "value": 10},
            {"id": 2, "value": 20},
        ]
    )

    latest_path, history_path = upsert_csv(
        new_data=first,
        output_dir=tmp_path / "firms",
        filename="hotspots.csv",
        key_columns=["id"],
    )

    second = pd.DataFrame(
        [
            {"id": 1, "value": 99},
            {"id": 3, "value": 30},
        ]
    )

    latest_path, history_path = upsert_csv(
        new_data=second,
        output_dir=tmp_path / "firms",
        filename="hotspots.csv",
        key_columns=["id"],
    )

    result = pd.read_csv(latest_path).set_index("id")

    assert len(result) == 3
    assert result.loc[1, "value"] == 99
    assert result.loc[2, "value"] == 20
    assert history_path.exists()


def test_upsert_menolak_key_yang_tidak_ada(tmp_path) -> None:
    df = pd.DataFrame([{"id": 1}])

    try:
        upsert_csv(df, tmp_path, "file.csv", key_columns=["missing"])
    except ValueError as error:
        assert "missing" in str(error)
    else:
        raise AssertionError("ValueError seharusnya dilempar")
