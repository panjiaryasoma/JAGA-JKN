---
project: JAGA-JKN
status: DRAFT
version: 0.2.0
owner: Panji
authority: Product Requirements
last_updated: 2026-10-09
---

# Simple PRD — backend prototipe lengkap

Kandidat petugas perlu membuka profil badan usaha dan riwayat bukti bulanan dari satu snapshot sintetis yang dapat ditelusuri. Frontend membutuhkan kontrak stabil tanpa menunggu ML selesai.

Backend menyediakan daftar/pencarian/filter badan usaha, detail, riwayat/detail bukti bulanan, metadata snapshot, dashboard agregat, serta health/readiness/capabilities. Mutu bukti, alasan abstention, dan sumber tetap terlihat. Nilai tidak diketahui tetap `null`.

Reviewer dapat membuka kasus, memulai pemeriksaan, meminta bukti, mencatat rencana intervensi dan outcome, serta menambahkan catatan. Supervisor dapat menyelesaikan/menutup/membuka ulang kasus. Link recurrence dibuat manusia. SQLite mempertahankan kasus, salinan bukti, dan event setelah restart. Token demo menentukan aktor/role; versi kasus dan idempotency mencegah update tertimpa atau aksi ganda.

Data berasal dari dua CSV kurasi pada commit `9390d36a1adbef6f17aa6804dd6c56d290e06d04`. API hanya membaca byte yang cocok dengan manifest. Data mentah, label simulator, ID pekerja, NPWP, telepon, dan estimasi kerugian tidak menjadi respons publik.

Selesai secara teknis bila alur CSV → validasi → API → review → intervensi → resolution/recurrence berjalan dengan pengujian kegagalan data, input salah, akses, transaksi, restart, serta konkurensi. Model ML terlatih, autentikasi produksi, pengesahan kebijakan, dan integrasi eksternal memerlukan pekerjaan berikutnya. Rincian BE-001..BE-019 ada di PRD.md dan API_CONTRACT.md.

Instruksi pemilik proyek pada 9 Oktober 2026 mengizinkan pekerjaan pada branch backend. Dokumen ini tetap DRAFT untuk penerimaan produk; implementasi tidak menandakan pengesahan B1/B2 atau freeze proyek.
