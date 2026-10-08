// =============================================================================
// POWER QUERY (M) SCRIPTS - ADVANCED EDITOR
// SISTEM INTELIJEN KEPATUHAN PEMBERI KERJA (ECIS) BPJS KESEHATAN
// Buka Advanced Editor pada masing-masing tabel dan ganti seluruh teksnya.
// =============================================================================

// -----------------------------------------------------------------------------
// 1. QUERY: Dim_Badan_Usaha
// -----------------------------------------------------------------------------
let
    Source = Csv.Document(File.Contents("C:\Users\linta\OneDrive\Documents\Hackathon BPJS\Dataset\powerbi\data\Dim_Badan_Usaha.csv"),[Delimiter=",", Columns=17, Encoding=65001, QuoteStyle=QuoteStyle.None]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{
        {"id_badan_usaha", type text},
        {"nama_badan_usaha", type text},
        {"bentuk_badan_hukum", type text},
        {"kode_kbli", type text},
        {"sektor_industri", type text},
        {"skala_usaha", type text},
        {"provinsi", type text},
        {"kantor_cabang_bpjs", type text},
        {"kode_kantor_cabang", type text},
        {"ump_provinsi_2026", type number},
        {"tanggal_registrasi_bpjs", type date},
        {"nomor_va_bpjs", type text},
        {"nama_pic_hrd", type text},
        {"profil_kepatuhan_dasar", type text},
        {"baseline_tenaga_kerja", Int64.Type},
        {"baseline_upah_riil", type number},
        {"urutan_skala_usaha", Int64.Type}
    })
in
    #"Changed Type"


// -----------------------------------------------------------------------------
// 2. QUERY: Dim_Kalender
// -----------------------------------------------------------------------------
let
    Source = Csv.Document(File.Contents("C:\Users\linta\OneDrive\Documents\Hackathon BPJS\Dataset\powerbi\data\Dim_Kalender.csv"),[Delimiter=",", Columns=12, Encoding=65001, QuoteStyle=QuoteStyle.None]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{
        {"Tanggal", type date},
        {"Tahun", Int64.Type},
        {"Nomor_Bulan", Int64.Type},
        {"Nama_Bulan", type text},
        {"Nama_Bulan_Singkat", type text},
        {"Tahun_Bulan", type text},
        {"Kuartal", type text},
        {"Tahun_Kuartal", type text},
        {"Hari_Ke_Minggu", Int64.Type},
        {"Hari_Nama", type text},
        {"Urutan_Tahun_Bulan", Int64.Type},
        {"Tanggal_Awal_Bulan", type date}
    })
in
    #"Changed Type"


// -----------------------------------------------------------------------------
// 3. QUERY: Dim_Sektor_KBLI
// -----------------------------------------------------------------------------
let
    Source = Csv.Document(File.Contents("C:\Users\linta\OneDrive\Documents\Hackathon BPJS\Dataset\powerbi\data\Dim_Sektor_KBLI.csv"),[Delimiter=",", Columns=3, Encoding=65001, QuoteStyle=QuoteStyle.None]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{
        {"kode_kbli", type text},
        {"sektor_industri", type text},
        {"kategori_profil_risiko", type text}
    })
in
    #"Changed Type"


// -----------------------------------------------------------------------------
// 4. QUERY: Fact_Kepatuhan_Bulanan
// -----------------------------------------------------------------------------
let
    Source = Csv.Document(File.Contents("C:\Users\linta\OneDrive\Documents\Hackathon BPJS\Dataset\powerbi\data\Fact_Kepatuhan_Bulanan.csv"),[Delimiter=",", Columns=28, Encoding=65001, QuoteStyle=QuoteStyle.None]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{
        {"id_badan_usaha", type text},
        {"periode_bulan", type text},
        {"jumlah_pekerja_seharusnya", Int64.Type},
        {"jumlah_pekerja_terdaftar_jkn", Int64.Type},
        {"selisih_pekerja", Int64.Type},
        {"rasio_kepatuhan_kepesertaan_pct", type number},
        {"rata_rata_upah_seharusnya_rp", type number},
        {"rata_rata_upah_dilaporkan_rp", type number},
        {"selisih_upah_per_pekerja_rp", type number},
        {"rasio_pelaporan_upah_pct", type number},
        {"iuran_seharusnya_rp", type number},
        {"iuran_tertagih_edabu_rp", type number},
        {"iuran_terbayar_rp", type number},
        {"selisih_iuran_potensial_rp", type number},
        {"status_pembayaran_iuran", type text},
        {"hari_keterlambatan_bayar", Int64.Type},
        {"denda_keterlambatan_rp", type number},
        {"kategori_indikasi_masalah", type text},
        {"durasi_masalah_berjalan_bulan", Int64.Type},
        {"tren_perkembangan_gap", type text},
        {"tingkat_urgensi_sistem", type text},
        {"rekomendasi_tindakan_otomatis", type text},
        {"tanggal_evaluasi", type date},
        {"urutan_tingkat_urgensi", Int64.Type},
        {"flag_anomali_naker", Int64.Type},
        {"flag_anomali_upah", Int64.Type},
        {"flag_menunggak", Int64.Type},
        {"flag_bermasalah_aktif", Int64.Type}
    })
in
    #"Changed Type"


// -----------------------------------------------------------------------------
// 5. QUERY: Fact_Intervensi_Wasrik
// -----------------------------------------------------------------------------
let
    Source = Csv.Document(File.Contents("C:\Users\linta\OneDrive\Documents\Hackathon BPJS\Dataset\powerbi\data\Fact_Intervensi_Wasrik.csv"),[Delimiter=",", Columns=25, Encoding=65001, QuoteStyle=QuoteStyle.None]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{
        {"id_kasus", type text},
        {"id_badan_usaha", type text},
        {"nama_badan_usaha", type text},
        {"kantor_cabang_bpjs", type text},
        {"periode_deteksi_kasus", type text},
        {"periode_intervensi", type text},
        {"jenis_pelanggaran", type text},
        {"durasi_sebelum_ditindak_bulan", Int64.Type},
        {"total_potensi_iuran_hilang_rp", type number},
        {"skor_urgensi_sistem", type text},
        {"rekomendasi_tindakan_sistem", type text},
        {"keputusan_petugas_bpjs", type text},
        {"nama_petugas_wasrik", type text},
        {"respon_badan_usaha", type text},
        {"hasil_resolusi_kasus", type text},
        {"waktu_penyelesaian_hari", Int64.Type},
        {"nominal_iuran_terpulihkan_rp", type number},
        {"status_residivis", type text},
        {"tanggal_deteksi", type date},
        {"tanggal_intervensi", type date},
        {"urutan_tingkat_urgensi", Int64.Type},
        {"kesesuaian_rekomendasi_petugas", type text},
        {"flag_residivis", Int64.Type},
        {"flag_tuntas", Int64.Type},
        {"rasio_pemulihan_pct", type number}
    })
in
    #"Changed Type"
