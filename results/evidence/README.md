# bukti ml — dataset sampai evaluasi

status: draft eksperimen sintetis

| komponen | bukti |
|---|---|
| Tes ML | 36 lulus; JUnit dan log lengkap |
| Data sintetis | 62 tes lulus; log lengkap |
| Governance | 24 tes + validator 213 entri lulus |
| Split | CSV dan hash cocok; overlap perusahaan 0; batas waktu lulus |
| Artifact | Hash PKL tetap; prediksi reload cocok dengan skor test tersimpan |
| Reproduksi training | Lulus; log lengkap dan 6 pembandingan file identik ada di clean_reproduction.json |
| GitHub CI | Belum dijalankan remote; workflow tersedia |
| SHAP baru | Tidak dibuat; koefisien LR tersedia |
| Validasi eksternal / as-of operasional | Belum tersedia |

| Regime | Partition | Perusahaan | Baris | Bulan fitur | Bulan target | NON-NORMAL |
|---|---|---|---|---|---|---|
| group_time | Train | 350 | 4,900 | 2025-01 → 2026-02 | 2025-02 → 2026-03 | 34.1% |
| group_time | Validation | 75 | 225 | 2026-03 → 2026-05 | 2026-04 → 2026-06 | 46.7% |
| group_time | Test | 75 | 450 | 2026-06 → 2026-11 | 2026-07 → 2026-12 | 45.3% |
| company_holdout | Train | 350 | 8,050 | 2025-01 → 2026-11 | 2025-02 → 2026-12 | 38.8% |
| company_holdout | Validation | 75 | 1,725 | 2025-01 → 2026-11 | 2025-02 → 2026-12 | 38.9% |
| company_holdout | Test | 75 | 1,725 | 2025-01 → 2026-11 | 2025-02 → 2026-12 | 36.9% |

model sha256: `83a4bd5362e903659d426a7d55e64756a28a3a381f72d2163a10de4829f3bb2c`

buka index.html untuk seluruh grafik; png dan svg di figures/
hasil test tidak dipakai untuk tuning ulang; data nyata dan validasi independen belum tersedia
