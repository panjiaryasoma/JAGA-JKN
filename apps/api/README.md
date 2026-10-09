# Backend JAGA-JKN

Backend prototipe lokal untuk snapshot sintetis dan workflow review manusia. Implementasi branch diselesaikan atas instruksi pemilik proyek; penerimaan bisnis pada dokumen governance tetap DRAFT. Tidak ada model terlatih atau kebijakan B1/B2 yang diaktifkan oleh backend.

## Menjalankan

Prasyarat: Python 3.12/3.13 dan uv 0.12.23. Seluruh perintah berikut dari root repository.

```bash
uv sync --locked
uv run --locked python -m apps.api --demo
```

Buka http://127.0.0.1:8000/docs atau http://127.0.0.1:8000/openapi.json. Launcher bind ke loopback; `--port 8001` tersedia bila port 8000 terpakai. `--demo` menghasilkan dua token acak, menggantikan token environment hanya untuk proses tersebut, dan menampilkannya sekali di terminal. Di Swagger, klik **Authorize**, masukkan token saja, lalu jalankan endpoint. Token berubah setiap restart `--demo`; kasus tetap tersimpan.

Untuk token stabil, export `JAGA_REVIEWER_TOKEN` dan `JAGA_SUPERVISOR_TOKEN` secara terpisah, lalu jalankan tanpa `--demo`. Generate masing-masing dengan `python -c 'import secrets; print(secrets.token_urlsafe(32))'`. Tidak ada token default. Tanpa konfigurasi token, API baca sintetis tetap berjalan; endpoint kasus dan `/me` menjawab 503 `AUTH_NOT_CONFIGURED`.

## Konfigurasi

| Environment | Default / aturan |
|---|---|
| JAGA_DATA_ROOT | `data/synthetic/curated`, relatif terhadap root repository secara default |
| JAGA_DATASET_MANIFEST | `config/backend_dataset_manifest.json` |
| JAGA_DB_PATH | `var/jaga-jkn.sqlite3`; direktori dibuat saat startup |
| JAGA_REVIEWER_TOKEN | Tidak ada; 32–256 karakter ASCII tanpa whitespace |
| JAGA_SUPERVISOR_TOKEN | Tidak ada; berbeda dari token reviewer |
| JAGA_REVIEWER_ID | `demo-reviewer`; pola `[a-z][a-z0-9_-]{2,63}` |
| JAGA_SUPERVISOR_ID | `demo-supervisor`; wajib berbeda bila kedua token aktif |

Path environment relatif dihitung dari working directory. `.env.example` hanya referensi; aplikasi tidak otomatis memuat `.env`. Actor ID adalah identitas audit demo, sehingga pergantian pemilik token harus memakai ID aktor baru. Seluruh aktor berbagi workspace prototipe yang sama.

## Alur demo / integrasi frontend

1. GET `/api/v1/capabilities` dan `/api/v1/dataset` untuk konteks kemampuan/snapshot.
2. GET `/api/v1/badan-usaha?q=BU-0001`, lalu `/api/v1/badan-usaha/BU-0001/evidence/2025-01`.
3. Reviewer POST `/api/v1/cases` untuk membuka review atas badan usaha-bulan.
4. Gunakan ETag respons sebagai If-Match pada setiap POST berikutnya: `START_REVIEW`, rencana intervensi, outcome, lalu supervisor `RESOLVE` atau `DISMISS`.
5. GET `/api/v1/cases/{case_id}/events` untuk riwayat aktor/versi. Case detail membawa salinan bukti awal.

Contoh request setelah menyimpan token terminal ke variabel shell `REVIEWER_TOKEN`:

```bash
curl --fail-with-body http://127.0.0.1:8000/api/v1/cases \
  -H "Authorization: Bearer ${REVIEWER_TOKEN}" \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: demo-open-0001' \
  -d '{"id_badan_usaha":"BU-0001","periode_bulan":"2025-01","reason":"Periksa mutu bukti sintetis."}'
```

Salin `data.case_id` ke `CASE_ID`. ETag awal adalah `"v1"`:

```bash
curl --fail-with-body "http://127.0.0.1:8000/api/v1/cases/${CASE_ID}/transitions" \
  -H "Authorization: Bearer ${REVIEWER_TOKEN}" \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: demo-start-0001' \
  -H 'If-Match: "v1"' \
  -d '{"action":"START_REVIEW","reason":"Mulai pemeriksaan demo."}'
```

Key harus baru untuk aksi baru, dan harus sama saat mengulang aksi yang responsnya hilang. Replay mengembalikan versi hasil asli; lakukan GET untuk versi terkini. Jika 412, muat ulang kasus, evaluasi ulang tindakan, lalu kirim dengan ETag terbaru dan key baru. 409 dapat menunjukkan kasus aktif sudah ada, konflik idempotency, transisi tidak sah, atau intervensi belum selesai.

Frontend menyimpan token dalam memory selama demo dan menggunakan development proxy `/api` ke `http://127.0.0.1:8000`. CORS tidak dibuka otomatis. Query/body yang tidak dikenal atau tipe salah ditolak. Detail field, envelope error, filter, dan lifecycle ada di [API_CONTRACT.md](../../docs/05_PREPRODUCTION/01_CONTRACTS_ACTIVE/API_CONTRACT.md).

## Verifikasi

```bash
uv sync --locked --group synthetic
uv run --no-sync pytest tests/backend -q
uv run --no-sync python scripts/smoke_backend.py
uv run --no-sync python -m unittest discover -s pipelines/synthetic -p 'test_*.py' -v
uv run --no-sync python scripts/validate_governance.py
uv run --no-sync python scripts/test_governance_security.py
uv run --no-sync ruff check apps/api packages/data/snapshot.py packages/data/case_store.py packages/domain tests/backend scripts/smoke_backend.py
uv run --no-sync ruff format --check apps/api packages/data/snapshot.py packages/data/case_store.py packages/domain tests/backend scripts/smoke_backend.py
```

Smoke harness membuka server HTTP sungguhan, memakai full snapshot, token sementara, dan database temporary tersendiri. Kasus demo pengguna tidak diubah. Backend CI memeriksa Python 3.12 dan 3.13 dengan lockfile yang sama; hasil pytest tersedia sebagai artifact workflow.

## Penyimpanan dan pemulihan

SQLite schema v1 memakai WAL, foreign keys, busy timeout, dan transaksi yang mengikat kasus/intervensi/event/idempotency receipt. Database lokal, journal, token, dan log tidak di-commit. Bila database gagal dibuka saat startup, workflow/readiness menjawab 503 sementara API snapshot masih dapat berjalan. Schema di luar versi 1 ditolak tanpa migrasi/destructive reset. Bila file database hilang setelah server menyala, request gagal tanpa membuat file kosong. Restart setelah memperbaiki path/file memuat kembali komponen; startup pada path baru memang membuat database baru.

Backup saat berjalan harus memakai SQLite online backup API, bukan hanya menyalin file utama saat WAL aktif. Contoh untuk database default (destination harus belum ada):

```bash
uv run --locked python - <<'PY'
import sqlite3
from pathlib import Path
source = Path('var/jaga-jkn.sqlite3').resolve()
target = Path('var/jaga-jkn-backup.sqlite3')
with target.open('xb'):
    pass
try:
    with sqlite3.connect(source.as_uri() + '?mode=ro', uri=True) as src:
        with sqlite3.connect(target) as dst:
            src.backup(dst)
except Exception:
    target.unlink(missing_ok=True)
    raise
PY
```

Untuk restore, hentikan proses dan arahkan `JAGA_DB_PATH` ke salinan backup yang diverifikasi, lalu startup dan periksa readiness/kasus. Simpan file asli sampai restore diverifikasi. Hasil backup tetap hanya data lokal; retensi dan backup luar host merupakan pekerjaan operasional berikutnya. Jangan menjalankan beberapa replika pada filesystem jaringan dengan SQLite.

Snapshot CSV dibaca dan divalidasi sekali saat startup. Perubahan byte tanpa pembaruan manifest yang disengaja menghasilkan 503; jangan mengganti hash hanya untuk mengabaikan data rusak. Hash SHA-256 mengikat byte dan dataset_id mengikat manifest; source_commit merupakan provenance yang dideklarasikan, bukan pemeriksaan Git online. Untuk snapshot baru, periksa kontrak, provenance, hash, jumlah baris, dan grid periode terlebih dahulu, lalu restart. Kasus lama tetap membawa snapshot pembukaannya.

## Batas penyelesaian

Selesai untuk demo sintetis: pembacaan bukti, workflow persisten, role demo, audit melalui API, konkurensi/idempotency, dashboard, health, dokumentasi, dan tes. Bulan Januari 2025–Desember 2026 adalah waktu simulasi. `ABSTAIN`, `null`, `UNKNOWN`, ML `NOT_CONFIGURED`, dan policy `UNRESOLVED` harus ditampilkan apa adanya.

Belum termasuk model terlatih/inferensi, legal-policy execution, automatic episode detection, integrasi BPJS, upload/pengiriman dokumen, pesan eksternal, IdP produksi, multi-tenant authorization, atau SLA produksi. Catatan intervensi tidak mengeksekusi tindak lanjut nyata. Audit append-only di API dapat diubah administrator database dan tidak diklaim tamper-proof. Launcher ini bukan panduan deployment publik; body/rate limit, TLS, dan penguatan operasional perlu ditetapkan sebelum deployment tersebut.
