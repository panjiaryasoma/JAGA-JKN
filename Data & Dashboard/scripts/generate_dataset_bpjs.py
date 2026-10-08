"""
Script Generator Dataset Intelijen Kepatuhan Pemberi Kerja BPJS Kesehatan (JKN)
Didesain khusus untuk Hackathon BPJS: Valid, Realistis, Sesuai Regulasi Nasional (Perpres 64/2020 & PP 86/2013).
Menghasilkan 4 berkas CSV terintegrasi relasional:
1. master_badan_usaha.csv
2. kepatuhan_bulanan_badan_usaha.csv (Panel time-series 24 bulan: 2025-01 s/d 2026-12)
3. log_intervensi_wasrik.csv (Closed-loop tracking dari deteksi -> rekomendasi -> aksi -> hasil)
4. dataset_intelijen_kepatuhan_ml.csv (Feature table siap training model Machine Learning)
"""

import os
import random
import numpy as np
import pandas as pd
from datetime import datetime, date

# Set random seed untuk hasil deterministik dan dapat di-reproduksi
np.random.seed(42)
random.seed(42)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# -----------------------------------------------------------------------------
# 1. PARAMETER REGULASI & DATA MASTER REFERENSI
# -----------------------------------------------------------------------------
BATAS_ATAS_UPAH = 12000000.0  # Plafon upah maksimal perhitungan iuran JKN (Perpres 64/2020)
TARIF_TOTAL = 0.05            # 5% total iuran JKN PPU
TARIF_BU = 0.04               # 4% ditanggung Badan Usaha (pemberi kerja)
TARIF_PEKERJA = 0.01          # 1% dipotong dari pekerja

REFERENSI_WILAYAH = [
    {"provinsi": "DKI Jakarta", "kc": "KC Jakarta Pusat", "ump_2026": 5729876, "kode_kc": "0101", "bobot": 0.22},
    {"provinsi": "Jawa Barat", "kc": "KC Bandung", "ump_2026": 2317601, "kode_kc": "0201", "bobot": 0.18},
    {"provinsi": "Banten", "kc": "KC Tangerang", "ump_2026": 3100881, "kode_kc": "0205", "bobot": 0.12},
    {"provinsi": "Jawa Timur", "kc": "KC Surabaya", "ump_2026": 2446880, "kode_kc": "0301", "bobot": 0.14},
    {"provinsi": "Jawa Tengah", "kc": "KC Semarang", "ump_2026": 2327386, "kode_kc": "0305", "bobot": 0.10},
    {"provinsi": "Sumatera Utara", "kc": "KC Medan", "ump_2026": 3228949, "kode_kc": "0401", "bobot": 0.07},
    {"provinsi": "Riau", "kc": "KC Pekanbaru", "ump_2026": 3780495, "kode_kc": "0403", "bobot": 0.05},
    {"provinsi": "Kalimantan Timur", "kc": "KC Balikpapan", "ump_2026": 3762431, "kode_kc": "0501", "bobot": 0.04},
    {"provinsi": "Sulawesi Selatan", "kc": "KC Makassar", "ump_2026": 3921088, "kode_kc": "0601", "bobot": 0.05},
    {"provinsi": "Bali", "kc": "KC Denpasar", "ump_2026": 3207459, "kode_kc": "0701", "bobot": 0.03}
]

SEKTOR_KBLI = [
    {"kode": "C", "nama": "Industri Pengolahan / Manufaktur", "prob_pds_tk": 0.28, "prob_pds_upah": 0.20},
    {"kode": "F", "nama": "Konstruksi & Infrastruktur", "prob_pds_tk": 0.40, "prob_pds_upah": 0.25},
    {"kode": "G", "nama": "Perdagangan Besar dan Eceran", "prob_pds_tk": 0.18, "prob_pds_upah": 0.28},
    {"kode": "N", "nama": "Jasa Penunjang Usaha (Alih Daya / Outsourcing / Security)", "prob_pds_tk": 0.48, "prob_pds_upah": 0.35},
    {"kode": "I", "nama": "Penyediaan Akomodasi dan F&B (Restoran & Hotel)", "prob_pds_tk": 0.25, "prob_pds_upah": 0.25},
    {"kode": "H", "nama": "Transportasi, Pergudangan & Logistik", "prob_pds_tk": 0.20, "prob_pds_upah": 0.18},
    {"kode": "J", "nama": "Informasi dan Komunikasi / Teknologi", "prob_pds_tk": 0.06, "prob_pds_upah": 0.10},
    {"kode": "Q", "nama": "Aktivitas Pelayanan Kesehatan & Rumah Sakit Swasta", "prob_pds_tk": 0.05, "prob_pds_upah": 0.08},
    {"kode": "A", "nama": "Pertanian, Perkebunan Kelapa Sawit & Kehutanan", "prob_pds_tk": 0.35, "prob_pds_upah": 0.15},
    {"kode": "K", "nama": "Jasa Keuangan, Pembiayaan dan Asuransi", "prob_pds_tk": 0.03, "prob_pds_upah": 0.05}
]

NAMA_WASRIK_LIST = [
    "Budi Santoso, S.E. (Pemeriksa Madya)",
    "Siti Rahmawati, S.H. (Pemeriksa Muda)",
    "Agus Hermawan, S.Kom. (Analis Wasrik)",
    "Dewi Lestari, S.E., M.M. (Pemeriksa Madya)",
    "Rian Hidayat, S.H. (Pemeriksa Pertama)",
    "Nurul Hasanah, S.Ak. (Analis Kepatuhan)",
    "Eko Prasetyo, S.H. (Pemeriksa Madya)",
    "Indah Permata, S.E. (Pemeriksa Pertama)",
    "Fajar Ramadhan, S.ST. (Analis Wasrik)",
    "Dian Sastrowardoyo, S.H. (Pemeriksa Muda)"
]

N_PERUSAHAAN = 500
BULAN_LIST = [f"{thn}-{bln:02d}" for thn in [2025, 2026] for bln in range(1, 13)]  # 24 bulan

print(f"Menghasilkan data untuk {N_PERUSAHAAN} Badan Usaha selama {len(BULAN_LIST)} bulan ({BULAN_LIST[0]} s/d {BULAN_LIST[-1]})...")

# -----------------------------------------------------------------------------
# 2. GENERATE MASTER BADAN USAHA
# -----------------------------------------------------------------------------
master_bu_rows = []

awalan_nama = ["PT", "PT", "PT", "CV", "CV", "Yayasan", "Koperasi"]
kata1 = ["Nusantara", "Bina", "Cipta", "Mandiri", "Sentosa", "Prima", "Makmur", "Sejahtera", "Daya", "Karya", 
         "Mega", "Inti", "Mitra", "Surya", "Adhi", "Wijaya", "Tri", "Garuda", "Sumber", "Sinar", "Harapan", "Bumi"]
kata2 = ["Tekstil", "Logistik", "Konstruksi", "Pangan", "Solusindo", "Teknologi", "Garda Utama", "Katering Prima", 
         "Ritel Modern", "Perkasa", "Plastindo", "Farmasi Medika", "Hospitality", "Oto Perkasa", "Agro Makmur", "Distribusindo",
         "Multi Karya", "Sarana Jaya", "Duta Abadi", "Lintas Samudera"]

# Profil dasar kecenderungan perilaku BU
PROFIL_PERILAKU = [
    "Patuh_Konsisten",     # 52% selalu sinkron dan tertib
    "Rentan_PDS_TK",       # 16% sering tidak daftarkan pegawai kontrak/naker baru
    "Rentan_PDS_Upah",     # 12% lapor upah di bawah riil / lapor hanya batas UMP
    "Rentan_Tunggakan",    # 10% naker dan upah benar tapi cashflow seret menunggak
    "Nakal_Kombinasi",     # 6% PDS TK + PDS Upah + Nunggak
    "Residivis_Kambuhan"   # 4% sempat patuh setelah ditegur, lalu kumat lagi di tahun ke-2
]
PROFIL_WEIGHTS = [0.52, 0.16, 0.12, 0.10, 0.06, 0.04]

wilayah_weights = [w["bobot"] for w in REFERENSI_WILAYAH]

for i in range(1, N_PERUSAHAAN + 1):
    bu_id = f"BU-{i:04d}"
    wilayah = np.random.choice(REFERENSI_WILAYAH, p=wilayah_weights)
    sektor = random.choice(SEKTOR_KBLI)
    bentuk_hukum = random.choice(awalan_nama)
    nama_bu = f"{bentuk_hukum} {random.choice(kata1)} {random.choice(kata2)}"
    profil = np.random.choice(PROFIL_PERILAKU, p=PROFIL_WEIGHTS)
    
    # Skala Badan Usaha berdasarkan tenaga kerja awal
    skala_choice = np.random.choice(["Mikro", "Kecil", "Menengah", "Besar"], p=[0.15, 0.40, 0.32, 0.13])
    if skala_choice == "Mikro":
        baseline_naker = random.randint(4, 9)
    elif skala_choice == "Kecil":
        baseline_naker = random.randint(10, 49)
    elif skala_choice == "Menengah":
        baseline_naker = random.randint(50, 199)
    else:
        baseline_naker = random.randint(200, 850)
        
    # Baseline upah rata-rata (harus >= UMP)
    ump = wilayah["ump_2026"]
    if skala_choice in ["Mikro", "Kecil"]:
        baseline_upah = round(ump * random.uniform(1.0, 1.45), -3)
    elif skala_choice == "Menengah":
        baseline_upah = round(ump * random.uniform(1.15, 2.10), -3)
    else:
        baseline_upah = round(ump * random.uniform(1.30, 2.80), -3)
    
    # Tahun daftar BPJS (2014 - 2024)
    thn_reg = random.randint(2014, 2024)
    bln_reg = random.randint(1, 12)
    tgl_reg = f"{thn_reg}-{bln_reg:02d}-{random.randint(1,28):02d}"
    
    va_bpjs = f"88888{random.randint(1000000000, 9999999999)}"
    pic_hrd = f"{random.choice(['Bambang', 'Lina', 'Hendra', 'Ratna', 'Yusuf', 'Fitri', 'Doni', 'Maya', 'Reza', 'Mega'])} {random.choice(['Kusuma', 'Pratama', 'Saputra', 'Handayani', 'Hidayat', 'Kurniawan', 'Utami'])}"
    
    master_bu_rows.append({
        "id_badan_usaha": bu_id,
        "nama_badan_usaha": nama_bu,
        "bentuk_badan_hukum": bentuk_hukum,
        "kode_kbli": sektor["kode"],
        "sektor_industri": sektor["nama"],
        "skala_usaha": skala_choice,
        "provinsi": wilayah["provinsi"],
        "kantor_cabang_bpjs": wilayah["kc"],
        "kode_kantor_cabang": wilayah["kode_kc"],
        "ump_provinsi_2026": ump,
        "tanggal_registrasi_bpjs": tgl_reg,
        "nomor_va_bpjs": va_bpjs,
        "nama_pic_hrd": pic_hrd,
        "profil_kepatuhan_dasar": profil,
        "baseline_tenaga_kerja": baseline_naker,
        "baseline_upah_riil": baseline_upah
    })

df_master_bu = pd.DataFrame(master_bu_rows)

# -----------------------------------------------------------------------------
# 3. GENERATE TIME-SERIES BULANAN & SIMULASI DESINKRONISASI REALISTIS
# -----------------------------------------------------------------------------
bulanan_rows = []
intervensi_rows = []
kasus_counter = 1

for idx_bu, bu in df_master_bu.iterrows():
    bu_id = bu["id_badan_usaha"]
    profil = bu["profil_kepatuhan_dasar"]
    ump = bu["ump_provinsi_2026"]
    curr_naker_riil = bu["baseline_tenaga_kerja"]
    curr_upah_riil = bu["baseline_upah_riil"]
    
    # State tracking longitudinal
    masalah_aktif = False
    jenis_masalah_aktif = None
    durasi_masalah_berjalan = 0
    bulan_mulai_masalah = None
    status_intervensi_berjalan = "Belum Ada"
    telah_diintervensi = False
    bulan_intervensi = None
    terjadi_recidivisme = False
    intervensi_kedua_done = False
    
    # Tentukan kapan masalah mulai muncul untuk BU yang bermasalah
    # Agar ada fase "Sebelum Masalah", "Mulai Desinkronisasi", "Makin Parah", "Intervensi", "Pemulihan / Kambuh"
    if profil == "Patuh_Konsisten":
        bulan_trigger = None
    elif profil == "Residivis_Kambuhan":
        bulan_trigger = 3    # Mulai April 2025, selesai sekitar Okt 2025, kumat Mei 2026
    else:
        bulan_trigger = random.randint(2, 8) # Mulai antara Feb - Agu 2025
        
    for idx_bln, periode in enumerate(BULAN_LIST):
        # Sedikit fluktuasi alami pada tenaga kerja riil (perekrutan / turnover wajar 0-5%)
        fluktuasi = np.random.choice([-2, -1, 0, 1, 2], p=[0.1, 0.2, 0.4, 0.2, 0.1])
        curr_naker_riil = max(3, curr_naker_riil + fluktuasi)
        
        # Penyesuaian upah tahunan di Januari 2026 (+4% s/d 7%)
        if periode == "2026-01":
            curr_upah_riil = round(curr_upah_riil * random.uniform(1.04, 1.07), -3)
            
        # Ground truth ketenagakerjaan seharusnya (WLKP Kemnaker / Pajak / BPJSTK)
        naker_seharusnya = curr_naker_riil
        upah_seharusnya = curr_upah_riil
        
        # Hitung iuran seharusnya (Perpres 64/2020: 5% upah di-cap Rp 12.000.000, minimal UMP)
        upah_dasar_seharusnya = min(BATAS_ATAS_UPAH, max(ump, upah_seharusnya))
        iuran_seharusnya = round(naker_seharusnya * upah_dasar_seharusnya * TARIF_TOTAL)
        
        # ---------------- LOGIKA SIMULASI MASALAH ----------------
        if bulan_trigger is not None and idx_bln >= bulan_trigger:
            if not masalah_aktif and not telah_diintervensi:
                masalah_aktif = True
                bulan_mulai_masalah = periode
                if profil == "Rentan_PDS_TK":
                    jenis_masalah_aktif = "PDS Tenaga Kerja"
                elif profil == "Rentan_PDS_Upah":
                    jenis_masalah_aktif = "PDS Upah"
                elif profil == "Rentan_Tunggakan":
                    jenis_masalah_aktif = "Tunggakan Iuran"
                elif profil == "Nakal_Kombinasi":
                    jenis_masalah_aktif = "PDS Kombinasi"
                elif profil == "Residivis_Kambuhan":
                    jenis_masalah_aktif = "PDS Tenaga Kerja"

        # Cek apakah kambuh (Recidivism) untuk profil Residivis_Kambuhan
        if profil == "Residivis_Kambuhan" and telah_diintervensi and idx_bln >= 16: # Mei 2026 kumat
            if not masalah_aktif:
                masalah_aktif = True
                terjadi_recidivisme = True
                bulan_mulai_masalah = periode
                jenis_masalah_aktif = "PDS Tenaga Kerja"
                durasi_masalah_berjalan = 0
                status_intervensi_berjalan = "Belum Ada"

        # Tentukan kondisi aktual di Edabu BPJS
        if not masalah_aktif:
            # Kondisi PATUH
            naker_terdaftar = naker_seharusnya
            upah_dilaporkan = upah_seharusnya
            durasi_masalah_berjalan = 0
            kategori_masalah = "Patuh"
            tren_gap = "Stabil Patuh"
            
            # Pembayaran tertib tepat waktu (antara tgl 1 - 9, jatuh tempo tgl 10)
            tgl_bayar_int = random.randint(2, 9)
            status_bayar = "Tepat Waktu"
            hari_terlambat = 0
            iuran_tertagih = iuran_seharusnya
            iuran_terbayar = iuran_seharusnya
            denda_iuran = 0
            
        else:
            # Kondisi BERMASALAH (Mulai dari gap kecil, lalu membesar / persisten)
            durasi_masalah_berjalan += 1
            
            # Simulasi gap membesar seiring waktu jika tidak ditangani
            faktor_keparahan = min(1.0, 0.25 + (durasi_masalah_berjalan * 0.15))
            
            # Default awal
            naker_terdaftar = naker_seharusnya
            upah_dilaporkan = upah_seharusnya
            status_bayar = "Tepat Waktu"
            hari_terlambat = 0
            
            if jenis_masalah_aktif in ["PDS Tenaga Kerja", "PDS Kombinasi"]:
                # BU tidak mendaftarkan karyawan kontrak/baru (misal 10% s/d 45% karyawan disembunyikan)
                persen_sembunyi = min(0.50, 0.12 * durasi_masalah_berjalan)
                karyawan_disembunyikan = max(1, int(round(naker_seharusnya * persen_sembunyi)))
                naker_terdaftar = max(1, naker_seharusnya - karyawan_disembunyikan)
                
            if jenis_masalah_aktif in ["PDS Upah", "PDS Kombinasi"]:
                # BU memotong lapor upah (hanya lapor batas UMP atau diskon 20-40%)
                upah_dilaporkan = max(ump, round(upah_seharusnya * (1.0 - (0.15 * faktor_keparahan)), -3))
                
            # Hitung iuran tertagih di portal Edabu
            upah_dasar_lapor = min(BATAS_ATAS_UPAH, max(ump, upah_dilaporkan))
            iuran_tertagih = round(naker_terdaftar * upah_dasar_lapor * TARIF_TOTAL)
            
            if jenis_masalah_aktif in ["Tunggakan Iuran", "PDS Kombinasi"]:
                # Pembayaran telat atau macet
                if durasi_masalah_berjalan == 1:
                    status_bayar = "Terlambat"
                    hari_terlambat = random.randint(5, 18)
                    iuran_terbayar = iuran_tertagih
                    denda_iuran = round(iuran_tertagih * 0.02)
                else:
                    status_bayar = "Menunggak"
                    hari_terlambat = 30 * min(6, durasi_masalah_berjalan)
                    iuran_terbayar = 0
                    # Denda 0.1% per bulan sesuai PP 86/2013 atau denda layanan
                    denda_iuran = round(iuran_tertagih * 0.01 * min(12, durasi_masalah_berjalan))
            else:
                status_bayar = "Tepat Waktu"
                hari_terlambat = 0
                iuran_terbayar = iuran_tertagih
                denda_iuran = 0
                
            kategori_masalah = jenis_masalah_aktif
            
            # Tentukan tren perkembangan gap
            if durasi_masalah_berjalan == 1:
                tren_gap = "Baru Muncul"
            elif durasi_masalah_berjalan in [2, 3]:
                tren_gap = "Memburuk"
            else:
                tren_gap = "Persisten Memburuk"

        # Hitung selisih dan kerugian iuran
        selisih_naker = naker_seharusnya - naker_terdaftar
        rasio_kepatuhan_naker = round((naker_terdaftar / naker_seharusnya) * 100, 2)
        
        selisih_upah = upah_seharusnya - upah_dilaporkan
        rasio_pelaporan_upah = round((upah_dilaporkan / upah_seharusnya) * 100, 2)
        
        # Selisih iuran potensi hilang = Iuran Seharusnya - Iuran Terbayar
        selisih_iuran_hilang = max(0, iuran_seharusnya - iuran_terbayar)
        
        # ---------------- LEVEL URGENSI SISTEM INTELIJEN ----------------
        if kategori_masalah == "Patuh":
            urgensi = "Normal"
            rekomendasi_sistem = "Tidak Perlu Tindakan"
        elif durasi_masalah_berjalan == 1 and selisih_iuran_hilang < 5000000 and status_bayar != "Menunggak":
            urgensi = "Rendah"
            rekomendasi_sistem = "Notifikasi Otomatis Portal Edabu"
        elif durasi_masalah_berjalan in [2, 3] and status_bayar != "Menunggak":
            urgensi = "Sedang"
            rekomendasi_sistem = "Surat Klarifikasi & Permintaan Pemutakhiran Data"
        elif durasi_masalah_berjalan in [4, 5] or status_bayar == "Menunggak" or selisih_iuran_hilang > 25000000:
            urgensi = "Tinggi"
            rekomendasi_sistem = "Surat Teguran Tertulis I & Jadwal Audit Wasrik Lapangan"
        else:
            urgensi = "Kritis"
            rekomendasi_sistem = "Surat Teguran Tertulis II & Pelimpahan SKK Datun Kejaksaan"

        # ---------------- SIMULASI ALUR KEPUTUSAN PETUGAS & INTERVENSI ----------------
        # Jika masalah sudah berjalan 3-4 bulan dan belum ada intervensi aktif untuk episode ini
        perlu_intervensi = False
        if masalah_aktif and durasi_masalah_berjalan >= 3:
            if not telah_diintervensi:
                perlu_intervensi = True
            elif terjadi_recidivisme and not intervensi_kedua_done:
                # Kasus berulang / kambuhan
                perlu_intervensi = True
                intervensi_kedua_done = True

        if perlu_intervensi:
            telah_diintervensi = True
            bulan_intervensi = periode
            
            # Buat record di log_intervensi_wasrik
            id_kasus = f"CAS-{periode[:4]}-{kasus_counter:04d}"
            kasus_counter += 1
            
            # Petugas meninjau rekomendasi sistem
            petugas = random.choice(NAMA_WASRIK_LIST)
            
            # Jika residivis, rekomendasi sistem otomatis dinaikkan levelnya
            if terjadi_recidivisme:
                rekomendasi_sistem = "Pemeriksaan Lapangan Khusus (Audit Investigasi Pelanggaran Berulang)"
                urgensi = "Kritis"

            # Respon petugas (85% setuju AI, 15% diskresi / penyesuaian lapangan)
            dice_petugas = random.random()
            if terjadi_recidivisme:
                keputusan_petugas = "Setuju Rekomendasi: Audit Lapangan & Usulan Sanksi TMP2T (Residivis)"
            elif dice_petugas < 0.85:
                keputusan_petugas = f"Setuju Rekomendasi: {rekomendasi_sistem}"
            elif dice_petugas < 0.95:
                keputusan_petugas = "Penyesuaian: Beri Dispensasi Cicilan Tunggakan (Restrukturisasi)"
            else:
                keputusan_petugas = "Eskalasi Cepat: Langsung Pemeriksaan Gabungan Bersama Disnaker"
                
            # Efektivitas tindakan terhadap Badan Usaha
            if terjadi_recidivisme:
                respon_bu = "Kooperatif Setelah Diberi Peringatan Keras Wasrik & Disnaker"
                hasil_akhir = "Tuntas - Pemutakhiran Data Wajib dengan Pengawasan Berkala"
                durasi_resolusi_hari = random.randint(20, 45)
                nominal_recovery = round(selisih_iuran_hilang * durasi_masalah_berjalan * 0.98)
            elif profil in ["Rentan_PDS_TK", "Rentan_PDS_Upah", "Residivis_Kambuhan"]:
                respon_bu = "Kooperatif - Memperbaiki Data & Mendaftarkan Seluruh Pekerja"
                hasil_akhir = "Tuntas - Patuh Kembali Penuh"
                durasi_resolusi_hari = random.randint(14, 45)
                nominal_recovery = round(selisih_iuran_hilang * durasi_masalah_berjalan * 0.95)
            elif profil == "Rentan_Tunggakan":
                respon_bu = "Kooperatif - Menandatangani Komitmen Pembayaran Bertahap"
                hasil_akhir = "Tuntas - Restrukturisasi Iuran Disetujui"
                durasi_resolusi_hari = random.randint(30, 60)
                nominal_recovery = round(selisih_iuran_hilang * 0.85)
            else: # Nakal_Kombinasi
                respon_bu = "Pasif / Menolak - Diberikan Teguran Keras & Diusulkan Sanksi TMP2T"
                hasil_akhir = "Eskalasi Hukum - SKK Kejaksaan Negeri (Datun)"
                durasi_resolusi_hari = random.randint(60, 120)
                nominal_recovery = round(selisih_iuran_hilang * 0.50)
                
            flag_residivis_kasus = "Residivis (Masalah Berulang)" if terjadi_recidivisme else "Kasus Baru Pertama"
            
            intervensi_rows.append({
                "id_kasus": id_kasus,
                "id_badan_usaha": bu_id,
                "nama_badan_usaha": bu["nama_badan_usaha"],
                "kantor_cabang_bpjs": bu["kantor_cabang_bpjs"],
                "periode_deteksi_kasus": bulan_mulai_masalah,
                "periode_intervensi": periode,
                "jenis_pelanggaran": kategori_masalah,
                "durasi_sebelum_ditindak_bulan": durasi_masalah_berjalan,
                "total_potensi_iuran_hilang_rp": selisih_iuran_hilang * durasi_masalah_berjalan,
                "skor_urgensi_sistem": urgensi,
                "rekomendasi_tindakan_sistem": rekomendasi_sistem,
                "keputusan_petugas_bpjs": keputusan_petugas,
                "nama_petugas_wasrik": petugas,
                "respon_badan_usaha": respon_bu,
                "hasil_resolusi_kasus": hasil_akhir,
                "waktu_penyelesaian_hari": durasi_resolusi_hari,
                "nominal_iuran_terpulihkan_rp": nominal_recovery,
                "status_residivis": flag_residivis_kasus
            })
            
            # Jika BU kooperatif, masalah pulih dalam bulan berikutnya!
            if "Tuntas" in hasil_akhir and profil != "Nakal_Kombinasi":
                masalah_aktif = False
                # Di bulan berikutnya BU kembali patuh

        # Simpan record bulanan
        bulanan_rows.append({
            "id_badan_usaha": bu_id,
            "periode_bulan": periode,
            "jumlah_pekerja_seharusnya": naker_seharusnya,
            "jumlah_pekerja_terdaftar_jkn": naker_terdaftar,
            "selisih_pekerja": selisih_naker,
            "rasio_kepatuhan_kepesertaan_pct": rasio_kepatuhan_naker,
            "rata_rata_upah_seharusnya_rp": upah_seharusnya,
            "rata_rata_upah_dilaporkan_rp": upah_dilaporkan,
            "selisih_upah_per_pekerja_rp": selisih_upah,
            "rasio_pelaporan_upah_pct": rasio_pelaporan_upah,
            "iuran_seharusnya_rp": iuran_seharusnya,
            "iuran_tertagih_edabu_rp": iuran_tertagih,
            "iuran_terbayar_rp": iuran_terbayar,
            "selisih_iuran_potensial_rp": selisih_iuran_hilang,
            "status_pembayaran_iuran": status_bayar,
            "hari_keterlambatan_bayar": hari_terlambat,
            "denda_keterlambatan_rp": denda_iuran,
            "kategori_indikasi_masalah": kategori_masalah,
            "durasi_masalah_berjalan_bulan": durasi_masalah_berjalan,
            "tren_perkembangan_gap": tren_gap,
            "tingkat_urgensi_sistem": urgensi,
            "rekomendasi_tindakan_otomatis": rekomendasi_sistem
        })

df_bulanan = pd.DataFrame(bulanan_rows)
df_intervensi = pd.DataFrame(intervensi_rows)

# -----------------------------------------------------------------------------
# 4. GENERATE DATASET MACHINE LEARNING (SNAPSHOT FEATURE TABLE SIAP MODEL)
# -----------------------------------------------------------------------------
# Mengagregasi histori 24 bulan per Badan Usaha menjadi tabular feature vector
# Fitur-fitur ini sangat ideal untuk pemodelan ML (Prediksi Jenis Masalah, Klasifikasi Preskriptif, Recidivism Risk)
ml_feature_rows = []

for idx_bu, bu in df_master_bu.iterrows():
    bu_id = bu["id_badan_usaha"]
    df_sub = df_bulanan[df_bulanan["id_badan_usaha"] == bu_id]
    
    # Metrik agregat time-series
    avg_gap_naker = df_sub["selisih_pekerja"].mean()
    max_gap_naker = df_sub["selisih_pekerja"].max()
    avg_gap_upah = df_sub["selisih_upah_per_pekerja_rp"].mean()
    max_gap_upah = df_sub["selisih_upah_per_pekerja_rp"].max()
    total_iuran_hilang = df_sub["selisih_iuran_potensial_rp"].sum()
    frekuensi_telat_bayar = (df_sub["status_pembayaran_iuran"] != "Tepat Waktu").sum()
    max_bulan_tunggak = df_sub["durasi_masalah_berjalan_bulan"].max()
    
    # Ambil snapshot kondisi bulan terakhir (2026-12)
    last_row = df_sub.iloc[-1]
    
    # Riwayat intervensi
    intervensi_bu = df_intervensi[df_intervensi["id_badan_usaha"] == bu_id]
    pernah_ditegur = 1 if len(intervensi_bu) > 0 else 0
    pernah_residivis = 1 if (len(intervensi_bu) > 0 and (intervensi_bu["status_residivis"].str.contains("Residivis")).any()) else 0
    
    # Target prediksi untuk Hackathon
    label_kategori = last_row["kategori_indikasi_masalah"]
    label_urgensi = last_row["tingkat_urgensi_sistem"]
    label_rekomendasi = last_row["rekomendasi_tindakan_otomatis"]
    
    ml_feature_rows.append({
        "id_badan_usaha": bu_id,
        "bentuk_badan_hukum": bu["bentuk_badan_hukum"],
        "kode_kbli": bu["kode_kbli"],
        "sektor_industri": bu["sektor_industri"],
        "skala_usaha": bu["skala_usaha"],
        "provinsi": bu["provinsi"],
        "ump_provinsi_2026": bu["ump_provinsi_2026"],
        "jumlah_pekerja_seharusnya_saat_ini": last_row["jumlah_pekerja_seharusnya"],
        "jumlah_pekerja_terdaftar_saat_ini": last_row["jumlah_pekerja_terdaftar_jkn"],
        "selisih_pekerja_saat_ini": last_row["selisih_pekerja"],
        "rasio_kepatuhan_naker_saat_ini": last_row["rasio_kepatuhan_kepesertaan_pct"],
        "rata_rata_upah_seharusnya_saat_ini": last_row["rata_rata_upah_seharusnya_rp"],
        "rata_rata_upah_dilaporkan_saat_ini": last_row["rata_rata_upah_dilaporkan_rp"],
        "selisih_upah_saat_ini": last_row["selisih_upah_per_pekerja_rp"],
        "rasio_pelaporan_upah_saat_ini": last_row["rasio_pelaporan_upah_pct"],
        "status_bayar_terakhir": last_row["status_pembayaran_iuran"],
        "durasi_masalah_aktif_bulan": last_row["durasi_masalah_berjalan_bulan"],
        "tren_perkembangan_gap": last_row["tren_perkembangan_gap"],
        # Fitur Agregat Historis (24 Bulan)
        "rata_rata_selisih_naker_24bln": round(avg_gap_naker, 2),
        "maksimal_selisih_naker_24bln": max_gap_naker,
        "rata_rata_selisih_upah_24bln": round(avg_gap_upah, 2),
        "maksimal_selisih_upah_24bln": max_gap_upah,
        "total_kerugian_iuran_historis_rp": total_iuran_hilang,
        "frekuensi_keterlambatan_bayar_24bln": frekuensi_telat_bayar,
        "durasi_masalah_terpanjang_bulan": max_bulan_tunggak,
        "pernah_diintervensi_wasrik": pernah_ditegur,
        "riwayat_pernah_residivis": pernah_residivis,
        # Target Label Modeling
        "target_kategori_masalah": label_kategori,
        "target_tingkat_urgensi": label_urgensi,
        "target_rekomendasi_tindakan": label_rekomendasi,
        "target_potensi_kerugian_iuran_bln_ini_rp": last_row["selisih_iuran_potensial_rp"]
    })

df_ml = pd.DataFrame(ml_feature_rows)

# -----------------------------------------------------------------------------
# 5. EXPORT SEMUA KE CSV
# -----------------------------------------------------------------------------
file_master = os.path.join(OUTPUT_DIR, "master_badan_usaha.csv")
file_bulanan = os.path.join(OUTPUT_DIR, "kepatuhan_bulanan_badan_usaha.csv")
file_intervensi = os.path.join(OUTPUT_DIR, "log_intervensi_wasrik.csv")
file_ml = os.path.join(OUTPUT_DIR, "dataset_intelijen_kepatuhan_ml.csv")

df_master_bu.to_csv(file_master, index=False, encoding="utf-8-sig")
df_bulanan.to_csv(file_bulanan, index=False, encoding="utf-8-sig")
df_intervensi.to_csv(file_intervensi, index=False, encoding="utf-8-sig")
df_ml.to_csv(file_ml, index=False, encoding="utf-8-sig")

print("=" * 60)
print("BERHASIL MEMBUAT SEMUA DATASET BPJS KESEHATAN!")
print("=" * 60)
print(f"1. Master Badan Usaha: {file_master} ({len(df_master_bu)} baris)")
print(f"2. Kepatuhan Bulanan Panel: {file_bulanan} ({len(df_bulanan)} baris)")
print(f"3. Log Intervensi Wasrik: {file_intervensi} ({len(df_intervensi)} baris)")
print(f"4. Dataset Intelijen ML: {file_ml} ({len(df_ml)} baris)")
print("=" * 60)
