# Model sintetis JAGA-JKN

`best_model.pkl` berisi classifier **dan preprocessing yang sudah fit**. File ini diabaikan Git; clone repository saja tidak mengunduhnya. Pipeline menyediakan ZIP unduhan dan GitHub Actions dapat mengunggah artifact setelah branch perbaikan dipublikasikan.

## Training dari checkout bersih

Gunakan Python 3.12 dan uv, lalu dari root repository:

```bash
uv sync --locked --group ml
uv run --no-sync pytest tests/ml -q
uv run --no-sync python -m pipelines.training
```

Output:

- `models/best_model.pkl` — bundle model primary `group_time`.
- `models/metadata.json` — hash artifact penuh, versi runtime, fitur, seleksi validation, dan provenance kode/data.
- `models/example_input.json`, `example_output.json`, `input_schema.json`.
- `results/ml_repair_report.md`, `results/benchmarks/*.json`, `*_predictions.csv`.
- `artifacts/jaga-jkn-ml-handoff.zip` — model, source, lockfile, source CSV sintetis, laporan, checksum.

Ekstrak ZIP ke direktori kosong untuk memakai artifact tanpa training ulang. Jalankan `uv sync --locked --group ml --python 3.12`, lalu:

```bash
uv run --no-sync python -m packages.ml.inference --input models/example_input.json
```

Loader memerlukan metadata di sebelah `.pkl`; versi Python major.minor dan paket harus sesuai. Gunakan `uv.lock` yang disertakan. Hash mendeteksi file rusak, bukan keaslian publisher: pickle hanya boleh berasal dari pipeline/CI yang dipercaya.

## Batas penggunaan

Eksperimen ini memprediksi label NON-NORMAL simulator pada bulan berikutnya. Skor belum dikalibrasi menjadi probabilitas risiko nyata. Status domain DRAFT; bukan penetapan kepatuhan. Threshold dipilih dari validation macro F1 dan tidak punya persetujuan operasional. Historical test sudah pernah diperiksa; hasil baru adalah regression benchmark.

Penggunaan adapter backend dijelaskan di `packages/ml/README.md`. Aktivasi endpoint ML belum dilakukan. SHAP lama tersimpan di `results/historical/ff25494/` dan bukan penjelasan untuk model baru. Plot SHAP opsional membutuhkan paket `shap` tambahan dan tidak menjadi prasyarat training.

## bukti dataset split dan validasi

Dari checkout repository lengkap yang sudah diperbaiki, sesudah training:

```bash
uv run --no-sync python scripts/reproduce_ml_bundle.py
uv run --no-sync python scripts/build_ml_evidence.py
```

`results/evidence/index.html` memuat 9 visualisasi dataset, fitur, split perusahaan/waktu, label per partition, korelasi training, evaluasi kedua regime, seleksi validation, dan koefisien LR. Versi PNG/SVG tersedia di `results/evidence/figures/`.

Folder bukti menyertakan log tes asli, JUnit XML, hash sumber, manifest reproducibility, membership perusahaan, assignment seluruh 12.000 baris, dan alasan exclusion. CSV train/val/test kedua regime disertakan pada paket bukti. Script laporan memverifikasi bahwa model, threshold, data dan split tetap cocok; tidak men-tuning model. Script reproduce membuat replay independen dari setting training yang dibekukan dan membandingkan byte model, skor, serta metrik.

Script bukti memerlukan checkout repository lengkap (termasuk governance dan synthetic tests). Paket model dapat dipakai sendiri untuk inference/training, sedangkan patch dalam paket bukti diterapkan ke checkout base untuk mereproduksi keseluruhan pemeriksaan.

CI remote dan validasi eksternal/data nyata tetap belum diklaim lulus. SHAP baru tidak dibuat; interpretasi parameter menggunakan koefisien LR dengan batasan ordinal encoding dan korelasi fitur.
