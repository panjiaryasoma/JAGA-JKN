# JAGA-JKN | Serah Terima Data untuk Pengembangan ML

**Kode dokumen:** JAGA-DATA-ML-HO-001  
**Versi:** 0.1.1 (revisi bahasa; rancangan serah terima, bukan pengesahan fitur atau label ML)  
**Penerima:** Haidir, penanggung jawab pengembangan ML  
**Penyedia:** Tim Data Engineering JAGA-JKN  
**Cabang data:** `lintang-data-contract-alignment`  
**Commit acuan dataset yang dibekukan:** `9390d36a1adbef6f17aa6804dd6c56d290e06d04`  
**Bukti pengujian data:** GitHub Actions `37759059714` (62 dari 62 pengujian lulus)  
**Bukti publikasi CSV:** GitHub Actions `37806124944` (berhasil)  
**Keputusan serah terima:** **DATA SIAP DIAUDIT OLEH TIM ML; FITUR, LABEL, DAN PELATIHAN MODEL BELUM DISETUJUI.**

> **Batas penggunaan:** Seluruh data bersifat **sintetis** untuk pengujian perangkat lunak dan penelitian prototipe. Data ini bukan data empiris BPJS Kesehatan, bukan bukti pelanggaran JKN, dan tidak boleh digunakan untuk sanksi atau keputusan operasional. Kewenangan kebijakan B1/B2 belum selesai diverifikasi. Karena itu, hasil aturan tetap `ABSTAIN` sebagai mekanisme penolakan yang aman.

## 1. Tujuan dan pembagian pekerjaan

Dokumen ini menjelaskan **data mana yang harus diambil Haidir, fungsi setiap sumber, pemisahan fitur dengan label, batas waktu informasi, cara membagi data, serta bukti yang wajib disimpan**. Tim data menyediakan dan memvalidasi data; Haidir bertanggung jawab atas perumusan target, pemeriksaan kebocoran informasi, pemilihan fitur, pembagian data latih/validasi/uji, pelatihan model, dan evaluasinya.

**Jangan langsung menjalankan pelatihan** menggunakan semua kolom dari berkas kurasi atau berkas kandidat ML berisi 500 baris. Nilai yang membentuk label di simulator dapat muncul kembali sebagai fitur, sehingga nilai akurasi yang tinggi belum tentu membuktikan kemampuan mendeteksi risiko nyata.

## 2. Daftar sumber dan ketentuan penggunaannya

Seluruh alamat di bawah merujuk commit dataset **`9390d36a1adbef6f17aa6804dd6c56d290e06d04`**, bukan cabang `main` yang dapat berubah.

| Berkas | Satuan pengamatan dan jumlah | Fungsi | Batas pemakaian |
|---|---|---|---|
| `data/synthetic/curated/curated_kepatuhan_evidence.csv` | **Perusahaan-bulan; 12.000 baris** | **Sumber utama calon fitur** dari observasi dan mutu bukti hasil kurasi | Pilih kolom yang terbukti tersedia saat prediksi dan lulus audit kebocoran; jangan ambil seluruh kolom |
| `data/synthetic/scenario/kepatuhan_bulanan_badan_usaha.csv` | Perusahaan-bulan; 12.000 baris | Dunia acuan simulasi, sumber pembentukan label sintetis, serta bahan pemeriksaan kesesuaian skenario | Bukan sumber fitur bebas pakai; nilai acuan dan kondisi pembentuk label dapat membocorkan jawaban |
| `data/synthetic/raw/raw_kepatuhan_bulanan_badan_usaha.csv` | Perusahaan-bulan; 12.000 baris | Bukti mentah, gangguan data buatan, konflik sumber, masa berlaku informasi, dan waktu pencatatan | Bukan kebenaran independen; digunakan untuk penelusuran dan pemeriksaan ketersediaan fitur |
| `data/synthetic/curated/curated_master_badan_usaha.csv` | Perusahaan; 500 baris | Informasi perusahaan seperti skala, KBLI, dan wilayah | Gabung berdasarkan `id_badan_usaha`; atribut hanya calon fitur bersyarat, dan `scenario_profile_synthetic` dilarang sebagai fitur |
| `data/synthetic/candidate_ml/dataset_candidate_ml_audit.csv` | Kondisi terakhir per perusahaan; 500 baris | **Pemeriksaan awal struktur dan potensi kebocoran label** | **Belum layak dilatih langsung**; statusnya `CANDIDATE_ONLY__REQUIRES_LEAKAGE_LABEL_AND_EVALUATION_AUDIT` |
| `data/synthetic/scenario/log_review_petugas_synthetic.csv` | Peristiwa tinjauan petugas; 244 baris | Simulasi alur kerja manusia | Bukan tanggapan petugas sungguhan dan bukan label kebenaran lapangan |
| `data/synthetic/validation/` | Ringkasan pemeriksaan dan distribusi | Pemeriksaan kualitas, nilai kosong, duplikasi, sebaran, dan kelengkapan periode | Bukti kualitas data sintetis, bukan ukuran mutu model |
| `powerbi/data/` | Tabel penyajian untuk Power BI | Laporan dan visualisasi | Bukan sumber utama pelatihan ML; pengaitan ulang berkas PBIX masih tertunda |

**Tautan dataset yang dibekukan:**  
https://github.com/panjiaryasoma/JAGA-JKN/tree/9390d36a1adbef6f17aa6804dd6c56d290e06d04/data/synthetic

**Kode pembangkit dan pengolahan:**  
https://github.com/panjiaryasoma/JAGA-JKN/tree/9390d36a1adbef6f17aa6804dd6c56d290e06d04/pipelines/synthetic

## 3. Bukti kualitas dan asal data

- Dataset memuat **500 badan usaha × 24 bulan (Januari 2025 sampai Desember 2026) = 12.000 catatan perusahaan-bulan**.
- Hasil `dataset_summary.json`: **PASS**, tidak ada pelanggaran integritas keras atau peringatan deskriptif tersisa.
- **62 dari 62 pengujian data dan kontrak lulus**. Itu bukan pengujian ketepatan model ML.
- **26 berkas CSV serta dua ringkasan validasi** telah dipublikasikan ke GitHub. Empat grafik PNG berada di artefak GitHub Actions, bukan pada commit dataset tersebut.
- Versi asumsi pembangkitan: `SYN-2026-10-08-v3`.
- **Seed yang benar-benar dipakai:** `JAGA_SYNTHETIC_SEED=42` untuk skenario; pembangkit bukti mentah memakai **43** (`42 + 1`).
- Uji pengulangan hash membuktikan skenario deterministik pada pengujian yang dijalankan. Determinisme pembangkit mentah diuji pada pengujian unit; belum ada klaim bahwa seluruh keluaran mentah dan kurasi telah diuji dengan dua pengulangan penuh beserta hash.
- Dokumen strategi data yang masih **DRAFT** menyebut `generation_seed=20261006`, `split_seed=20261007`, dan `model_seed=20261008`. Angka itu **belum boleh dianggap sebagai konfigurasi eksekusi**. Yang telah berjalan hanya seed 42 dan 43; pembagian data dan pelatihan belum dilakukan.

## 4. Kunci penggabungan dan batas waktu prediksi

1. `id_badan_usaha` mengidentifikasi satu perusahaan sintetis. `periode_bulan` berupa `YYYY-MM`. Pasangan **(`id_badan_usaha`, `periode_bulan`)** merupakan kunci unik perusahaan-bulan.
2. Berkas induk perusahaan digabung menggunakan `id_badan_usaha`. **Jangan** menggabungkan berdasarkan nama badan usaha karena nama buatan dapat berulang.
3. Nama, NPWP, nomor telepon, pengenal pekerja, pengenal sumber, dan pengenal perusahaan bukan fitur mentah ML.
4. Pisahkan **dunia acuan simulasi**, **bukti teramati**, **bukti hasil kurasi**, **hasil aturan**, **status tinjauan**, serta **hasil untuk penyajian**. Informasi dari tahap hilir tidak otomatis tersedia saat model memprediksi.
5. Haidir harus menetapkan **batas waktu prediksi (`prediction_cutoff`)** dan hanya menggunakan informasi yang sudah tersedia pada atau sebelum batas itu. Data bulan berjalan mungkin sah untuk menjelaskan kondisi bulan tersebut, tetapi bisa menjadi kebocoran informasi bila model diminta memprediksi kondisi masa depan.
6. Seluruh distribusi berasal dari simulator ber-seed, bukan angka prevalensi atau proporsi pelanggaran sebenarnya di populasi JKN.

## 5. Matriks kelayakan 91 kolom kurasi

Baca lampiran `JAGA_JKN_ML_FEATURE_ELIGIBILITY_MATRIX.csv`. Semua **91 kolom** telah dikelompokkan dan diberi **`langsung_sebagai_fitur=TIDAK`**. Nilai **bersyarat** tidak berarti otomatis disetujui.

| Klasifikasi dalam matriks | Jumlah | Aturan |
|---|---:|---|
| `KUNCI_GABUNG_BUKAN_FITUR` | 3 | Untuk penggabungan, kelompok perusahaan, atau batas waktu, bukan fitur langsung |
| `KANDIDAT_LABEL_SAJA` | 1 | `synthetic_risk_mode_ground_truth` hanya calon label (`y`), tidak pernah fitur (`X`) |
| `OBSERVASI_BERSYARAT` | 12 | Calon fitur jika tersedia saat prediksi, tidak membocorkan label, dan asal data diketahui |
| `KUALITAS_BUKTI_BERSYARAT` | 16 | Calon fitur jika pemeriksaan mutu bukti sudah ada pada waktu prediksi |
| `DILARANG_SEBAGAI_FITUR` | 19 | Hasil aturan/tinjauan, pengenal pekerja, atau nilai estimasi sintetis yang berbahaya sebagai fitur |
| `METADATA_PENELUSURAN_SAJA` | 40 | Hanya untuk penelusuran, audit, asal-usul data, atau metadata kewenangan |

**Contoh yang perlu kewaspadaan tinggi:**

- `registration_discrepancy_detected`, `wage_discrepancy_signal_rp`, dan `contribution_payment_gap_observed` berhubungan dekat dengan logika pembentukan label `synthetic_risk_mode_ground_truth`. **Jangan masukkan sebelum audit kebocoran selesai.**
- `reference_worker_count` serta informasi dunia acuan membutuhkan pembuktian bahwa nilainya memang tersedia dari sumber yang sah pada saat prediksi, bukan hanya diketahui simulator.
- `*_rule_result`, `*_review_state`, `overall_review_state`, `human_review_recommendation`, dan informasi tinjauan manusia merupakan hasil hilir, bukan fitur bawaan.
- `estimated_exposure_synthetic_rp` adalah estimasi sintetis untuk penyajian, bukan kerugian terukur dan bukan dasar penentuan kepatuhan.
- `missing_worker_ids_json` dan `unexpected_worker_ids_json` memuat daftar pengenal pekerja; jangan ubah menjadi fitur.
- `scenario_profile_synthetic` pada berkas induk adalah pengaturan simulator, bukan atribut kejadian yang pantas dipelajari model.

**Peringatan kebocoran label:** Simulator menyusun `synthetic_risk_mode_ground_truth` dari perubahan pekerja, upah, dan pembayaran. Jika ketiga indikator itu langsung dimasukkan sebagai `X`, model bisa sekadar mempelajari ulang rumus pembangkit, bukan mengenali pola yang dapat diterapkan di lapangan. Nilai F1 yang sangat tinggi tetap harus dicurigai dan diaudit.

## 6. Pilihan tujuan prediksi yang harus diputuskan Haidir

**Belum ada tujuan ML maupun kontrak label yang dibekukan.** Dua kemungkinan untuk dibahas:

**Pilihan A — Klasifikasi kondisi simulasi pada bulan yang sama.**  
Calon `y_t = synthetic_risk_mode_ground_truth`. Hanya layak sebagai percobaan mereproduksi simulator setelah pembatasan fitur terbukti aman. Ini **bukan** klasifikasi pelanggaran JKN secara hukum dan bukan bukti mutu operasional nyata.

**Pilihan B — Peringatan dini untuk bulan mendatang.**  
Calon `y_(t+h)` dibentuk dari kondisi simulasi di masa depan, dengan jarak prediksi `h` yang ditetapkan. Fitur harus berasal dari informasi hingga bulan `t`. Dibutuhkan tabel fitur berdasarkan waktu, perumusan label masa depan, serta evaluasi temporal yang memadai. **Dataset siap latih untuk pilihan ini belum disediakan.**

Kolom `registration_rule_result`, `wage_rule_result`, `contribution_rule_result`, dan `overall_review_state` **bukan target yang sah untuk percobaan awal ini**. Otorisasi B1/B2 masih tertunda dan aturan akan menolak memberi keputusan dengan `ABSTAIN`. Hasil tinjauan petugas sintetis juga bukan label keadaan nyata.

## 7. Pembagian data latih, validasi, dan uji

**Saat ini belum ada berkas `train.csv`, `validation.csv`, atau `test.csv` yang dihasilkan.** Pembagian berikut adalah usulan kepada Haidir, bukan hasil eksekusi.

1. **Kelompokkan berdasarkan perusahaan:** setiap `id_badan_usaha` beserta seluruh riwayatnya hanya boleh berada pada **satu** kelompok. Jangan mencampur perusahaan yang sama di data latih dan uji.
2. **Contoh awal:** 70%/15%/15% dari 500 perusahaan berarti **350/75/75 perusahaan**. Jika seluruh perusahaan memiliki 24 bulan lengkap, jumlah catatan adalah **8.400/1.800/1.800**. Ini contoh rancangan, belum dijalankan.
3. **Pengujian waktu terpisah:** sisihkan periode berikutnya untuk pengujian di luar rentang waktu pelatihan. Jangan mengklaim pengujian perusahaan baru sama dengan pengujian masa depan.
4. **Hindari kebocoran saat praproses:** pengisian nilai kosong, pengodean kategori, penskalaan, pemilihan fitur, penyeimbangan label, dan pencarian parameter hanya boleh mempelajari data latih. Validasi dipakai untuk pemilihan pendekatan; data uji dijaga hingga evaluasi akhir.
5. **Seed pembagian yang diusulkan:** `20261007` hanya tertulis pada dokumen rancangan. Haidir wajib mencatat **seed yang benar-benar digunakan** dan tidak mengakuinya sebagai fakta sebelum dijalankan.
6. **Bukti pembagian:** simpan daftar perusahaan per kelompok, jumlah observasi, distribusi label, batas waktu, SHA kode, dan pemeriksaan irisan perusahaan = **0**.
7. **Dilarang membagi 12.000 baris secara acak per baris** karena riwayat perusahaan dapat muncul pada data latih sekaligus uji. Untuk tujuan prediksi mendatang, lakukan pengujian waktu dengan kontrol kebocoran dan jelaskan cakupan penilaiannya.

### Contoh artefak keluaran berikutnya milik Haidir

```text
data/synthetic/ml_splits/train.csv
data/synthetic/ml_splits/validation.csv
data/synthetic/ml_splits/test.csv
data/synthetic/ml_splits/split_manifest.json
results/ml_baseline_metrics.json
results/label_and_leakage_audit.md
models/metadata.json
```

**Nama di atas adalah usulan letak keluaran, bukan berkas yang sudah tersedia.** Pembuatan, pengujian, dan publikasinya memerlukan ruang lingkup kerja ML yang terpisah. Serah terima ini tidak mengizinkan perubahan sumber data, permintaan penggabungan, atau penggabungan cabang.

## 8. Daftar pemeriksaan penerimaan serah terima

| ID | Syarat penerimaan | Keadaan | Penanggung jawab |
|---|---|---|---|
| ML-HO-001 | SHA dataset, jumlah baris, dan kunci penggabungan jelas | **LULUS** | Tim data |
| ML-HO-002 | Pengujian kontrak, mutu data, dan makna nilai kosong jelas | **LULUS** | Tim data |
| ML-HO-003 | Asal pembangkitan, seed aktual, dan batasan sintetis terdokumentasi | **LULUS** | Tim data |
| ML-HO-004 | Seluruh 91 kolom diklasifikasikan; tidak ada fitur yang disetujui otomatis | **LULUS sebagai rancangan; menunggu peninjauan Haidir** | Tim data dan Haidir |
| ML-HO-005 | Tujuan prediksi, waktu prediksi, jarak prediksi, dan definisi label disetujui | **BELUM** | Haidir dan pemilik domain |
| ML-HO-006 | Daftar fitur `X` disahkan, asalnya jelas, dan kebocoran label diaudit | **BELUM** | Haidir |
| ML-HO-007 | Tidak ada informasi simulator, keputusan hilir, atau nilai estimasi terlarang di fitur `X` | **BELUM DIBUKTIKAN** | Haidir |
| ML-HO-008 | Pembagian menurut perusahaan dijalankan dan pengujian waktu dirancang | **BELUM** | Haidir |
| ML-HO-009 | Seed pembagian dan model aktual, daftar kelompok, serta manifest disimpan | **BELUM** | Haidir |
| ML-HO-010 | Model pembanding, metrik, distribusi per kelas, kalibrasi, dan keterbatasan dievaluasi | **BELUM** | Haidir |
| ML-HO-011 | Hasil ML hanya berlaku pada data sintetis; tidak dianggap pengesahan kebijakan | **WAJIB** | Semua pihak |

**Keputusan:** Data **boleh diserahkan kepada Haidir untuk audit fitur dan label**. **Pelatihan model belum boleh dinyatakan siap** sebelum syarat ML-HO-005 sampai ML-HO-009 diselesaikan. Tidak ada izin otomatis untuk membuat PR atau melakukan penggabungan.

## 9. Urutan pekerjaan Haidir sesudah menerima data

1. Ambil sumber dari commit yang dibekukan; periksa `dataset_summary.json` dan matriks 91 kolom.
2. Rumuskan pertanyaan ML: unit prediksi, kondisi yang diprediksi, batas waktu, jarak prediksi, dan pembanding awal.
3. Tentukan label `y` serta daftar calon fitur `X`; buktikan tiap fitur tersedia pada saat prediksi dan bukan hasil turunan langsung dari label.
4. Tetapkan pembagian menurut perusahaan dan rancangan uji waktu; simpan daftar kelompok serta seed.
5. Setelah audit lolos, lakukan pelatihan dan evaluasi; simpan hasil pengujian beserta penjelasan keterbatasan data sintetis.

## 10. Tautan bukti yang dibekukan

- Dataset: https://github.com/panjiaryasoma/JAGA-JKN/tree/9390d36a1adbef6f17aa6804dd6c56d290e06d04/data/synthetic
- Calon dataset ML: https://github.com/panjiaryasoma/JAGA-JKN/blob/9390d36a1adbef6f17aa6804dd6c56d290e06d04/data/synthetic/candidate_ml/dataset_candidate_ml_audit.csv
- Data kurasi: https://github.com/panjiaryasoma/JAGA-JKN/blob/9390d36a1adbef6f17aa6804dd6c56d290e06d04/data/synthetic/curated/curated_kepatuhan_evidence.csv
- Skenario dan label sintetis: https://github.com/panjiaryasoma/JAGA-JKN/blob/9390d36a1adbef6f17aa6804dd6c56d290e06d04/data/synthetic/scenario/kepatuhan_bulanan_badan_usaha.csv
- Ringkasan kualitas data: https://github.com/panjiaryasoma/JAGA-JKN/blob/9390d36a1adbef6f17aa6804dd6c56d290e06d04/data/synthetic/validation/dataset_summary.json
- Kode pembangkitan: https://github.com/panjiaryasoma/JAGA-JKN/blob/9390d36a1adbef6f17aa6804dd6c56d290e06d04/pipelines/synthetic/generate_dataset_bpjs.py
- Kode pengolahan kurasi: https://github.com/panjiaryasoma/JAGA-JKN/blob/9390d36a1adbef6f17aa6804dd6c56d290e06d04/pipelines/synthetic/pipeline_cleansing_dan_disambiguasi.py
- Bukti pengujian mutu data: https://github.com/panjiaryasoma/JAGA-JKN/actions/runs/37759059714
- Bukti CSV berhasil di-push: https://github.com/panjiaryasoma/JAGA-JKN/actions/runs/37806124944

**Catatan:** Semua nama berkas dan kolom yang tetap berbahasa Inggris adalah pengenal teknis dari kode sumber; penjelasan kerja, instruksi, batas penggunaan, dan kriteria penerimaan menggunakan bahasa Indonesia.
