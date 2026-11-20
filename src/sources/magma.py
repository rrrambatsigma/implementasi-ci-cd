
"""
MAGMA Indonesia Data Ingestion
--------------------------------
Source:
    https://magma.esdm.go.id/

Coverage:
    All volcanoes listed on the MAGMA activity-level page.

Features:
    - Extract volcano activity levels.
    - Extract individual volcano report links.
    - Scrape report details.
    - Normalize records into JSON.
    - Deterministic report IDs.
    - Idempotent upsert.
    - Atomic JSON writes.

Output:
    data/magma/latest.json
    data/magma/history/YYYYMMDDTHHMMSSZ.json
"""

import hashlib
import json
import logging
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup

from src.config import DATA_DIR, MAGMA_REQUEST_DELAY, REQUEST_TIMEOUT, USER_AGENT
from src.utils.http import build_session
from src.utils.io import atomic_write_json
from src.utils.storage import get_run_slot_id

# ============================================================
# CONFIGURATION
# ============================================================

BASE_URL = "https://magma.esdm.go.id"

ACTIVITY_URL = (
    f"{BASE_URL}/v1/gunung-api/tingkat-aktivitas"
)

OUTPUT_DIR = Path(DATA_DIR) / "magma"

LATEST_FILE = OUTPUT_DIR / "latest.json"

HISTORY_DIR = OUTPUT_DIR / "history"

HEADERS = {
    "Accept": "text/html,application/xhtml+xml",
}

LOGGER = logging.getLogger(__name__)


# ============================================================
# HTTP SESSION
# ============================================================

def create_session():
    """
    Membuat HTTP session untuk request ke MAGMA.
    """

    return build_session(
        user_agent=USER_AGENT,
        headers=HEADERS,
        retries=3,
        backoff_factor=0.5,
    )


def get_page(session, url):
    """
    Mengambil halaman HTML dengan validasi HTTP.
    """

    response = session.get(
        url,
        timeout=REQUEST_TIMEOUT
    )

    response.raise_for_status()

    if not response.text.strip():
        raise ValueError(
            f"Halaman MAGMA kosong: {url}"
        )

    return response.text


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def clean_text(value):
    """
    Membersihkan whitespace dari teks HTML.
    """

    if value is None:
        return None

    value = re.sub(
        r"\s+",
        " ",
        value
    ).strip()

    return value or None


def extract_report_id(url):
    """
    Mengambil ID laporan dari URL MAGMA.

    Contoh:
    /v1/gunung-api/laporan/214152?signature=...
    """

    match = re.search(
        r"/laporan/(\d+)",
        url
    )

    if match:
        return match.group(1)

    return None


def canonical_report_url(url):
    """
    Menghapus query signature dari URL untuk
    menghasilkan identitas URL yang stabil.
    """

    parsed = urlsplit(url)

    return urlunsplit((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        "",
        ""
    ))


def generate_report_id(report_url, content):
    """
    Menghasilkan ID deterministik.

    Prioritas:
    1. ID laporan dari URL.
    2. Hash URL canonical.
    3. Hash konten sebagai fallback.
    """

    report_id = extract_report_id(report_url)

    if report_id:
        return report_id

    if report_url:
        value = canonical_report_url(report_url)
    else:
        value = content

    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def get_element_text(parent, selector):
    """
    Mengambil teks dari elemen berdasarkan CSS selector.
    Mengembalikan None jika elemen tidak ditemukan.
    """

    element = parent.select_one(selector)

    if element is None:
        return None

    return clean_text(
        element.get_text(" ", strip=True)
    )


# ============================================================
# EXTRACT VOLCANO ACTIVITY LIST
# ============================================================

def extract_volcanoes(html):
    """
    Mengekstraksi seluruh gunung api dari tabel
    tingkat aktivitas MAGMA.

    Output:
        [
            {
                volcano_name,
                location,
                activity_level,
                report_url,
                report_id
            }
        ]
    """

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    table_container = soup.select_one(
        "div.table-responsive"
    )

    if table_container is None:
        raise ValueError(
            "Tabel tingkat aktivitas MAGMA tidak ditemukan. "
            "Kemungkinan struktur halaman berubah."
        )

    table_body = table_container.find("tbody")

    if table_body is None:
        raise ValueError(
            "Tbody tabel tingkat aktivitas tidak ditemukan."
        )

    volcanoes = []

    current_activity_level = None

    rows = table_body.find_all(
        "tr",
        recursive=True
    )

    for row in rows:

        # Heading kategori tingkat aktivitas.
        heading = row.select_one(
            "a.tx-inverse.tx-14.tx-medium.d-block"
        )

        if heading:
            current_activity_level = clean_text(
                heading.get_text(" ", strip=True)
            )

            continue

        if not current_activity_level:
            continue

        # Cari tautan detail laporan gunung api.
        link = row.find(
            "a",
            href=True
        )

        if link is None:
            continue

        report_url = urljoin(
            BASE_URL,
            link["href"]
        )

        if "/gunung-api/laporan/" not in report_url:
            continue

        # Informasi nama gunung dan lokasi.
        row_text = clean_text(
            row.get_text(" ", strip=True)
        )

        # Menghapus teks tombol "Lihat laporan".
        row_text = re.sub(
            r"Lihat laporan",
            "",
            row_text,
            flags=re.IGNORECASE
        ).strip()

        parts = row_text.split(" - ", 1)

        if len(parts) >= 2:
            volcano_name = clean_text(parts[0])
            location = clean_text(parts[1])
        else:
            volcano_name = clean_text(
                link.get_text(" ", strip=True)
            )
            location = None

        report_id = extract_report_id(report_url)

        if not volcano_name:
            LOGGER.warning(
                "Nama gunung tidak ditemukan: %s",
                report_url
            )
            continue

        volcanoes.append({
            "volcano_name": volcano_name,
            "location": location,
            "activity_level": current_activity_level,
            "report_url": report_url,
            "report_id": report_id,
        })

    if not volcanoes:
        raise ValueError(
            "Tidak ada gunung api yang berhasil diekstraksi. "
            "Periksa struktur HTML MAGMA."
        )

    # Deduplikasi daftar berdasarkan URL laporan.
    unique = {}

    for volcano in volcanoes:
        key = canonical_report_url(
            volcano["report_url"]
        )

        unique[key] = volcano

    return list(unique.values())


# ============================================================
# EXTRACT REPORT DETAILS
# ============================================================

def extract_report_detail(session, volcano):
    """
    Mengambil detail laporan individual.

    Field yang diekstraksi mengikuti struktur halaman
    detail laporan MAGMA yang diketahui.
    """

    report_url = volcano["report_url"]

    html = get_page(
        session,
        report_url
    )

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    container = soup.select_one(
        "div.col-lg-12"
    )

    if container is None:
        raise ValueError(
            f"Container laporan tidak ditemukan: {report_url}"
        )

    # Identitas laporan.
    title = get_element_text(
        container,
        "h5.card-title"
    )

    subtitle = get_element_text(
        container,
        "p.card-subtitle"
    )

    author = None

    if subtitle:
        parts = subtitle.split(", ", 1)

        if len(parts) > 1:
            author = clean_text(parts[1])

    # Informasi lokasi.
    location_detail = get_element_text(
        container,
        "p.col-lg-6.pd-0"
    )

    # Gambar laporan.
    image_element = container.select_one(
        "img.img-fluid"
    )

    image_url = None

    if image_element and image_element.get("src"):
        image_url = urljoin(
            BASE_URL,
            image_element["src"]
        )

    # Observasi visual.
    visual_observation = get_element_text(
        container,
        "div.media-body p"
    )

    # Deskripsi tambahan.
    other_description = get_element_text(
        container,
        "div.media.pd-30 p"
    )

    # Informasi klimatologi, seismik, rekomendasi.
    cards = container.select(
        "div.card.pd-30"
    )

    def card_text(index):

        if index >= len(cards):
            return None

        return clean_text(
            cards[index].get_text(
                " ",
                strip=True
            )
        )

    climatology = card_text(0)

    seismic_observation = card_text(1)

    recommendation = card_text(2)

    # Validasi minimal agar halaman error tidak
    # tersimpan sebagai laporan kosong.
    if not title and not visual_observation:
        raise ValueError(
            f"Isi laporan tidak berhasil diekstraksi: "
            f"{report_url}"
        )

    content_for_hash = json.dumps(
        {
            "title": title,
            "location": location_detail,
            "visual_observation": visual_observation,
            "climatology": climatology,
            "seismic_observation": seismic_observation,
            "recommendation": recommendation,
        },
        ensure_ascii=False,
        sort_keys=True
    )

    report_id = generate_report_id(
        report_url,
        content_for_hash
    )

    return {
        "report_id": report_id,
        "report_url": report_url,
        "report_url_canonical": canonical_report_url(
            report_url
        ),

        "volcano_name": volcano["volcano_name"],
        "location": volcano["location"],
        "activity_level": volcano["activity_level"],

        "title": title,
        "author": author,
        "location_detail": location_detail,

        "image_url": image_url,

        "visual_observation": visual_observation,
        "other_description": other_description,

        "climatology": climatology,
        "seismic_observation": seismic_observation,
        "recommendation": recommendation,

        "source": "MAGMA Indonesia - Badan Geologi",
        "source_url": report_url,
    }


# ============================================================
# IDEMPOTENT UPSERT
# ============================================================

def upsert_reports(new_records, output_path, failed_reports=None, activity_levels=None):
    """
    Upsert laporan berdasarkan report_id.

    Jika report_id sudah tersedia:
        Record diperbarui.

    Jika report_id belum tersedia:
        Record ditambahkan.

    Jika pipeline dijalankan ulang:
        Tidak menghasilkan duplikasi report_id.
    """

    output_path = Path(output_path)

    existing_records = []

    if output_path.exists():

        with open(
            output_path,
            encoding="utf-8"
        ) as file:

            existing_data = json.load(file)

        if isinstance(existing_data, dict):
            existing_records = existing_data.get(
                "records",
                []
            )

        elif isinstance(existing_data, list):
            existing_records = existing_data

    indexed_records = {}

    for record in existing_records:

        report_id = record.get("report_id")

        if report_id:
            indexed_records[str(report_id)] = record

    for record in new_records:

        report_id = record.get("report_id")

        if not report_id:
            raise ValueError(
                "Record MAGMA tidak memiliki report_id."
            )

        indexed_records[str(report_id)] = record

    merged_records = [
        indexed_records[key]
        for key in sorted(indexed_records)
    ]

    payload = {
        "metadata": {
            "source": "MAGMA Indonesia - Badan Geologi",
            "coverage": "Indonesia",
            "total_records": len(merged_records),
            "last_updated": datetime.now(UTC).isoformat(),
            "deduplication_key": "report_id",
            "last_run_successful": len(new_records),
            "last_run_failed": len(failed_reports or []),
            "activity_levels": activity_levels or {},
        },
        "records": merged_records,
    }

    atomic_write_json(
        payload,
        output_path
    )

    return output_path, len(merged_records)


# ============================================================
# MAIN SCRAPER
# ============================================================

def fetch_magma():
    """
    Main ingestion function.

    Pipeline:
        1. Fetch activity-level page.
        2. Extract all volcanoes.
        3. Fetch individual reports.
        4. Normalize report data.
        5. Upsert into latest.json.
        6. Save deterministic history snapshot.
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    HISTORY_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    session = create_session()

    LOGGER.info(
        "Starting MAGMA Indonesia ingestion..."
    )

    try:

        # ----------------------------------------------------
        # STEP 1: GET ACTIVITY PAGE
        # ----------------------------------------------------

        activity_html = get_page(
            session,
            ACTIVITY_URL
        )

        # ----------------------------------------------------
        # STEP 2: EXTRACT VOLCANO LIST
        # ----------------------------------------------------

        volcanoes = extract_volcanoes(
            activity_html
        )

        LOGGER.info(
            "Volcanoes discovered: %s",
            len(volcanoes)
        )

        # ----------------------------------------------------
        # STEP 3: EXTRACT INDIVIDUAL REPORTS
        # ----------------------------------------------------

        normalized_reports = []

        failed_reports = []

        for index, volcano in enumerate(
            volcanoes,
            start=1
        ):

            LOGGER.info(
                "[%s/%s] Scraping %s",
                index,
                len(volcanoes),
                volcano["volcano_name"]
            )

            try:

                report = extract_report_detail(
                    session,
                    volcano
                )

                normalized_reports.append(
                    report
                )

            except (
                requests.RequestException,
                ValueError,
                AttributeError,
                TypeError,
                IndexError
            ) as error:

                LOGGER.warning(
                    "Gagal mengambil laporan %s: %s",
                    volcano["volcano_name"],
                    error
                )

                failed_reports.append({
                    "volcano_name": volcano["volcano_name"],
                    "report_url": volcano["report_url"],
                    "error": str(error),
                })

            # Jeda sopan agar tidak membebani server MAGMA.
            if MAGMA_REQUEST_DELAY and index < len(volcanoes):

                time.sleep(MAGMA_REQUEST_DELAY)

    finally:

        session.close()

    # --------------------------------------------------------
    # STEP 4: VALIDATE SCRAPING RESULT
    # --------------------------------------------------------

    if not normalized_reports:

        raise RuntimeError(
            "Tidak ada laporan MAGMA yang berhasil "
            "diekstraksi. File output tidak diperbarui."
        )

    # --------------------------------------------------------
    # STEP 5: IDEMPOTENT UPSERT
    # --------------------------------------------------------

    activity_levels = {}

    for volcano in volcanoes:

        level = volcano["activity_level"] or "Unknown"

        activity_levels[level] = activity_levels.get(level, 0) + 1

    latest_path, total_records = upsert_reports(
        new_records=normalized_reports,
        output_path=LATEST_FILE,
        failed_reports=failed_reports,
        activity_levels=activity_levels,
    )

    # --------------------------------------------------------
    # STEP 6: HISTORICAL SNAPSHOT
    # --------------------------------------------------------

    now = datetime.now(UTC)

    slot = get_run_slot_id(now)

    history_path = HISTORY_DIR / (
        f"magma_{slot}.json"
    )

    # Snapshot slot menyimpan hasil observasi
    # yang berhasil diambil pada slot tersebut.
    history_payload = {
        "metadata": {
            "source": "MAGMA Indonesia - Badan Geologi",
            "collected_at": now.isoformat(),
            "run_slot": slot,
            "coverage": "Indonesia",
            "successful_reports": len(normalized_reports),
            "failed_reports": len(failed_reports),
        },
        "records": normalized_reports,
        "errors": failed_reports,
    }

    atomic_write_json(
        history_payload,
        history_path
    )

    # --------------------------------------------------------
    # STEP 7: EXECUTION SUMMARY
    # --------------------------------------------------------

    LOGGER.info("=" * 60)
    LOGGER.info("MAGMA INGESTION SUMMARY")
    LOGGER.info("=" * 60)

    LOGGER.info(
        "Volcanoes discovered : %s",
        len(volcanoes)
    )

    LOGGER.info(
        "Successful reports   : %s",
        len(normalized_reports)
    )

    LOGGER.info(
        "Failed reports       : %s",
        len(failed_reports)
    )

    LOGGER.info(
        "Total stored records : %s",
        total_records
    )

    LOGGER.info(
        "Latest output        : %s",
        latest_path
    )

    LOGGER.info(
        "History output       : %s",
        history_path
    )

    if failed_reports:
        LOGGER.warning(
            "Some reports could not be extracted. "
            "Check execution logs."
        )

    return latest_path


# ============================================================
# EXECUTION
# ============================================================

if __name__ == "__main__":

    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | "
            "%(levelname)s | "
            "%(name)s | "
            "%(message)s"
        )
    )

    fetch_magma()