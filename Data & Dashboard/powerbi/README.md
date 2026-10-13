# JAGA-JKN: Panduan Rebind Power BI & Audit Integritas Data

Dokumen ini adalah panduan resmi integrasi (*rebind*) model Power BI Desktop terhadap dataset sintetis kanonis yang telah divalidasi pada repositori **JAGA-JKN** (`powerbi/data/`).

---

## 1. Prinsip Tata Kelola & Integritas Data

Sesuai kontrak data dan dokumen strategi tata kelola JAGA-JKN:
1. **Pemisahan Diskrepansi vs Vonis Pelanggaran:**  
   Sistem mencatat diskrepansi fisik/administratif (`registration_discrepancy_detected`, `wage_discrepancy_detected`, `contribution_payment_gap_observed`), **bukan** vonis pelanggaran hukum.
2. **Kualitas Bukti (Evidence Quality Triage):**  
   Setiap diskrepansi dipilah berdasarkan kekuatan bukti:
   * **HIGH:** Bukti terverifikasi silang (layak ditelaah petugas).
   * **MEDIUM:** Bukti membutuhkan validasi dokumen pembanding.
   * **LOW:** Bukti awal belum memadai (wajib pengayaan data/enrichment, dilarang langsung ditindak).
3. **Prinsip Fail-Closed (Tata Kelola Regulasi):**  
   Karena otoritas regulasi B1/B2 belum disahkan dalam sandbox prototipe ini, seluruh aturan sistem mengembalikan status **ABSTAIN** (`flag_governance_blocked = 1`). Dashboard menyajikan fakta objektif tanpa membuat asumsi pelanggaran sepihak.
4. **Status Netral Sektor Industri:**  
   Kolom `sector_prior_status` pada `Dim_Sektor_KBLI` berstatus `NO_EMPIRICAL_PRIOR__DO_NOT_INFER_SIGNAL_FROM_SECTOR_ALONE`. Sistem tidak membuat stereotip risiko berbasis sektor tanpa bukti empiris entitas.
5. **Estimasi Paparan Finansial Bukan Kerugian Riil:**  
   `estimated_exposure_synthetic_rp` diberi label `SIMULATED_ESTIMATE__NOT_EMPIRICAL_LOSS__NOT_FOR_DECISION`.

---

## 2. Sumber Data Kanonis (`powerbi/data/`)

Model Power BI terhubung ke 5 tabel berstruktur Star Schema yang dihasilkan langsung dari pipeline data kurasi:

| Nama File | Tipe Tabel | Jumlah Baris | Kunci Utama / Relasi | Deskripsi |
| :--- | :--- | :---: | :--- | :--- |
| `Dim_Badan_Usaha.csv` | Dimensi | 500 | `id_badan_usaha` (PK) | Profil entitas terstandarisasi, skala, KBLI, cabang BPJS |
| `Dim_Kalender.csv` | Dimensi | 730 | `Tanggal` (PK) | Kalender harian 2025-01-01 s.d. 2026-12-31 |
| `Dim_Sektor_KBLI.csv` | Dimensi | 10 | `kode_kbli` (PK) | Klasifikasi baku lapangan usaha dan status prior |
| `Fact_Risk_Evidence.csv` | Fakta Inti | 12.000 | `(id_badan_usaha, periode_bulan)` | Observasi bulanan, diskrepansi, kualitas bukti, exposure |
| `Fact_Human_Review_Synthetic.csv` | Fakta Pendukung | 244 | `id_review` (PK) | Log audit peninjauan oleh petugas (*human-in-the-loop*) |

---

## 3. Cara Menjalankan & Memuat Ulang di Power BI Desktop

1. **Buka File Laporan:**  
   Buka file `powerbi/POWER BI BPJS.pbix` menggunakan Power BI Desktop.
2. **Atur Parameter `DataRoot`:**  
   * Klik tab **Home** -> klik dropdown **Transform data** -> pilih **Edit parameters**.
   * Pada parameter **DataRoot**, masukkan path folder data lokal Anda (tanpa tanda slash di akhir), contoh:  
     `C:/Users/linta/OneDrive/Documents/Hackathon BPJS/Dataset/JAGA-JKN/powerbi/data`
   * Klik **OK**, lalu klik **Apply Changes**.
3. **Periksa Power Query M Scripts:**  
   Jika membuat model dari nol, buka **Advanced Editor** pada masing-masing query dan gunakan skrip dari file `powerbi/POWER_QUERY_M_SCRIPTS.m`.
4. **Terapkan DAX Measures:**  
   Salin dan pasang formula DAX dari file `powerbi/DAX_MEASURES_BPJS.dax` untuk seluruh visual kartu KPI, grafik, dan tabel.

---

## 4. Struktur Relasi Model (Star Schema)

* `Dim_Badan_Usaha[id_badan_usaha]` **(1) — (*) `Fact_Risk_Evidence[id_badan_usaha]`**
* `Dim_Kalender[Tanggal]` **(1) — (*) `Fact_Risk_Evidence[tanggal_evaluasi]`**
* `Dim_Sektor_KBLI[kode_kbli]` **(1) — (*) `Dim_Badan_Usaha[kode_kbli]`**
* `Dim_Badan_Usaha[id_badan_usaha]` **(1) — (*) `Fact_Human_Review_Synthetic[id_badan_usaha]`**
* `Dim_Kalender[Tanggal]` **(1) — (*) `Fact_Human_Review_Synthetic[tanggal_review]`**

---

## 5. Bukti Hasil Pengujian Otomatis (*Test & Audit Evidence*)

Pengujian integritas data, konsistensi relasi kunci, dan keselarasan formula DAX dijalankan menggunakan test suite otomatis:

```bash
python tests/test_powerbi_data_rebind.py -v
```

### Ringkasan Hasil Pengujian:
```text
test_dax_mathematical_equivalents ... ok
test_evidence_quality_triage ... ok
test_file_row_counts ... ok
test_governance_fail_closed_contract ... ok
test_human_review_log_integrity ... ok
test_relational_integrity_foreign_keys ... ok

----------------------------------------------------------------------
Ran 6 tests in 0.300s

OK
```

### Matriks Verifikasi Angka Sumber vs Dashboard:

| Metrik / Indikator | Nilai Kanonis Sumber CSV | Status Uji | Keterangan Tata Kelola |
| :--- | :---: | :---: | :--- |
| **Total Entitas Terpantau** | 500 BU | **PASS** | 500 badan usaha unik |
| **Total Periode Observasi** | 12.000 baris | **PASS** | 24 bulan (Jan 2025 - Des 2026) |
| **Diskrepansi Kepesertaan** | 4.189 kasus (34,9%) | **PASS** | `registration_discrepancy_detected` |
| ↳ *Kualitas Bukti HIGH* | 1.316 kasus (31,4%) | **PASS** | Siap ditelaah petugas |
| ↳ *Kualitas Bukti MEDIUM* | 1.170 kasus (27,9%) | **PASS** | Butuh pengayaan dokumen |
| ↳ *Kualitas Bukti LOW* | 1.703 kasus (40,7%) | **PASS** | Bukti lemah / belum memadai |
| **Diskrepansi Upah Teramati** | 1.509 kasus (12,6%) | **PASS** | `wage_discrepancy_detected` |
| **Gap Pembayaran Iuran** | 1.628 kasus (13,6%) | **PASS** | `contribution_payment_gap_observed` |
| **Total Kasus Terindikasi** | 5.873 kasus (48,9%) | **PASS** | Minimal 1 diskrepansi teramati |
| **Total Estimasi Paparan** | Rp 142.433.794.809 | **PASS** | *Simulated estimate*, bukan kerugian riil |
| **Kasus Diblokir Regulasi** | 12.000 kasus (100%) | **PASS** | *Fail-closed* (B1/B2 unresolved) |
| **Log Tinjauan Petugas** | 244 peristiwa | **PASS** | Tinjauan manusia (*Human-in-the-loop*) |
| ↳ *Dikonfirmasi Petugas* | 163 kasus (66,8%) | **PASS** | `REVIEW_CONFIRMED` |
| ↳ *Minta Tambahan Bukti* | 57 kasus (23,4%) | **PASS** | `REQUEST_MORE_EVIDENCE` |
| ↳ *Tanpa Tindakan Lanjut* | 24 kasus (9,8%) | **PASS** | `NO_ACTION_AFTER_REVIEW` |
| ↳ *Resolusi: Monitoring* | 92 kasus (37,7%) | **PASS** | Dalam pemantauan berkala |
| ↳ *Resolusi: Open* | 77 kasus (31,6%) | **PASS** | Kasus berjalan |
| ↳ *Resolusi: Resolved* | 75 kasus (30,7%) | **PASS** | Kasus selesai tuntas |
