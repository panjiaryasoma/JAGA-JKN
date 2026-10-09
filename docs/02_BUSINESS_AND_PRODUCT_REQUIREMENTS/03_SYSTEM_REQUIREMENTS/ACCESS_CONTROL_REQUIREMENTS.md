---
project: JAGA-JKN
status: DRAFT
version: 0.2.0
owner: Panji
authority: Prototype Backend Contract
last_updated: 2026-10-09
---

# Kontrol akses backend prototipe

API baca snapshot sintetis, dashboard agregat, health, capability, dan status ML tersedia tanpa login untuk demo lokal. Semua endpoint kasus, event, intervensi, dan /me membutuhkan Authorization: Bearer.

Dua role demo: REVIEWER dan SUPERVISOR. Seluruh aktor demo berada pada satu workspace; belum ada multi-tenant atau pembagian wilayah. Matriks aksi mengacu CASE_LIFECYCLE_SPEC.md. Role/actor tidak diterima dari payload atau query.

Token dikonfigurasi melalui JAGA_REVIEWER_TOKEN dan JAGA_SUPERVISOR_TOKEN, minimum 32 karakter ASCII tanpa spasi, berbeda satu sama lain. ID aktor opsional melalui JAGA_REVIEWER_ID/JAGA_SUPERVISOR_ID, harus berbeda bila kedua token aktif. Token dibandingkan melalui digest SHA-256 dan constant-time compare; token tidak disimpan dalam database kasus, log, atau respons API. --demo menghasilkan token acak baru untuk sesi lokal dan menampilkannya sekali di terminal pengguna.

Token tidak tersedia → 503 AUTH_NOT_CONFIGURED pada endpoint terlindungi. Token hilang/salah → 401 dengan WWW-Authenticate: Bearer. Role tidak cukup → 403. Authorization header duplikat ditolak. Tidak ada default token tetap, token di query, session cookie, login/password, refresh token, atau klaim identitas petugas BPJS sebenarnya.

Server demo bind ke 127.0.0.1. CORS tidak dibuka otomatis. Deployment publik memerlukan IdP/auth produksi, TLS, manajemen secret/rotasi, pembatasan akses data, rate limiting, dan audit operasional tersendiri. Komponen ini final untuk lingkup demo yang dinyatakan, bukan autentikasi produksi.
