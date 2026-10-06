# JAGA-JKN

**Sistem Intelijen Kepatuhan Pemberi Kerja JKN**

JAGA-JKN adalah platform web decision-support berbasis AI/ML untuk membantu BPJS Kesehatan memantau siklus kepatuhan pemberi kerja: merekonstruksi kondisi yang seharusnya, mendeteksi episode ketidaksesuaian, memprioritaskan tindak lanjut, dan memantau penyelesaian atau kemunculan kembali masalah.

> Sistem mendukung keputusan petugas, bukan menetapkan pelanggaran atau sanksi secara otomatis.

## Status

Project scaffold / preproduction baseline untuk Healthkathon BPJS Kesehatan 2026.

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
