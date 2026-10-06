---
project: JAGA-JKN
competition: BPJS Kesehatan Healthkathon 2026
status: DRAFT
version: 0.1.0
owner: TBD
authority: Project Governance
last_updated: 2026-10-07
---

# Project Charter

## Project
**JAGA-JKN — Sistem Intelijen Kepatuhan Pemberi Kerja JKN**

## Business need
BPJS Kesehatan membutuhkan mekanisme yang membantu petugas memahami ketidaksinkronan antara kondisi ketenagakerjaan pemberi kerja dan kondisi kepatuhan JKN, memprioritaskan kasus, menentukan tindak lanjut yang proporsional, dan memonitor penyelesaian tanpa menyerahkan keputusan akhir kepada AI.

## Objective
Membangun prototipe web decision-support yang mampu:
1. merekonstruksi kondisi kepatuhan yang seharusnya;
2. membandingkannya dengan kondisi aktual/teramati;
3. membentuk episode ketidaksesuaian lintas waktu;
4. memberi early warning dan prioritas pemeriksaan;
5. merekomendasikan intervensi;
6. memonitor resolved / recurring;
7. menyediakan evidence yang dapat ditelusuri.

## MVP scope
- Pendaftaran pekerja sebagian.
- Under-reporting upah.
- Ketidaksesuaian / keterlambatan iuran.
- Web dashboard internal BPJS.
- Synthetic two-world dataset yang seeded, versioned, validated.
- Rules + ML + decision-support.
- Human-in-the-loop.

## Out of scope MVP
- Keputusan fraud otomatis.
- Sanksi otomatis.
- Penggunaan data peserta JKN nyata tanpa izin resmi.
- Mobile native.
- Production integration BPJS.

## Success criteria
- Vertical slice end-to-end dapat didemonstrasikan.
- Semua requirement MVP tertrace ke test/evidence.
- Dataset lulus acceptance gate.
- Model dibandingkan baseline dan dievaluasi pada holdout yang benar.
- Sistem dapat abstain ketika evidence tidak cukup.
- UAT scenario inti lulus.
- Proposal Healthkathon didukung evidence implementasi aktual.
