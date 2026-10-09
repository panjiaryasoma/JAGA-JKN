# JAGA-JKN

**Sistem Intelijen Kepatuhan Pemberi Kerja JKN**

JAGA-JKN adalah platform web decision-support berbasis AI/ML untuk membantu BPJS Kesehatan memantau siklus kepatuhan pemberi kerja: merekonstruksi kondisi yang seharusnya, mendeteksi episode ketidaksesuaian, memprioritaskan tindak lanjut, dan memantau penyelesaian atau kemunculan kembali masalah.

> Sistem mendukung keputusan petugas, bukan menetapkan pelanggaran atau sanksi secara otomatis.

## Status

Backend prototipe sintetis tersedia: profil/bukti bulanan, dashboard agregat, kasus review persisten, intervensi/outcome, audit, dan role demo. Snapshot terkunci berisi 500 badan usaha × 24 bulan. ML masih `NOT_CONFIGURED`; kebijakan `UNRESOLVED` dan keputusan bukti `ABSTAIN`.

## Menjalankan backend

Gunakan Python 3.12 atau 3.13 dan uv 0.12.23, dari root repository:

```bash
uv sync --locked
uv run --locked python -m apps.api --demo
```

Swagger: http://127.0.0.1:8000/docs. Token reviewer/supervisor dibuat acak dan ditampilkan sekali di terminal; gunakan tombol **Authorize** untuk mencoba workflow. Kasus tersimpan di `var/jaga-jkn.sqlite3`. Tanpa `--demo` atau token environment, endpoint baca tetap tersedia dan workflow menjawab `AUTH_NOT_CONFIGURED`.

Panduan integrasi, contoh request, konfigurasi, backup, dan pemeriksaan: [apps/api/README.md](apps/api/README.md). Kontrak: [API_CONTRACT.md](docs/05_PREPRODUCTION/01_CONTRACTS_ACTIVE/API_CONTRACT.md). Bukti penyelesaian teknis: [BACKEND_IMPLEMENTATION_REPORT.md](docs/08_TESTING_AND_ACCEPTANCE/BACKEND_IMPLEMENTATION_REPORT.md).

## Struktur utama

```text
apps/
  api/          FastAPI backend
  web/          dashboard web desktop-first

packages/
  domain/       domain model, policy, dan decision rules
  ml/           inference contract dan model integration
  data/         data contract dan shared data utilities

pipelines/
  synthetic/    synthetic data generation
  features/     feature engineering
  evaluation/   evaluation & benchmarking

models/         model artifacts/manifest (artifacts besar tidak di-commit)
tests/          test suites lintas komponen
scripts/        developer/project automation
config/         versioned non-secret configuration
docs/           canonical project documentation
```

## Prinsip desain

- human-in-the-loop
- evidence-backed decision support
- policy-aware expected-state reconstruction
- reproducible synthetic data
- traceability dari requirement sampai acceptance evidence
- fail-closed / abstain ketika bukti atau data tidak memadai

## Dokumentasi

Mulai dari [`docs/README.md`](docs/README.md) dan [`docs/DOCUMENT_MANIFEST.csv`](docs/DOCUMENT_MANIFEST.csv).
