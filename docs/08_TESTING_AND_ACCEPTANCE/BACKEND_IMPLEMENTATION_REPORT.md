---
project: JAGA-JKN
status: DRAFT
version: 0.2.0
owner: Panji
authority: Technical Verification Evidence
last_updated: 2026-10-09
---

# Backend prototype completion evidence

Lingkup BE-001..BE-019 sudah diimplementasikan untuk demo lokal dengan data sintetis. Status DRAFT merujuk penerimaan produk/domain pada governance, bukan placeholder kode. Laporan ini tidak menetapkan penerimaan bisnis, model ML, otoritas B1/B2, atau kesiapan produksi.

## Baseline dan kemampuan

Branch: `panji-backend-implementation`, basis merge main `8cf7428718539d378238da37355f8af1942e8379`. Source snapshot yang dideklarasikan: `9390d36a1adbef6f17aa6804dd6c56d290e06d04`; manifest hash/row-count ada di `config/backend_dataset_manifest.json`. Tidak ada perubahan generator, CSV sumber, model, atau kontrol governance tepercaya dalam implementasi ini.

- Read API: profil, pencarian/filter/pagination, riwayat dan bukti bulanan, metadata/provenance, agregat dashboard.
- Review: buka kasus, pemeriksaan, tunggu/resume bukti, intervensi/outcome, catatan, resolution/dismissal/reopen, manual recurrence.
- Persistence: SQLite schema v1, snapshot bukti per kasus, audit event, idempotency receipt, atomic transaction, strong ETag/version check.
- Operasional demo: Bearer token server-owned untuk reviewer/supervisor, launcher loopback, capabilities, health, OpenAPI, error/log tersanitasi, panduan backup/restore.

## Hasil verifikasi lokal

Runtime verifikasi: Python 3.12.14, SQLite 3.53.1, uv 0.12.23. Dependensi runtime/dev/synthetic direkam di `uv.lock`. Perintah dapat diulang dari `apps/api/README.md`.

| Pemeriksaan | Hasil |
|---|---|
| Backend pytest | 98 passed; 68 kontrak/validasi snapshot + 30 workflow/access/persistence |
| Real HTTP smoke | PASS; 17 pemeriksaan, 500 perusahaan, 12000 bukti, kasus sampai RESOLVED |
| Synthetic regressions yang sudah ada | 62 passed |
| Governance security regressions | 24 passed |
| Governance manifest validator | PASS; 213 entries |
| Ruff lint dan formatting backend/harness | PASS |

Smoke menjalankan subprocess server yang benar-benar menerima request HTTP loopback, bukan hanya TestClient. Token/DB sementara terpisah dari database demo pengguna. Smoke membuktikan protected endpoints, role denial, idempotency replay, intervensi/outcome, supervisor resolution, event versions, preservation of case evidence, dan OpenAPI. Backend tests menggunakan fixture kecil berbasis CSV sumber serta satu verifikasi full snapshot.

`.github/workflows/backend.yml` mengulang lint, format, backend tests, real HTTP smoke, 62 synthetic regressions, dan governance checks pada Python 3.12 dan 3.13. Workflow hanya memiliki contents:read dan tidak mendorong commit otomatis. Status remote harus dibaca dari run yang terikat commit terkait; laporan lokal ini tidak menggantikan hasil CI. JUnit diunggah sebagai artifact per Python version. [Workflow branch](https://github.com/panjiaryasoma/JAGA-JKN/actions/workflows/backend.yml?query=branch%3Apanji-backend-implementation).

## Bukti kegagalan dan perbaikan

Pengembangan dimulai dari consumer tests yang gagal sebelum modul API tersedia. Implementasi kemudian memenuhi kontrak. Pengujian tambahan menguji kegagalan nyata:

| Skenario | Perilaku terverifikasi |
|---|---|
| Hash/header/boolean/angka/JSON/enum/FK/grid tidak valid | Seluruh snapshot ditolak; 503 tanpa data kosong palsu |
| Token hilang/salah atau role dipalsukan | 401/403/422 sesuai kontrak; tidak ada privilege dari body |
| Dua update atas versi sama | Tepat satu berhasil; yang lain 412; event tidak ganda |
| Dua pembukaan kasus yang sama | Tepat satu kasus aktif; yang lain 409 |
| Write event dipaksa gagal dengan database trigger | Kasus/version/event/receipt rollback; retry dapat berhasil |
| Respons mutasi hilang lalu diulang | Respons asal dikembalikan; tidak menambah event |
| Dataset hilang setelah restart | Kasus lama dan snapshotnya tetap dapat dibaca; kasus baru 503 |
| Database dihapus setelah startup | Readiness dan workflow 503; tidak membuat DB kosong |
| Dua startup serentak | Inisialisasi schema diserialkan; WAL lock contention ditunggu terbatas |
| Timestamp dengan UTC di luar rentang kalender | 422, bukan error internal 500 |
| Intervensi milik kasus lain / outcome diulang | 404 / 409 tanpa perubahan state |
| Schema database versi tak dikenal | 503 tanpa reset versi/data |

Readiness untuk database hilang awalnya gagal diuji karena hanya memeriksa objek startup. Perbaikan menambah probe schema/koneksi dan membuka koneksi runtime dengan mode=rw. Normalisasi UTC ekstrem awalnya menghasilkan OverflowError; sekarang menjadi error validasi. Test startup serentak menemukan SQLITE_BUSY saat mengubah journal mode; retry hanya untuk lock contention dan dibatasi sebelum transaksi schema dimulai. Temuan tersebut menjadi regression tests.

Traceability rinci: `docs/07_TRACEABILITY_AND_CONTROL/TEST_TRACEABILITY.csv`. Hasil teknis tidak mengubah status manifest governance atau mengaktifkan policy registry.

## Batas yang masih terbuka

Dataset tetap sintetis untuk Januari 2025–Desember 2026, termasuk bulan simulasi di masa depan. Semua rule/review baseline ABSTAIN, ML NOT_CONFIGURED, policy UNRESOLVED. Review RESOLVED tidak mengubah arti bukti atau menyatakan pelanggaran/utang selesai secara hukum.

Integrasi model/artifact dari tim ML, fitur prediksi, automatic episode detection, kebijakan yang disahkan, IdP dan tenant isolation produksi, TLS/rate/body limits deployment publik, SLA/load testing, dan sistem eksternal belum termasuk hasil ini. Audit append-only berlaku melalui API; administrator SQLite tidak dianggap tidak dapat mengubah data. Dua role demo melayani satu workspace. Tidak ada pesan atau tindak lanjut nyata yang dikirim saat mencatat intervensi.

Langkah integrasi berikutnya adalah frontend memakai kontrak HTTP yang tersedia, lalu adapter model setelah artifact/version/feature contract diterima. Perubahan kebijakan/model membutuhkan kontrak dan uji baru; jangan menyamakan test backend yang lulus dengan pengesahan domain.
