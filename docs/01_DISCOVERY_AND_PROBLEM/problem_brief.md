---
project: JAGA-JKN
competition: BPJS Kesehatan Healthkathon 2026
status: REVIEWED
version: 0.2.0
owner: Panji
authority: Discovery & Problem Evidence
authority_level: A2
last_updated: 2026-10-07
---

# Problem Brief

## Validated problem class

Healthkathon 2026 secara eksplisit menetapkan **Efisiensi Risiko pada Pemberi Kerja** sebagai satu dari tiga kategori kompetisi. Participant Guide resmi mendefinisikan enam modus pada kategori tersebut, tetapi Proposal Guide mengklasifikasikan item #6 secara berbeda:

1. pendaftaran pekerja sebagian (PDUK);
2. pelaporan upah lebih rendah;
3. penggelapan atau penundaan setoran iuran;
4. misklasifikasi status hubungan kerja;
5. manipulasi data mutasi karyawan;
6. kolusi fasilitas kesehatan / surat keterangan fiktif.

Dengan demikian, keberadaan **problem class** employer-compliance risk adalah `VERIFIED`; klasifikasi item #6 berstatus `CONFLICTING_A0` dan tidak dipakai dalam MVP. Yang belum verified adalah frekuensi, nilai kerugian, workflow internal, serta data operasional yang tersedia untuk mendeteksi setiap modus.

## Problem statement

> BPJS Kesehatan membutuhkan cara yang dapat dipertanggungjawabkan untuk mengidentifikasi dan menindaklanjuti indikasi ketidaksesuaian antara kewajiban JKN pemberi kerja dan kondisi yang teramati, dengan mempertimbangkan perubahan lintas waktu, kualitas bukti, dan kewenangan keputusan manusia.

Pernyataan ini tidak mengklaim bahwa BPJS saat ini tidak memiliki proses atau sistem sejenis. Kondisi internal tersebut belum tersedia sebagai evidence proyek.

## Why expected vs observed is a defensible framing

Peraturan dan materi resmi BPJS menunjukkan bahwa pemberi kerja memiliki kewajiban mendaftarkan pekerja, memberikan data pekerja/upah yang benar, melaporkan perubahan data, dan membayar iuran. Karena kewajiban tersebut menghasilkan suatu kondisi normatif yang seharusnya terjadi, membandingkan **expected/reference state** dengan **observed/reported state** adalah hipotesis desain yang dapat diturunkan dari kewajiban formal.

Tetapi sumber kebenaran operasional untuk expected state pada deployment nyata masih `UNKNOWN`.

## Proposed MVP focus

Dari enam modus resmi, MVP mengusulkan tiga slice yang secara data-konseptual paling langsung berhubungan dengan discrepancy terukur:

- pendaftaran pekerja sebagian;
- under-reporting upah;
- ketidaksesuaian / penundaan iuran.

Pemilihan tiga slice ini adalah `PRODUCT HYPOTHESIS`, bukan klaim bahwa ketiganya adalah risiko terbesar secara empiris.

## Explicit non-claims

JAGA-JKN belum memiliki evidence untuk menyatakan:

- modus tertentu adalah yang paling sering terjadi;
- nominal kerugian nasional akibat tiap modus;
- proses review BPJS saat ini bersifat manual atau tidak efisien;
- data payroll/ketenagakerjaan eksternal tertentu tersedia bagi BPJS;
- model ML tertentu adalah solusi terbaik;
- risk score sama dengan probabilitas pelanggaran.

## Gate A

**PASS_WITH_CONSTRAINTS**

Phase B boleh dimulai karena problem class, competition fit, regulatory obligation, dan data-governance constraint telah didukung authority yang memadai. Constraint yang wajib dibawa ke BRD/domain phase:

- internal workflow = `UNKNOWN`;
- operational data availability = `UNKNOWN`;
- prevalence / financial magnitude = `UNKNOWN`;
- production thresholds = `UNKNOWN`;
- current regulation must be version-checked before encoding policy.
