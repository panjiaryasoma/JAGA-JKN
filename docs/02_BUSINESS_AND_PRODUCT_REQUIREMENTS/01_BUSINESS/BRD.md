---
project: JAGA-JKN
competition: BPJS Kesehatan Healthkathon 2026
status: DRAFT
version: 0.1.0
owner: TBD
authority: Business Requirements
last_updated: 2026-10-07
---

# Business Requirements Document (BRD)

## Business objective
Meningkatkan efektivitas pemantauan kepatuhan pemberi kerja dengan mengubah data tersebar menjadi kasus yang dapat dipahami, diprioritaskan, ditindaklanjuti, dan ditutup secara terukur.

## Business requirements
- **BR-001** Sistem harus membantu mengidentifikasi ketidaksesuaian antara kondisi referensi dan kondisi kepatuhan JKN yang teramati.
- **BR-002** Sistem harus menunjukkan perkembangan masalah lintas waktu, bukan hanya snapshot.
- **BR-003** Sistem harus membantu memprioritaskan kasus berdasarkan risiko, dampak, persistence, dan kualitas evidence.
- **BR-004** Sistem harus mendukung beberapa jalur intervensi, tidak menyamakan semua kasus sebagai audit.
- **BR-005** Sistem harus mendukung human decision authority; AI tidak menetapkan pelanggaran atau sanksi.
- **BR-006** Sistem harus dapat menunjukkan apakah masalah membaik, selesai, atau berulang.
- **BR-007** Sistem harus menjaga traceability evidence sampai sumber data/rule yang mendasarinya.
- **BR-008** Prototipe tidak boleh memerlukan data peserta JKN nyata tanpa izin resmi.

## Business success metrics
- Risk Capture @ Review Budget.
- False Escalation Rate.
- Episode onset detection delay.
- Evidence coverage.
- Time-to-resolution (future/pilot).
- Recurrence rate (future/pilot).
