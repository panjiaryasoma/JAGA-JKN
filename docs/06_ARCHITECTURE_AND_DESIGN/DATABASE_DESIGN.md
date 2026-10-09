---
project: JAGA-JKN
status: DRAFT
version: 0.2.0
owner: Panji
authority: Prototype Backend Design
last_updated: 2026-10-09
---

# Database workflow prototipe

Implementasi: SQLite, PRAGMA user_version=1, WAL, foreign_keys=ON, busy_timeout=5000. DDL sumber berada di packages/data/case_store.py. Schema baru dibuat atomik; versi selain 0/1 ditolak dan tidak direset. Schema 0 hanya menerima pembuatan tabel baru, bukan migrasi tabel tak dikenal. Setiap mutasi memakai transaksi BEGIN IMMEDIATE; pembacaan daftar/count memakai satu transaksi baca.

| Tabel | Key / relasi | Data dan invariant |
|---|---|---|
| cases | case_id UUID PK; recurrence_of FK cases | ID perusahaan-bulan, status/version, alasan, aktor/waktu, JSON DatasetRef dan MonthlyEvidence. Partial unique index pada perusahaan-bulan ketika OPEN/IN_REVIEW/WAITING_EVIDENCE. |
| case_events | event_id UUID PK; case_id FK; UNIQUE(case_id,version) | Aktor/role, action, payload normalisasi, waktu server. Satu event per mutasi sukses; tidak ada edit/delete melalui API. |
| interventions | intervention_id UUID PK; case_id FK | Jenis rencana, status PLANNED/COMPLETED/CANCELLED, catatan/due_at, aktor/waktu, catatan outcome. Index case/time/ID. |
| mutation_receipts | PK(actor_id,idempotency_key) | Fingerprint SHA-256, respons JSON dan status HTTP asal. Tidak memiliki expiry otomatis pada prototipe. |

DatasetRef dan MonthlyEvidence dalam kasus adalah salinan immutable melalui API, bukan foreign key ke file CSV yang dapat diganti. Case creation memerlukan bukti valid; mutasi/replay kasus lama tidak bergantung pada snapshot aktif. Snapshot CSV tidak dimasukkan seluruhnya ke database kasus.

Domain store memeriksa state/role/alasan, recurrence (asal RESOLVED, perusahaan sama, periode lebih baru), If-Match, intervensi belum selesai, serta keunikan aktif sebelum menulis. Kunci unik dan BEGIN IMMEDIATE menutup race antarwriter. Bila data/event/receipt gagal, semuanya rollback. Reader tidak melihat setengah transaksi. Catatan boleh ditambah pada status terminal; versi tetap naik.

Waktu disimpan UTC ISO-8601; versi integer positif, bukan waktu. UUID lowercase menjadi pengenal eksternal. Semua parameter request memakai SQL binding; nama kolom dan tabel berasal dari konstanta internal. Unknown/missing value bukti dipertahankan dalam JSON; tidak ada kolom token, worker ID list, NPWP, telepon, ground truth, atau nilai exposure.

Database bukan ledger anti-tamper. Operator host memiliki akses penuh; belum ada tenant/region isolation, retensi otomatis, atau audit eksternal. Backup online memakai sqlite3.Connection.backup; restore pada path terpisah dan periksa sebelum mengganti konfigurasi. Contoh ada di apps/api/README.md. Tidak ada destructive reset/migration endpoint.
