# Offline model inference adapter

Training dan inference memakai `build_features` serta preprocessing yang sama. Tidak ada dependensi API/server pada training package. Dari repository/bundle yang sudah `uv sync --locked --group ml`:

```python
import json
from packages.ml.inference import load_bundle, predict_record, record_from_api

bundle = load_bundle()  # models/best_model.pkl + models/metadata.json
result = predict_record(bundle, json.load(open("models/example_input.json")))

# Respons JSON dari dua endpoint backend pada dataset dan perusahaan yang sama:
# GET /api/v1/badan-usaha/BU-0001
# GET /api/v1/badan-usaha/BU-0001/evidence/2025-01
# raw = record_from_api(company_response, evidence_response)
# result = predict_record(bundle, raw)
```

Adapter hanya mengambil fitur yang dideklarasikan; ground truth, rule output, review state dan exposure tidak masuk model. `dataset_id`, `source_commit`, `id_badan_usaha` kedua respons harus cocok. Semua fitur wajib ada dan inference menolak missing values, quality/boolean invalid, periode invalid, kuantitas negatif/infinite, serta input tanpa `is_synthetic: true`. Caller harus menampilkan kondisi tidak tersedia/abstain bila validasi gagal.

Hasil memuat target bulan berikutnya, model version, score, threshold, dan `experimental_prediction`. Score class-weighted belum dikalibrasi. API existing masih `ml_status=NOT_CONFIGURED`, `policy_status=UNRESOLVED`; adapter ini tidak mengubah keputusan rule atau workflow. Integrasi endpoint memerlukan task terpisah setelah review hasil model.

Missing observations pada training dipertahankan dan diimputasi dengan median training saja. Inference sengaja menolak input tidak lengkap. Unknown kategori profil diberi kode -1 melalui encoder training, tidak fit ulang.
