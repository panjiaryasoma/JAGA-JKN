"""
Script Generator Dataset Mentah (RAW) Intelijen Kepatuhan BPJS Kesehatan.
Menyimulasikan anomali dan "kekotoran" riil dunia operasional:
1. Human Data Entry Noise (spasi berlebih, penulisan PT/CV tidak standar, kontak null, format NPWP beragam).
2. Bank Settlement & Cut-Off Lag (transaksi tgl 10 malam terbukukan tgl 11).
3. Reporting Lag Data Eksternal (WLKP Kemnaker jeda per semester).
4. False Alarms Musiman (proyek konstruksi selesai, panen usai, bukan PDS).
5. Pekerja Ikut JKN Pasangan (legal exemption, bukan PDS).
6. True Compliance Violations (PDS-TK, PDS-Upah, Tunggakan iuran riil).

Integritas relasional (Foreign Key) TETAP DIJAGA 100% agar data valid dan dapat dilacak.
"""

import os
import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

np.random.seed(42)
random.seed(42)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

# Baca data master dan bulanan yang sudah terverifikasi sebagai ground-truth baseline
df_master_clean = pd.read_csv(os.path.join(DATA_DIR, "master_badan_usaha.csv"))
df_bulanan_clean = pd.read_csv(os.path.join(DATA_DIR, "kepatuhan_bulanan_badan_usaha.csv"))

print("Menghasilkan Layer 1: Data Mentah Operasional (RAW) dengan Anomali Realistis...")

# -----------------------------------------------------------------------------
# 1. GENERATE RAW MASTER BADAN USAHA (Human Input Noise)
# -----------------------------------------------------------------------------
raw_master_rows = []

for idx, row in df_master_clean.iterrows():
    nama_ori = row["nama_badan_usaha"]
    bentuk = row["bentuk_badan_hukum"]
    
    # Injeksi variasi penulisan nama (typo/spasi/casing) pada ~30% data
    dice_noise = random.random()
    if dice_noise < 0.10:
        # Tambah spasi ganda
        nama_raw = nama_ori.replace(" ", "  ")
    elif dice_noise < 0.20:
        # Huruf kecil semua atau kapital semua
        nama_raw = nama_ori.lower() if random.random() < 0.5 else nama_ori.upper()
    elif dice_noise < 0.30:
        # Variasi tanda titik (PT. vs PT)
        if nama_ori.startswith("PT "):
            nama_raw = "PT. " + nama_ori[3:]
        elif nama_ori.startswith("CV "):
            nama_raw = "CV. " + nama_ori[3:]
        else:
            nama_raw = nama_ori
    else:
        nama_raw = nama_ori

    # Format NPWP: ada yang terformat dengan titik/strip, ada yang angka murni, ada yang null (usaha mikro)
    npwp_digits = f"{random.randint(10, 99)}{random.randint(100, 999)}{random.randint(100, 999)}{random.randint(1, 9)}{random.randint(100, 999)}{random.randint(100, 999)}"
    if row["skala_usaha"] == "Mikro" and random.random() < 0.25:
        npwp_raw = np.nan  # NPWP belum terdaftar / null
    elif random.random() < 0.60:
        # Terformat resmi: XX.XXX.XXX.X-XXX.XXX
        npwp_raw = f"{npwp_digits[:2]}.{npwp_digits[2:5]}.{npwp_digits[5:8]}.{npwp_digits[8]}-{npwp_digits[9:12]}.{npwp_digits[12:]}"
    else:
        npwp_raw = npwp_digits  # Angka polos

    # Format nomor telepon PIC HRD: beragam format (+62, 08, 021, atau null)
    if random.random() < 0.08:
        telp_raw = np.nan  # Kontak kosong
    elif random.random() < 0.40:
        telp_raw = f"+62 8{random.randint(11, 99)}-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}"
    elif random.random() < 0.70:
        telp_raw = f"08{random.randint(11, 99)}{random.randint(10000000, 99999999)}"
    else:
        telp_raw = f"(021) {random.randint(5000000, 8999999)}"

    # Email PIC HRD (12% data null)
    if random.random() < 0.12:
        email_raw = np.nan
    else:
        domain = random.choice(["perusahaan.co.id", "gmail.com", "corp.id", "yahoo.com", "business.id"])
        pic_clean = row["nama_pic_hrd"].lower().replace(" ", ".")
        email_raw = f"{pic_clean}@{domain}"

    # Status verifikasi berkas pendaftaran di BPJS
    status_berkas = random.choice(["Terverifikasi Lengkap", "Terverifikasi Lengkap", "Terverifikasi Lengkap", 
                                   "Data Migrasi Legacy Askes", "Menunggu Pemutakhiran NPWP"])

    raw_master_rows.append({
        "id_badan_usaha": row["id_badan_usaha"],  # FK tetap bersih & valid!
        "nama_badan_usaha_raw": nama_raw,
        "bentuk_badan_hukum": bentuk,
        "kode_kbli": row["kode_kbli"],
        "sektor_industri": row["sektor_industri"],
        "skala_usaha": row["skala_usaha"],
        "provinsi": row["provinsi"],
        "kantor_cabang_bpjs": row["kantor_cabang_bpjs"],
        "kode_kantor_cabang": row["kode_kantor_cabang"],
        "ump_provinsi_2026": row["ump_provinsi_2026"],
        "npwp_badan_usaha": npwp_raw,
        "nomor_va_bpjs": row["nomor_va_bpjs"],
        "nama_pic_hrd": row["nama_pic_hrd"],
        "nomor_telepon_pic": telp_raw,
        "email_pic_hrd": email_raw,
        "tanggal_registrasi_bpjs": row["tanggal_registrasi_bpjs"],
        "status_kelengkapan_berkas": status_berkas
    })

df_raw_master = pd.DataFrame(raw_master_rows)

# -----------------------------------------------------------------------------
# 2. GENERATE RAW KEPATUHAN BULANAN (Reporting Lags, Bank Settlement, False Alarms)
# -----------------------------------------------------------------------------
raw_bulanan_rows = []

# Buat kamus sektor untuk referensi cepat
sektor_dict = dict(zip(df_master_clean["id_badan_usaha"], df_master_clean["kode_kbli"]))
skala_dict = dict(zip(df_master_clean["id_badan_usaha"], df_master_clean["skala_usaha"]))

for idx, row in df_bulanan_clean.iterrows():
    bu_id = row["id_badan_usaha"]
    periode = row["periode_bulan"]
    kbli = sektor_dict[bu_id]
    skala = skala_dict[bu_id]
    
    naker_seharusnya = row["jumlah_pekerja_seharusnya"]
    naker_terdaftar = row["jumlah_pekerja_terdaftar_jkn"]
    upah_seharusnya = row["rata_rata_upah_seharusnya_rp"]
    upah_lapor = row["rata_rata_upah_dilaporkan_rp"]
    status_bayar_clean = row["status_pembayaran_iuran"]
    iuran_tertagih = row["iuran_tertagih_edabu_rp"]
    
    # ---------------- ANOMALI 1: BANK CUT-OFF & SETTLEMENT LATENCY ----------------
    # Perusahaan sebenarnya bayar tepat tanggal 10 sebelum tengah malam (23:30),
    # tapi mutasi bank baru terbukukan tanggal 11 dini hari.
    # Jika sistem naif membaca tgl 11, sistem menganggap "Terlambat".
    ada_delay_bank = False
    if status_bayar_clean == "Tepat Waktu" and random.random() < 0.15: # 15% bayar di ujung waktu (tgl 10 malam)
        ada_delay_bank = True
        jam_bayar = f"23:{random.randint(10, 58):02d}:{random.randint(10, 58):02d}"
        timestamp_bayar_nasabah = f"{periode}-10 {jam_bayar}"
        # Bank membukukan tanggal 11 pukul 00:00 - 02:00
        timestamp_mutasi_bank = f"{periode}-11 0{random.randint(0, 2)}:{random.randint(10, 58):02d}:00"
        status_bayar_raw = "Terlambat (Sistem Bank)"  # Raw capture bank
    elif status_bayar_clean == "Tepat Waktu":
        tgl_bayar = random.randint(2, 9)
        jam_bayar = f"{random.randint(8, 17):02d}:{random.randint(10, 58):02d}:{random.randint(10, 58):02d}"
        timestamp_bayar_nasabah = f"{periode}-{tgl_bayar:02d} {jam_bayar}"
        timestamp_mutasi_bank = timestamp_bayar_nasabah
        status_bayar_raw = "Tepat Waktu"
    elif status_bayar_clean == "Terlambat":
        tgl_bayar = min(28, 10 + row["hari_keterlambatan_bayar"])
        jam_bayar = f"{random.randint(8, 17):02d}:{random.randint(10, 58):02d}:{random.randint(10, 58):02d}"
        timestamp_bayar_nasabah = f"{periode}-{tgl_bayar:02d} {jam_bayar}"
        timestamp_mutasi_bank = timestamp_bayar_nasabah
        status_bayar_raw = "Terlambat"
    else: # Menunggak
        timestamp_bayar_nasabah = np.nan
        timestamp_mutasi_bank = np.nan
        status_bayar_raw = "Belum Ada Pembayaran"

    # ---------------- ANOMALI 2: REPORTING LAG WLKP KEMNAKER ----------------
    # WLKP hanya update per semester (Juni & Desember). Pada bulan lain, data WLKP
    # sering tertinggal 1-3 bulan dari data mutasi naker aktual di lapangan.
    bln_int = int(periode.split("-")[1])
    lag_wlkp_bulan = 0
    if bln_int in [2, 3, 4, 5]:
        lag_wlkp_bulan = bln_int - 1  # data masih posisi Desember tahun lalu
        status_data_wlkp = f"Posisi Data WLKP Tertinggal {lag_wlkp_bulan} Bulan"
    elif bln_int in [8, 9, 10, 11]:
        lag_wlkp_bulan = bln_int - 7  # data masih posisi Juni tahun berjalan
        status_data_wlkp = f"Posisi Data WLKP Tertinggal {lag_wlkp_bulan} Bulan"
    else:
        status_data_wlkp = "Data WLKP Baru Terverifikasi (Sinkronisasi Semester)"

    # Angka naker tercatat di portal Kemnaker (bisa sedikit berbeda karena lag)
    if lag_wlkp_bulan > 0 and random.random() < 0.25:
        naker_tercatat_kemnaker = max(3, naker_seharusnya + random.randint(-4, 4))
    else:
        naker_tercatat_kemnaker = naker_seharusnya

    # ---------------- ANOMALI 3: FALSE POSITIVE MUSIMAN / PROYEK SELESAI ----------------
    # Di sektor Konstruksi (F) atau Pertanian/Perkebunan (A), pengurangan naker seringkali
    # karena proyek konstruksi selesai termin atau musim panen usai (bukan PDS-TK!).
    indikasi_proyek_selesai = False
    alasan_mutasi_lapangan = "Normal"
    
    if kbli in ["F", "A"] and row["kategori_indikasi_masalah"] == "Patuh" and random.random() < 0.08:
        # Ada pengurangan naker riil legal
        indikasi_proyek_selesai = True
        alasan_mutasi_lapangan = "Pekerjaan Proyek Lapangan Selesai / Kontrak PKWT Berakhir Legal"

    # ---------------- ANOMALI 4: PEKERJA IKUT TANGGUNGAN JKN PASANGAN ----------------
    # Pekerja (terutama wanita bersuami yang suaminya PNS/BUMN/TNI/Polri atau PPU di BU lain)
    # memilih tetap terdaftar di bawah kartu keluarga pasangan.
    # Ini legal dan BUKAN PDS Tenaga Kerja!
    if skala in ["Menengah", "Besar"]:
        pekerja_ikut_pasangan = random.randint(1, 6)
    else:
        pekerja_ikut_pasangan = random.randint(0, 1)

    raw_bulanan_rows.append({
        "id_badan_usaha": bu_id,
        "periode_bulan": periode,
        "naker_tercatat_wlkp_kemnaker": naker_tercatat_kemnaker,
        "status_pemutakhiran_wlkp": status_data_wlkp,
        "naker_terdaftar_edabu_bpjs": naker_terdaftar,
        "naker_terverifikasi_ikut_pasangan": pekerja_ikut_pasangan,
        "selisih_naker_mentah": naker_tercatat_kemnaker - naker_terdaftar,
        "rata_rata_upah_spt_pajak_rp": upah_seharusnya,
        "rata_rata_upah_lapor_edabu_rp": upah_lapor,
        "selisih_upah_mentah_rp": upah_seharusnya - upah_lapor,
        "tagihan_iuran_edabu_rp": iuran_tertagih,
        "nominal_terbayar_kas_bpjs_rp": row["iuran_terbayar_rp"],
        "status_pembayaran_raw": status_bayar_raw,
        "timestamp_pembayaran_nasabah": timestamp_bayar_nasabah,
        "timestamp_mutasi_bank": timestamp_mutasi_bank,
        "flag_delay_cut_off_bank": ada_delay_bank,
        "alasan_mutasi_lapangan": alasan_mutasi_lapangan,
        "indikator_proyek_musiman": indikasi_proyek_selesai,
        "status_kepatuhan_ground_truth": row["kategori_indikasi_masalah"] # Sebagai label validasi ground truth
    })

df_raw_bulanan = pd.DataFrame(raw_bulanan_rows)

# -----------------------------------------------------------------------------
# 3. EXPORT FILE RAW KE CSV
# -----------------------------------------------------------------------------
file_raw_master = os.path.join(DATA_DIR, "raw_master_badan_usaha.csv")
file_raw_bulanan = os.path.join(DATA_DIR, "raw_kepatuhan_bulanan_badan_usaha.csv")

df_raw_master.to_csv(file_raw_master, index=False, encoding="utf-8-sig")
df_raw_bulanan.to_csv(file_raw_bulanan, index=False, encoding="utf-8-sig")

print("=" * 65)
print("BERHASIL MEMBUAT LAYER DATA MENTAH (RAW) DENGAN NOISE REALISTIS!")
print("=" * 65)
print(f"1. Raw Master Badan Usaha    : {file_raw_master} ({len(df_raw_master)} baris)")
print(f"2. Raw Kepatuhan Bulanan Panel: {file_raw_bulanan} ({len(df_raw_bulanan)} baris)")
print("=" * 65)
