---
project: JAGA-JKN
status: DRAFT
version: 0.2.0
owner: Panji
authority: Prototype Backend Design
last_updated: 2026-10-09
---

# Arsitektur backend prototipe

Lingkup yang diimplementasikan: pembacaan snapshot sintetis dan workflow review lokal. Penerimaan produk tetap DRAFT. Komponen ML dan otoritas kebijakan tidak diklaim tersedia.

| Lapisan | Modul | Tanggung jawab |
|---|---|---|
| Bootstrap | apps/api/config.py, __main__.py | Konfigurasi proses, path tepercaya, token demo, loopback server |
| HTTP | apps/api/main.py, workflow.py, schemas.py | Validasi request, envelope, health, pagination, API workflow, request ID dan log tersanitasi |
| Akses | apps/api/auth.py | Digest token, aktor server-owned, Bearer dependency |
| Domain | packages/domain/read_models.py, cases.py | Whitelist bukti, tipe ketat, state machine, role, reason/datetime validation |
| Snapshot | packages/data/snapshot.py | Bounded read, hash manifest, CSV validation, index immutable |
| Persistence | packages/data/case_store.py | Schema version, transaksi SQLite, audit dan receipt, optimistic concurrency |

Startup memvalidasi konfigurasi token, memuat snapshot, kemudian menginisialisasi database. Dataset dan database gagal secara independen: liveness tetap hidup, readiness melaporkan komponen gagal; pembacaan kasus lama tidak memerlukan dataset aktif. HTTP tidak dapat menentukan path/file sumber.

Snapshot valid dimuat sekali per worker. Data 500 × 24 diindeks berdasarkan ID dan badan usaha-bulan; filter dijalankan sebelum pagination. Profil dibuat dari whitelist eksplisit. Bukti mempertahankan abstention, provenance, mutu, dan missingness. Loader tidak menghitung ulang aturan sumber atau mengakses internet.

Untuk mutasi, autentikasi menentukan aktor; schema memvalidasi body/header. Adapter menghitung fingerprint kanonis method/path/payload/If-Match. Store memeriksa wewenang supervisor, membuka BEGIN IMMEDIATE, menangani replay/conflict, memvalidasi versi dan state, lalu menulis data/event/receipt dalam transaksi sama. Respons berisi versi hasil, ETag, dan event ID. Rollback mencegah event atau receipt parsial.

Kasus menyimpan salinan bukti yang dipakai saat dibuka. Penutupan review tidak mengubah rule_result ABSTAIN. Recurrence adalah link eksplisit manusia, tidak menghasilkan label model. Dashboard hanya mengagregasi observasi/mutu/abstention satu bulan.

SQLite pada satu host dipilih agar demo reproducible tanpa provisioning database eksternal. Startup bersamaan menyerialkan keputusan versi schema; koneksi runtime tidak membuat file baru bila database hilang. Jalur skala berikutnya adalah repository adapter ke database server dengan migrasi yang ditinjau, bukan berbagi SQLite lintas host.

Kontrak HTTP: API_CONTRACT.md. State machine: CASE_LIFECYCLE_SPEC.md. Detail tabel: DATABASE_DESIGN.md. Pengujian dan batas penerimaan: docs/08_TESTING_AND_ACCEPTANCE/BACKEND_IMPLEMENTATION_REPORT.md. Ini desain implementasi branch yang diizinkan pemilik proyek, tanpa mengubah status freeze pada manifest governance.
