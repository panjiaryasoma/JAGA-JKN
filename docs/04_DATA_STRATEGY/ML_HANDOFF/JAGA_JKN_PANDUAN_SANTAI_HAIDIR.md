# JAGA-JKN: Panduan Data buat Haidir

**Versi:** 1.0 — panduan kerja santai, bukan pengganti kontrak resmi  
**Buat:** Haidir (bagian ML)  
**Dataset yang dipakai:** branch `lintang-data-contract-alignment`, commit `9390d36a1adbef6f17aa6804dd6c56d290e06d04`  
**Status:** data sintetis sudah dibuat dan dicek; **fitur, label, pembagian data, dan training ML belum final**.

## Dir, mulai dari sini dulu

Kita sudah punya dataset sintetis JAGA-JKN untuk **500 badan usaha** dengan riwayat **24 bulan** (Januari 2025 sampai Desember 2026). Totalnya **12.000 baris data bulanan**. Ini bahan buat eksperimen ML, **bukan data asli BPJS** dan bukan bukti kalau suatu perusahaan benar-benar melanggar aturan.

**Jangan langsung ambil CSV terus panggil `model.fit()`.** Soalnya ada kolom yang memang dibuat simulator untuk membentuk jawabannya. Kalau ikut dimasukkan sebagai fitur, akurasi bisa kelihatan tinggi padahal modelnya cuma belajar mengulang rumus pembangkit data.

## File mana yang perlu lu buka?

| File | Buat apa | Perlu diingat |
|---|---|---|
| `data/synthetic/curated/curated_kepatuhan_evidence.csv` | **Sumber utama calon fitur**; 12.000 baris perusahaan-bulan | **Jangan pakai semua kolom**. Pilih setelah audit fitur dan waktu ketersediaannya. |
| `data/synthetic/scenario/kepatuhan_bulanan_badan_usaha.csv` | Dunia acuan simulasi; ada `synthetic_risk_mode_ground_truth` | **Sumber kandidat label** untuk eksperimen, bukan fitur mentah. |
| `data/synthetic/raw/raw_kepatuhan_bulanan_badan_usaha.csv` | Bukti mentah dengan gangguan data dan konflik sumber buatan | Buat cek asal data dan apakah informasi benar-benar tersedia saat prediksi. |
| `data/synthetic/curated/curated_master_badan_usaha.csv` | Informasi perusahaan, misalnya skala, sektor, dan wilayah | Gabungkan pakai `id_badan_usaha`, **bukan nama perusahaan**. |
| `data/synthetic/candidate_ml/dataset_candidate_ml_audit.csv` | Ringkasan terakhir 500 perusahaan | **Cuma buat audit awal, belum siap training.** |
| `data/synthetic/scenario/log_review_petugas_synthetic.csv` | Simulasi hasil tinjauan petugas | **Bukan label dari petugas asli.** |
| `data/synthetic/validation/` | Laporan nilai kosong, duplikasi, kualitas bukti, dan distribusi | Baca sebelum eksperimen. |
| `powerbi/data/` | Data untuk dashboard | Jangan jadikan sumber utama training. |

Link data: https://github.com/panjiaryasoma/JAGA-JKN/tree/9390d36a1adbef6f17aa6804dd6c56d290e06d04/data/synthetic

## Jebakan paling penting: kebocoran label

Misalnya target lu `synthetic_risk_mode_ground_truth`, yang membedakan kondisi seperti `NORMAL`, `WAGE_REPORTING_GAP`, dan lainnya. Di simulator, kondisi itu berkaitan langsung dengan selisih pekerja, upah, dan pembayaran.

Kalau targetnya dibentuk dari selisih upah, lalu fitur lu `wage_discrepancy_signal_rp`, model bisa kelihatan jago karena petunjuk jawabannya sudah ada. Hal serupa perlu diperiksa untuk `missing_worker_count`, `registration_discrepancy_detected`, dan `contribution_payment_gap_observed`.

Hal lain yang perlu **dikeluarkan dari fitur `X` secara bawaan**:

- `synthetic_risk_mode_ground_truth` dan `scenario_profile_synthetic` (informasi jawaban/simulator).
- `*_rule_result`, `*_review_state`, `overall_review_state`, `human_review_recommendation` (hasil aturan atau alur tinjauan, bukan observasi mentah).
- `estimated_exposure_synthetic_rp` (estimasi sintetis untuk penyajian; bukan kerugian nyata atau dasar keputusan).
- ID badan usaha, NPWP, nama, nomor telepon, daftar ID pekerja, dan ID sumber (untuk identifikasi/penelusuran, bukan fitur).

**Penting:** bahkan kolom observasi atau kualitas bukti belum otomatis aman. Lu perlu pastikan kolom itu **sudah diketahui pada waktu prediksi** dan tidak secara langsung membentuk label. Daftar lengkap **91 kolom** ada di matriks handoff resmi; semuanya dimulai dari status **belum boleh langsung masuk `X`**.

Matriks: https://github.com/panjiaryasoma/JAGA-JKN/blob/lintang-data-contract-alignment/docs/04_DATA_STRATEGY/ML_HANDOFF/JAGA_JKN_ML_FEATURE_ELIGIBILITY_MATRIX.csv

## Sebenarnya ML-nya mau memprediksi apa?

Ini **belum diputuskan**, jadi tentukan dulu sebelum training:

**Opsi A: klasifikasi kondisi sintetis di bulan yang sama.** Cocok buat eksperimen awal atau memastikan pipeline ML berjalan. Tapi hati-hati, ini bisa jadi cuma menebak rumus simulator, bukan belajar risiko yang berguna di dunia nyata.

**Opsi B: peringatan dini untuk bulan berikutnya.** Pakai riwayat sampai bulan `t` untuk memprediksi kondisi pada bulan `t+1` (atau jarak waktu lain yang lu tetapkan). Ini lebih menarik untuk produk, tetapi **dataset fitur masa depan belum disiapkan**. Lu perlu bikin fitur historis dan label sesuai jarak prediksi tanpa melihat masa depan.

Jangan memakai hasil `*_rule_result` sebagai target pelanggaran hukum. Otorisasi aturan B1/B2 masih belum tuntas; sistem saat ini sengaja mengembalikan `ABSTAIN`.

## Kalau mau bagi train, validation, test

**Belum ada file split yang dibuat.** Contoh usulan untuk percobaan awal:

- **Train:** 350 perusahaan (70%).
- **Validation:** 75 perusahaan (15%).
- **Test:** 75 perusahaan (15%).

Aturan kerasnya: **semua 24 bulan milik satu perusahaan harus masuk kelompok yang sama**. Jangan bagi acak 12.000 baris karena perusahaan yang sama bisa muncul di train dan test.

Kalau modelnya mau memprediksi bulan depan, tambah **pengujian berdasarkan waktu**. Semua fitur bergantung waktu harus dihitung dari data yang tersedia sampai batas waktu prediksi. Praproses dan pemilihan fitur jangan belajar dari data uji.

Seed generator yang benar-benar dipakai **42** dan generator raw **43**. Nilai `split_seed=20261007` dan `model_seed=20261008` baru tercantum di dokumen strategi yang masih DRAFT; **belum dieksekusi**. Lu yang perlu menentukan, memakai, dan menyimpan seed eksperimen ML sebenarnya.

## Biar handoff-nya jelas, urutan kerja lu begini

1. Ambil dataset dari commit yang ditautkan di atas, lalu cek `data/synthetic/validation/dataset_summary.json`. Hasil validasi data sekarang **PASS**; **62/62 pengujian** yang lulus adalah pengujian data, **bukan** metrik performa ML.
2. Tulis **pertanyaan prediksi**, target `y`, unit prediksi (perusahaan atau perusahaan-bulan), dan batas waktu informasi yang boleh dilihat model.
3. Pilih fitur `X` dari berkas kurasi, pakai matriks 91 kolom, dan jelaskan **kenapa tiap fitur aman dari kebocoran**.
4. Bikin **train/validation/test** dengan pemisahan menurut `id_badan_usaha`, simpan daftar perusahaan per kelompok, distribusi label, seed, dan bukti tidak ada perusahaan yang overlap.
5. Baru setelah itu coba model pembanding, training, dan evaluasi. Simpan metrik per kelas, hasil audit kebocoran, dan keterbatasan eksperimen.

**Pembagian tugas:** tim data bertanggung jawab atas pembangkitan, kurasi, validasi, dan publikasi dataset. **Lu memegang rancangan fitur/label, pembagian data, training, dan evaluasi ML.** Kalau ada kolom yang maknanya belum jelas, tahan dulu pemakaiannya; jangan tebak dari nama kolom.

**Intinya: datanya sudah tersedia, tetapi belum ada izin teknis untuk menganggap semua kolom aman buat model. Audit dulu, split dengan benar, baru train.**

---

**Catatan:** panduan ini sengaja santai. Untuk keputusan formal, status penerimaan, dan klasifikasi lengkap setiap kolom, acuan utamanya tetap dokumen [Serah Terima Data untuk Pengembangan ML](https://github.com/panjiaryasoma/JAGA-JKN/blob/lintang-data-contract-alignment/docs/04_DATA_STRATEGY/ML_HANDOFF/JAGA_JKN_DATA_TO_ML_HANDOFF_HAIDIR.md). Dokumen santai ini belum mengubah kode, dataset, atau status persetujuan ML.
