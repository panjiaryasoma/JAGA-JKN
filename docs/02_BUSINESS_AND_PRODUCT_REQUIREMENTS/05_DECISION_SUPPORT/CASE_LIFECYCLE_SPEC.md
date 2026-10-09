---
project: JAGA-JKN
status: DRAFT
version: 0.2.0
owner: Panji
authority: Prototype Backend Contract
last_updated: 2026-10-09
---

# Lifecycle kasus review prototipe

Kontrak implementasi lokal setelah instruksi pemilik proyek untuk menyelesaikan backend pada 9 Oktober 2026. Ini rancangan workflow demo, bukan klaim workflow internal BPJS atau pengesahan kebijakan B1/B2.

Kasus adalah permintaan review manusia atas satu badan usaha-bulan dari snapshot sintetis. Pembukaan kasus tidak menetapkan risiko, utang, pelanggaran, atau kewajiban tindakan nyata. Bukti dan metadata snapshot disalin immutable saat kasus dibuka; kasus lama tetap dapat dibaca bila dataset aktif rusak atau berubah.

| Status awal | Action | Status akhir | Role minimum |
|---|---|---|---|
| OPEN | START_REVIEW | IN_REVIEW | REVIEWER |
| IN_REVIEW | REQUEST_EVIDENCE | WAITING_EVIDENCE | REVIEWER |
| WAITING_EVIDENCE | RESUME_REVIEW | IN_REVIEW | REVIEWER |
| IN_REVIEW | RESOLVE | RESOLVED | SUPERVISOR |
| IN_REVIEW | DISMISS | DISMISSED | SUPERVISOR |
| RESOLVED / DISMISSED | REOPEN | OPEN | SUPERVISOR |

SUPERVISOR juga dapat melakukan aksi REVIEWER. Semua transisi memerlukan alasan. RESOLVED berarti pemeriksaan demo diselesaikan oleh manusia, bukan verifikasi hukum. DISMISSED berarti kasus review ditutup tanpa tindak lanjut pada prototipe.

Satu kasus aktif per badan usaha-bulan; kasus aktif ialah OPEN/IN_REVIEW/WAITING_EVIDENCE. Kasus terminal dapat dibuka ulang hanya jika tidak ada kasus aktif pengganti pada pasangan tersebut.

Intervensi hanya berupa catatan rencana REQUEST_DOCUMENTS/CONTACT_REVIEW/FOLLOW_UP, tanpa pengiriman pesan atau tindakan eksternal. Dibuat ketika IN_REVIEW/WAITING_EVIDENCE, awal PLANNED, kemudian tepat satu outcome COMPLETED/CANCELLED beserta catatan. Waktu due_at opsional harus memiliki timezone dan disimpan dalam UTC. Penyelesaian/penutupan kasus diblokir selama masih ada intervensi PLANNED. Catatan bebas boleh ditambahkan pada semua status tanpa mengubah status.

Recurrence adalah hubungan yang dinyatakan manusia: kasus baru boleh menunjuk kasus RESOLVED milik badan usaha sama dengan bulan yang lebih awal. Ini bukan hasil deteksi model. Link tidak mengubah kasus terdahulu.

Setiap mutasi menghasilkan event append-only melalui API dan menaikkan versi kasus tepat satu. Tidak tersedia edit/delete event atau delete kasus. Database lokal administrator tidak dianggap tamper-proof.

Idempotency-Key wajib untuk setiap POST. Key terikat aktor dan fingerprint method/path/payload/If-Match. Replay identik mengembalikan respons/ETag semula, ditandai Idempotent-Replay: true; ini bukan pembacaan versi terkini. Key sama dengan request berbeda ditolak 409.

Semua mutasi kasus yang sudah ada wajib If-Match kuat, format "vN". Header hilang → 428, format salah → 422, versi usang → 412 VERSION_CONFLICT. Operasi kasus/intervensi/event/receipt berada dalam satu transaksi SQLite BEGIN IMMEDIATE; kegagalan menulis menggulung balik semuanya. Data dan event harus bertahan setelah restart.
