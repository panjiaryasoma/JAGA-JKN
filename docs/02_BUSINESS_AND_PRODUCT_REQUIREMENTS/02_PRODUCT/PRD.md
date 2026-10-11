---
project: JAGA-JKN
status: DRAFT
version: 0.2.0
owner: Panji
authority: Product Requirements
last_updated: 2026-10-09
---

# PRD — backend bukti sintetis dan workflow review

## Tujuan dan lingkup

Tujuan produk tetap mendukung pemeriksaan ketidaksesuaian pemberi kerja dengan keputusan akhir pada manusia. Backend prototipe memungkinkan kandidat petugas menjelajahi badan usaha dan bukti sintetis, kemudian menjalankan workflow review yang mempertahankan ketidakpastian, kualitas, dan penelusuran sumber.

Dasar kebutuhan: BRD, Project Charter O-03/O-06/O-07/O-08, dan handoff JAGA-DATA-ML-HO-001. Pengguna operasional aktual, kebijakan eksekusi, dan akses data produksi belum terverifikasi. Pekerjaan branch diperintahkan pemilik proyek; penerimaan produk/domain tetap terbuka. Tidak ada deklarasi FROZEN atau production-ready.

## Perjalanan pengguna

1. Membuka daftar badan usaha dan mencari nama/ID atau memfilter provinsi, skala, dan KBLI.
2. Membuka profil menggunakan ID stabil; nama bukan kunci penggabungan.
3. Menelusuri bulan/rentang bulan dan melihat registrasi, upah, pembayaran, mutu bukti, alasan aturan, dan sumber.
4. Melihat konteks sintetis serta status ML/kebijakan. ABSTAIN, data tidak diketahui, dan layanan data gagal tidak ditampilkan sebagai risiko rendah.
5. Membuka kasus, mencatat pemeriksaan dan intervensi, menyelesaikan review melalui supervisor, serta menghubungkan recurrence manual bila relevan.

## Requirement dan acceptance criteria

| ID | Perilaku yang harus dibuktikan |
|---|---|
| BE-001 | Metadata memuat commit sumber yang dideklarasikan, hash kedua CSV, periode simulasi, jumlah baris, dan penanda sintetis; semua respons data menunjuk snapshot sama. |
| BE-002 | Pencarian nama/ID case-insensitive; filter exact-match dapat digabung; pagination dibatasi; urutan ID deterministik; tidak ada hasil berarti daftar kosong. |
| BE-003 | Detail ID sah yang tidak ditemukan menghasilkan 404, format salah 422. Tidak membocorkan pengenal personal atau kolom simulator. |
| BE-004 | Riwayat berurutan berdasarkan bulan, filter inklusif, detail bulan tunggal tersedia, alasan dan lineage dipertahankan. |
| BE-005 | null/false/0 berbeda. Observasi tidak menjadi keputusan pelanggaran; hasil aturan tetap ABSTAIN dan otoritas belum disahkan. |
| BE-006 | Hash, header, tipe, enum, kunci unik, foreign key, dan grid perusahaan-bulan diperiksa sebelum melayani data. Satu kegagalan menutup seluruh API data dengan 503. |
| BE-007 | 404/405/422/503/500 memakai envelope error; request ID body/header konsisten; tanpa stack trace, nilai input mentah, atau path lokal. |
| BE-008 | Liveness terpisah dari readiness; log akses berisi request ID, template route, status/durasi tanpa body/query/identitas perusahaan. |
| BE-009 | Metadata menyatakan ML NOT_CONFIGURED dan policy UNRESOLVED. Tidak ada prediksi rekaan, label ground truth, worker IDs, NPWP, telepon, atau exposure dalam respons. |
| BE-010 | Dependensi terkunci, run/test terdokumentasi, fixture kecil dan smoke test snapshot 500 × 24 tersedia. |

## Perluasan backend prototipe

Instruksi pemilik proyek berikutnya meminta backend sampai final. Lingkup teknis diperluas menjadi kasus review persisten, catatan intervensi/outcome, resolution/dismissal/reopen, link recurrence manual, autentikasi demo, dan dashboard agregat. Kontrak CASE_LIFECYCLE_SPEC.md serta ACCESS_CONTROL_REQUIREMENTS.md menjadi target uji, tetap DRAFT untuk penerimaan bisnis.

| ID | Acceptance criteria tambahan |
|---|---|
| BE-011 | Token server menentukan aktor/role; identitas/role dalam payload ditolak; tindakan supervisor ditolak untuk reviewer. |
| BE-012 | Semua transisi mengikuti state machine; alasan wajib; tidak ada dua kasus aktif badan usaha-bulan. |
| BE-013 | Rencana intervensi dicatat lokal; outcome tepat satu; kasus dengan rencana belum selesai tidak dapat ditutup. |
| BE-014 | Setiap aksi menambah event berurutan dengan aktor, waktu server, dan versi; kasus/event bertahan setelah restart. |
| BE-015 | If-Match mencegah lost update; dua aksi simultan atas versi sama menghasilkan tepat satu pemenang. |
| BE-016 | Idempotency-Key mencegah efek ganda; beda payload dengan key sama ditolak; kegagalan transaksi tidak meninggalkan event/versi/receipt parsial. |
| BE-017 | Case snapshot lama tetap dapat dibaca saat dataset aktif gagal; recurrence hanya menghubungkan perusahaan sama, periode lebih baru, kasus asal RESOLVED. |
| BE-018 | Dashboard membedakan true/false/unknown, mutu bukti, dan abstention; tidak mengarang risk score atau estimasi manfaat. |
| BE-019 | Capabilities menjelaskan status snapshot, database, auth, dan ML; kegagalan komponen tidak disamarkan menjadi hasil kosong. |

Integrasi model terlatih, eksekusi aturan B1/B2, autentikasi produksi, automatic episode detection, dan sistem eksternal tetap membutuhkan bukti/kontrak berikutnya.

## Data dan waktu

Snapshot Januari 2025–Desember 2026 adalah waktu simulasi, termasuk bulan yang mungkin berada di masa depan terhadap server. API tidak mengklaim kondisi aktual hari ini atau ketersediaan fitur prediksi. Tidak ada training, inferensi, atau perubahan aturan saat request API.

## Sumber kontrak dan traceability

Kontrak HTTP: docs/05_PREPRODUCTION/01_CONTRACTS_ACTIVE/API_CONTRACT.md. Identitas snapshot: config/backend_dataset_manifest.json. Skema respons/OpenAPI berasal dari model kode; pemetaan field sumber eksplisit. docs/07_TRACEABILITY_AND_CONTROL/TEST_TRACEABILITY.csv menghubungkan requirement ke tes. Penerimaan bisnis/ML terpisah dari tes perangkat lunak.
