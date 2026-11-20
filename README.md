# Implementasi CI/CD Web Scraping dengan Azure dan GitHub Actions

Rambat Ungu Aryati / L0224010

Pipeline web scraping data kebakaran hutan, aktivitas gunung api, cuaca, dan
kualitas udara di Indonesia. Pipeline dijalankan otomatis oleh GitHub Actions
setiap 6 jam dan hasilnya disimpan di Azure Blob Storage.

## Sumber data

| Sumber | Data | Akses |
|---|---|---|
| NASA FIRMS | Titik panas (hotspot) MODIS dan VIIRS | REST API CSV, MAP_KEY |
| MAGMA Indonesia | Tingkat aktivitas dan laporan gunung api | Scraping HTML |
| Open-Meteo Air Quality | PM2.5, PM10, CO, NO2, SO2, O3, AQI | REST API JSON, tanpa key |
| Open-Meteo Weather | Suhu, hujan, angin, kelembapan | REST API JSON, tanpa key |

OpenWeatherMap Air Pollution API tidak dipakai pada implementasi ini; Open-Meteo
sudah mencakup seluruh variabel yang dibutuhkan.

## Struktur proyek

```
.github/workflows/   ci.yml dan pipeline.yml (Tahap 8)
data/                output lokal (tidak di-commit)
docs/screenshots/    bukti proses untuk laporan
scripts/             skrip provisioning Azure
src/
  main.py            orkestrator + manifest + exit code
  config.py          bbox, titik pantau, env
  sources/
    firms.py         NASA FIRMS (CSV)
    magma.py         MAGMA Indonesia (HTML)
    open_meteo_client.py  klien bersama Open-Meteo
    air_quality.py   kualitas udara
    weather.py       cuaca
  utils/
    io.py            penulisan CSV/JSON atomik
    http.py          session dengan retry
    ingestion_utils.py  upsert berbasis natural key
    storage.py       slot waktu + manifest
tests/               unit test tanpa jaringan (fixture HTML/CSV)
```

## Persiapan lokal

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env   # lalu isi FIRMS_MAP_KEY
```

Variabel environment yang dipakai:

| Nama | Default | Keterangan |
|---|---|---|
| `FIRMS_MAP_KEY` | — | wajib untuk NASA FIRMS |
| `FIRMS_DAY_RANGE` | 2 | jendela data FIRMS (1-5 hari) |
| `REQUEST_TIMEOUT` | 60 | timeout request (detik) |
| `FORECAST_DAYS` | 1 | jumlah hari forecast Open-Meteo |
| `MAGMA_REQUEST_DELAY` | 1 | jeda antar-request detail MAGMA (detik) |

## Menjalankan pipeline

```powershell
python -m src.main            # toleran: gagal bila semua sumber gagal
python -m src.main --strict   # gagal bila ada satu sumber gagal
```

Output lokal:

```
data/
  firms/latest_hotspots.csv
  magma/latest.json
  air_quality/latest_air_quality.csv
  weather/latest_weather.csv
  manifest.json
  <sumber>/history/<slot>_<file>     # snapshot slot enam jam UTC
```

Setiap record memakai waktu UTC: `observed_at_utc` untuk FIRMS dan
`valid_time_utc` untuk Open-Meteo. MAGMA menyimpan `last_updated` dalam ISO 8601
UTC.

## Validasi

```powershell
ruff check .
pytest
```

## Catatan implementasi

- **Idempotensi**: setiap sumber memakai natural key sehingga eksekusi ulang
  tidak menghasilkan duplikasi. Snapshot history dipisahkan per slot enam jam.
- **FIRMS**: CSV berisi header saja berarti tidak ada hotspot pada jendela
  tersebut, bukan kegagalan. Sensor VIIRS NRT dapat kosong sementara MODIS
  tersedia, sehingga keduanya dipakai bersama.
- **MAGMA**: 69 gunung api discrap dari tabel tingkat aktivitas, lalu detail
  laporan diambil satu per satu dengan jeda sopan dan retry untuk 429/5xx.
- **Toleransi kegagalan**: satu sumber gagal tidak menghentikan sumber lain;
  status per sumber dicatat di `data/manifest.json`.
- **GitHub Actions**: runner selalu mulai dari filesystem kosong. Akumulasi
  `latest_*` lintas run perlu mengunduh hasil sebelumnya dari Blob Storage
  terlebih dahulu (dibahas pada Tahap 8).

## Status pengerjaan

- [x] Tahap 1 — Persiapan lingkungan
- [x] Tahap 2 — Implementasi scraper Python
- [ ] Tahap 3 — Repository dan alur Git
- [ ] Tahap 4 — Azure Storage
- [ ] Tahap 5 — Microsoft Entra ID
- [ ] Tahap 6 — Federated credential dan RBAC
- [ ] Tahap 7 — GitHub Variables
- [ ] Tahap 8 — Workflow CI/CD
- [ ] Tahap 9 — Scheduler dan pengujian
- [ ] Tahap 10 — Dokumentasi PDF
