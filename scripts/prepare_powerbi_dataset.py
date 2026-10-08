"""
Script Persiapan Dataset Khusus Power BI Desktop (.PBIX Ready)
Mentransformasikan data operasional BPJS menjadi Star Schema Enterprise:
1. Fact_Kepatuhan_Bulanan.csv (Hierarki Tanggal, Kunci Relasi, Sorting Columns)
2. Fact_Intervensi_Wasrik.csv (Metrik Pemulihan Iuran, Key Dates, Flags)
3. Dim_Badan_Usaha.csv (Atribut Dimensi Perusahaan, KBLI, Wilayah)
4. Dim_Kalender.csv (Tabel Tanggal Lengkap untuk Time Intelligence DAX)
5. Dim_Sektor_KBLI.csv (Dimensi Kategori Lapangan Usaha)

Seluruh kolom diformat agar langsung terdeteksi tipe datanya oleh Power BI tanpa error transformasi.
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, date

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DATA_DIR = os.path.join(BASE_DIR, "data")
POWERBI_DATA_DIR = os.path.join(BASE_DIR, "powerbi", "data")
os.makedirs(POWERBI_DATA_DIR, exist_ok=True)

print("Memulai transformasi dataset menuju skema Power BI (.PBIX Ready)...")

# 1. BACA DATA SOURCE
df_master = pd.read_csv(os.path.join(SOURCE_DATA_DIR, "master_badan_usaha.csv"))
df_bulanan = pd.read_csv(os.path.join(SOURCE_DATA_DIR, "kepatuhan_bulanan_badan_usaha.csv"))
df_intervensi = pd.read_csv(os.path.join(SOURCE_DATA_DIR, "log_intervensi_wasrik.csv"))

# -----------------------------------------------------------------------------
# 2. GENERATE DIM_KALENDER (TABLE DATE UNTUK DAX TIME INTELLIGENCE)
# -----------------------------------------------------------------------------
print(" -> Membuat Dim_Kalender.csv (2025-01-01 s/d 2026-12-31)...")
start_date = date(2025, 1, 1)
end_date = date(2026, 12, 31)
date_range = pd.date_range(start=start_date, end=end_date, freq="D")

nama_bulan_id = {
    1: "Januari", 2: "Februari", 3: "Maret", 4: "April", 5: "Mei", 6: "Juni",
    7: "Juli", 8: "Agustus", 9: "September", 10: "Oktober", 11: "November", 12: "Desember"
}
nama_bulan_singkat_id = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "Mei", 6: "Jun",
    7: "Jul", 8: "Agu", 9: "Sep", 10: "Okt", 11: "Nov", 12: "Des"
}

kalender_rows = []
for dt in date_range:
    bln = dt.month
    thn = dt.year
    q = (bln - 1) // 3 + 1
    kalender_rows.append({
        "Tanggal": dt.strftime("%Y-%m-%d"),
        "Tahun": thn,
        "Nomor_Bulan": bln,
        "Nama_Bulan": nama_bulan_id[bln],
        "Nama_Bulan_Singkat": nama_bulan_singkat_id[bln],
        "Tahun_Bulan": f"{thn}-{bln:02d}",
        "Kuartal": f"Q{q}",
        "Tahun_Kuartal": f"{thn} Q{q}",
        "Hari_Ke_Minggu": dt.weekday() + 1,
        "Hari_Nama": dt.strftime("%A"),
        "Urutan_Tahun_Bulan": thn * 100 + bln, # Kunci pengurutan visual Power BI
        "Tanggal_Awal_Bulan": f"{thn}-{bln:02d}-01"
    })

df_dim_kalender = pd.DataFrame(kalender_rows)

# -----------------------------------------------------------------------------
# 3. GENERATE DIM_BADAN_USAHA
# -----------------------------------------------------------------------------
print(" -> Membuat Dim_Badan_Usaha.csv...")
df_dim_bu = df_master.copy()
# Tambahkan sorting key untuk skala usaha
skala_order = {"Mikro": 1, "Kecil": 2, "Menengah": 3, "Besar": 4}
df_dim_bu["urutan_skala_usaha"] = df_dim_bu["skala_usaha"].map(skala_order)

# -----------------------------------------------------------------------------
# 4. GENERATE DIM_SEKTOR_KBLI
# -----------------------------------------------------------------------------
print(" -> Membuat Dim_Sektor_KBLI.csv...")
kbli_unique = df_master[["kode_kbli", "sektor_industri"]].drop_duplicates().sort_values("kode_kbli")
kategori_risiko = {
    "C": "Risiko Tinggi", "F": "Risiko Sangat Tinggi", "G": "Risiko Moderat",
    "N": "Risiko Sangat Tinggi", "I": "Risiko Moderat", "H": "Risiko Moderat",
    "J": "Risiko Rendah", "Q": "Risiko Rendah", "A": "Risiko Tinggi", "K": "Risiko Rendah"
}
kbli_unique["kategori_profil_risiko"] = kbli_unique["kode_kbli"].map(kategori_risiko)

# -----------------------------------------------------------------------------
# 5. GENERATE FACT_KEPATUHAN_BULANAN
# -----------------------------------------------------------------------------
print(" -> Membuat Fact_Kepatuhan_Bulanan.csv...")
df_fact_bulanan = df_bulanan.copy()

# Buat relasi tanggal standar YYYY-MM-01 untuk join dengan Dim_Kalender
df_fact_bulanan["tanggal_evaluasi"] = df_fact_bulanan["periode_bulan"] + "-01"

# Sorting key untuk urgensi sistem agar warna dan hirarki di Power BI rapi
urgensi_order = {"Normal": 1, "Rendah": 2, "Sedang": 3, "Tinggi": 4, "Kritis": 5}
df_fact_bulanan["urutan_tingkat_urgensi"] = df_fact_bulanan["tingkat_urgensi_sistem"].map(urgensi_order)

# Flag boolean indikator anomali untuk filter visual instan
df_fact_bulanan["flag_anomali_naker"] = np.where(df_fact_bulanan["selisih_pekerja"] > 0, 1, 0)
df_fact_bulanan["flag_anomali_upah"] = np.where(df_fact_bulanan["selisih_upah_per_pekerja_rp"] > 0, 1, 0)
df_fact_bulanan["flag_menunggak"] = np.where(df_fact_bulanan["status_pembayaran_iuran"] == "Menunggak", 1, 0)
df_fact_bulanan["flag_bermasalah_aktif"] = np.where(df_fact_bulanan["kategori_indikasi_masalah"] != "Patuh", 1, 0)

# -----------------------------------------------------------------------------
# 6. GENERATE FACT_INTERVENSI_WASRIK
# -----------------------------------------------------------------------------
print(" -> Membuat Fact_Intervensi_Wasrik.csv...")
df_fact_intervensi = df_intervensi.copy()

# Buat tanggal evaluasi relasi ke kalender
df_fact_intervensi["tanggal_deteksi"] = df_fact_intervensi["periode_deteksi_kasus"] + "-01"
df_fact_intervensi["tanggal_intervensi"] = df_fact_intervensi["periode_intervensi"] + "-01"

# Sort key urgensi
df_fact_intervensi["urutan_tingkat_urgensi"] = df_fact_intervensi["skor_urgensi_sistem"].map(urgensi_order)

# Flag Human-in-the-Loop agreement
df_fact_intervensi["kesesuaian_rekomendasi_petugas"] = np.where(
    df_fact_intervensi["keputusan_petugas_bpjs"].str.contains("Setuju Rekomendasi"),
    "Sesuai Rekomendasi Sistem",
    "Diskresi / Penyesuaian Petugas"
)

# Flag Residivis numerik untuk DAX measure
df_fact_intervensi["flag_residivis"] = np.where(
    df_fact_intervensi["status_residivis"].str.contains("Residivis"), 1, 0
)

# Flag Resolusi Tuntas
df_fact_intervensi["flag_tuntas"] = np.where(
    df_fact_intervensi["hasil_resolusi_kasus"].str.contains("Tuntas"), 1, 0
)

# Recovery Rate per Kasus (%)
df_fact_intervensi["rasio_pemulihan_pct"] = np.round(
    (df_fact_intervensi["nominal_iuran_terpulihkan_rp"] / df_fact_intervensi["total_potensi_iuran_hilang_rp"]) * 100, 2
)

# -----------------------------------------------------------------------------
# 7. EXPORT SEMUA KE POWERBI/DATA/
# -----------------------------------------------------------------------------
file_dim_kalender = os.path.join(POWERBI_DATA_DIR, "Dim_Kalender.csv")
file_dim_bu = os.path.join(POWERBI_DATA_DIR, "Dim_Badan_Usaha.csv")
file_dim_kbli = os.path.join(POWERBI_DATA_DIR, "Dim_Sektor_KBLI.csv")
file_fact_bulanan = os.path.join(POWERBI_DATA_DIR, "Fact_Kepatuhan_Bulanan.csv")
file_fact_intervensi = os.path.join(POWERBI_DATA_DIR, "Fact_Intervensi_Wasrik.csv")

df_dim_kalender.to_csv(file_dim_kalender, index=False, encoding="utf-8-sig")
df_dim_bu.to_csv(file_dim_bu, index=False, encoding="utf-8-sig")
kbli_unique.to_csv(file_dim_kbli, index=False, encoding="utf-8-sig")
df_fact_bulanan.to_csv(file_fact_bulanan, index=False, encoding="utf-8-sig")
df_fact_intervensi.to_csv(file_fact_intervensi, index=False, encoding="utf-8-sig")

print("=" * 70)
print("BERHASIL MEMBUAT SEMUA TABEL SKEMA BINTANG (STAR SCHEMA) UNTUK POWER BI!")
print("=" * 70)
print(f"1. Dim_Kalender            : {file_dim_kalender} ({len(df_dim_kalender)} baris)")
print(f"2. Dim_Badan_Usaha         : {file_dim_bu} ({len(df_dim_bu)} baris)")
print(f"3. Dim_Sektor_KBLI         : {file_dim_kbli} ({len(kbli_unique)} baris)")
print(f"4. Fact_Kepatuhan_Bulanan  : {file_fact_bulanan} ({len(df_fact_bulanan)} baris)")
print(f"5. Fact_Intervensi_Wasrik  : {file_fact_intervensi} ({len(df_fact_intervensi)} baris)")
print("=" * 70)
