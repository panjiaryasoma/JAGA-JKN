# kontrak perbaikan eksperimen ml

Status: DRAFT untuk penerimaan domain; spesifikasi implementasi eksperimen sintetis, 11 Oktober 2026. Dasar branch Haidir `ff2549427c6437bbe4a7835338974d9b538c8bf1`. Permintaan Panji: perbaiki pipeline dan serahkan model yang dapat ditemukan/digunakan.

## simple prd

Tim perlu bisa clone, menjalankan satu perintah training, melihat evaluasi yang tidak memakai test untuk tuning, lalu mengambil model bersama preprocessing dan metadata yang cocok. Model tetap eksperimen sintetis; tidak mengaktifkan keputusan hukum atau mengganti ABSTAIN pada backend.

## keputusan sebelum training ulang

- Unit: perusahaan-bulan. Target: kondisi simulator NON-NORMAL pada bulan kalender berikutnya; lima enum label sumber divalidasi. Fitur hanya dari baris bulan t dan profil perusahaan. Tidak memakai label, rule/review outputs, exposure, ID, atau worker ID lists sebagai X.
- Prediksi mengasumsikan snapshot bulanan sudah tersedia. Waktu ingest/as-of semua atribut tidak tersedia dalam sumber; ini bukan bukti point-in-time availability operasional. Pengujian waktu di bawah menguji urutan periode, tidak menyelesaikan batasan timestamp tersebut.
- Quality HIGH/MEDIUM/LOW dipetakan deterministik ke 1/0.5/0; enum lain ditolak. Boolean invalid ditolak. Missing observation dipertahankan; imputasi dipelajari hanya dari training. Input inference yang tidak lengkap/invalid ditolak.
- `month_index` ditahan dan dikeluarkan karena keputusan HOLD lama belum terselesaikan. `is_semester_end` diketahui dari kalender. Korelasi/MI hanya diagnostik, bukan aturan izin fitur. Observasi lainnya tetap kandidat bersyarat untuk benchmark sintetis; tidak dinyatakan disahkan untuk data nyata.
- Membership perusahaan asli 350/75/75 dipertahankan dalam config/ml_company_partitions.json. Setiap perusahaan tetap hanya di satu grup. Group-only benchmark tersedia untuk pembanding historis.
- Evaluasi utama `group_time`: training target <= 2026-03; validation target 2026-04..2026-06; test target 2026-07..2026-12. Fitur bulan sebelumnya. Batas label training tidak melampaui bulan fitur validation pertama; batas label validation tidak melampaui bulan fitur test pertama. Seluruh cutoff dibekukan sebelum membaca hasil model baru.
- Kandidat: LogisticRegression, RandomForest, LightGBM, parameter tetap. Fit scaler/imputer/encoder pada training saja. Pilih threshold setiap kandidat berdasarkan F1-macro validation, lalu pilih model berdasarkan F1-macro validation; tie-break deterministik. Test tidak menjadi argumen fungsi seleksi.
- Ambang operasional 0.60 yang belum disahkan dihapus dari rekomendasi. Score class-weighted belum dikalibrasi sebagai probabilitas risiko nyata. Metadata menyebut threshold seleksi validation dan tujuan optimasinya.
- Evaluasi test sekali setelah seleksi: confusion matrix, per-class metrics, F1 macro/binary, accuracy/balanced accuracy, ROC-AUC, average precision, Brier score; bandingkan constant normal/non-normal dan prior training. Simpan prediksi per perusahaan-bulan untuk audit. Jangan tuning ulang berdasarkan hasil test.
- Test lama sudah pernah dilihat saat audit/perbaikan; hasil rerun adalah regression benchmark, bukan holdout yang benar-benar virgin atau klaim validasi eksternal. Data sintetis independen/empiris diperlukan untuk penerimaan model.

## acceptance teknis

| ID | Syarat |
|---|---|
| MLR-001 | Semua modul importable; dependencies dikunci dan entrypoint terdokumentasi. |
| MLR-002 | Quality tidak runtuh ke nol; missing/enum/duplicate key/calendar gap ditangani eksplisit. |
| MLR-003 | Group split disjoint; lead target persis bulan berikutnya; temporal boundary diuji. |
| MLR-004 | Preprocessing dan seleksi model/threshold tidak belajar dari test; train/serve memakai transform sama. |
| MLR-005 | Model pkl, metadata, SHA-256 penuh, feature order, runtime version, dataset/code hash, split manifest, dan contoh input/output tersedia. |
| MLR-006 | Loader mendeteksi corrupt/mismatch artifact; input inference strict dan hanya synthetic; prediksi setelah reload sama. |
| MLR-007 | Hasil baru dapat direproduksi, baseline dilaporkan jujur; audit tidak mengubah korelasi menjadi izin fitur. |

Artifacts lokal: models/best_model.pkl + models/metadata.json. Model binary diabaikan git; ZIP handoff membawa artifact dan loader/source yang cocok. Perubahan branch ML tidak otomatis mengaktifkan model di API backend atau memberi izin merge/publish ke branch teman.

## tambahan bukti review

Permintaan Panji: bukti validasi dan visualisasi dari dataset sampai split. Paket bukti menambahkan grafik deskriptif snapshot, kualitas/distribusi fitur, timeline target, label per partition, korelasi training, confusion matrix/ROC/PR/reliability diagnostic, perbandingan kandidat validation, dan koefisien model. Log tes dan replay dari folder bersih disimpan, beserta CSV split, membership serta assignment seluruh baris.

Bukti ini dibuat sesudah model dibekukan; tidak mengubah model, threshold atau pembagian data berdasarkan test. Kelengkapan bukti teknis tidak mengubah status domain DRAFT, validasi eksternal, atau otorisasi operasional.
