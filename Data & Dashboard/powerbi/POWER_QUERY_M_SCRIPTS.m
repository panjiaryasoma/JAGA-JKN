// ==============================================================================
// JAGA-JKN: POWER QUERY M SCRIPTS (CANONICAL REBIND)
// Sesuai dengan Kontrak Data powerbi/data/ dan parameter DataRoot
// ==============================================================================

// ------------------------------------------------------------------------------
// PARAMETER: DataRoot
// Atur nilai DataRoot pada menu Home -> Manage Parameters di Power BI Desktop.
// Contoh path lokal: "C:/Users/linta/OneDrive/Documents/Hackathon BPJS/Dataset/JAGA-JKN/powerbi/data"
// Tanpa tanda garis miring (slash) di akhir.
// ------------------------------------------------------------------------------
let
    DataRoot = "C:/Users/linta/OneDrive/Documents/Hackathon BPJS/Dataset/JAGA-JKN/powerbi/data" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
in
    DataRoot

// ------------------------------------------------------------------------------
// TABEL DIMENSI 1: Dim_Badan_Usaha
// ------------------------------------------------------------------------------
let
    Source = Csv.Document(File.Contents(DataRoot & "/Dim_Badan_Usaha.csv"),[Delimiter=",", Columns=10, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{
        {"id_badan_usaha", type text},
        {"nama_badan_usaha_terstandarisasi", type text},
        {"bentuk_badan_hukum", type text},
        {"kode_kbli", type text},
        {"sektor_industri", type text},
        {"skala_usaha", type text},
        {"provinsi", type text},
        {"kantor_cabang_bpjs", type text},
        {"synthetic_assumption_version", type text},
        {"urutan_skala_usaha", Int64.Type}
    })
in
    #"Changed Type"

// ------------------------------------------------------------------------------
// TABEL DIMENSI 2: Dim_Kalender
// ------------------------------------------------------------------------------
let
    Source = Csv.Document(File.Contents(DataRoot & "/Dim_Kalender.csv"),[Delimiter=",", Columns=6, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{
        {"Tanggal", type date},
        {"Tahun", Int64.Type},
        {"Nomor_Bulan", Int64.Type},
        {"Tahun_Bulan", type text},
        {"Urutan_Tahun_Bulan", Int64.Type},
        {"Tanggal_Awal_Bulan", type date}
    })
in
    #"Changed Type"

// ------------------------------------------------------------------------------
// TABEL DIMENSI 3: Dim_Sektor_KBLI
// ------------------------------------------------------------------------------
let
    Source = Csv.Document(File.Contents(DataRoot & "/Dim_Sektor_KBLI.csv"),[Delimiter=",", Columns=3, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{
        {"kode_kbli", type text},
        {"sektor_industri", type text},
        {"sector_prior_status", type text}
    })
in
    #"Changed Type"

// ------------------------------------------------------------------------------
// TABEL FAKTA 1: Fact_Risk_Evidence (Observasi Risiko, Bukti, dan Status Regulasi)
// ------------------------------------------------------------------------------
let
    Source = Csv.Document(File.Contents(DataRoot & "/Fact_Risk_Evidence.csv"),[Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{
        {"id_badan_usaha", type text},
        {"periode_bulan", type text},
        {"tanggal_evaluasi", type date},
        {"registration_discrepancy_detected", type logical},
        {"registration_rule_result", type text},
        {"registration_rule_reason", type text},
        {"registration_review_state", type text},
        {"registration_review_reason", type text},
        {"registration_evidence_quality", type text},
        {"registration_evidence_valid", type logical},
        {"registration_rule_id", type text},
        {"registration_authority_authorized", type logical},
        {"registration_authority_id", type text},
        {"registration_rule_version", type text},
        {"registration_applicable_period_verified", type logical},
        {"wage_discrepancy_detected", type logical},
        {"wage_rule_result", type text},
        {"wage_rule_reason", type text},
        {"wage_review_state", type text},
        {"wage_review_reason", type text},
        {"wage_evidence_quality", type text},
        {"wage_evidence_valid", type logical},
        {"wage_rule_id", type text},
        {"wage_authority_authorized", type logical},
        {"wage_authority_id", type text},
        {"wage_rule_version", type text},
        {"wage_applicable_period_verified", type logical},
        {"contribution_payment_gap_observed", type logical},
        {"contribution_rule_result", type text},
        {"contribution_rule_reason", type text},
        {"contribution_review_state", type text},
        {"contribution_review_reason", type text},
        {"contribution_evidence_quality", type text},
        {"contribution_evidence_valid", type logical},
        {"contribution_rule_id", type text},
        {"contribution_authority_authorized", type logical},
        {"contribution_authority_id", type text},
        {"contribution_rule_version", type text},
        {"contribution_applicable_period_verified", type logical},
        {"overall_review_state", type text},
        {"human_review_recommendation", type text},
        {"observed_discrepancy_types", type text},
        {"estimated_exposure_synthetic_rp", Int64.Type},
        {"exposure_decision_role", type text},
        {"is_synthetic", type logical},
        {"flag_reviewable", Int64.Type},
        {"flag_needs_enrichment", Int64.Type},
        {"flag_abstain", Int64.Type},
        {"flag_governance_blocked", Int64.Type},
        {"flag_needs_human_attention", Int64.Type},
        {"exposure_label", type text},
        {"presentation_contract", type text}
    })
in
    #"Changed Type"

// ------------------------------------------------------------------------------
// TABEL FAKTA 2: Fact_Human_Review_Synthetic (Log Audit Tinjauan Petugas)
// ------------------------------------------------------------------------------
let
    Source = Csv.Document(File.Contents(DataRoot & "/Fact_Human_Review_Synthetic.csv"),[Delimiter=",", Columns=10, Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{
        {"id_review", type text},
        {"id_badan_usaha", type text},
        {"periode_review", type text},
        {"system_recommendation", type text},
        {"human_review_outcome_synthetic", type text},
        {"simulated_resolution_state", type text},
        {"synthetic_outcome_assumption", type logical},
        {"is_synthetic", type logical},
        {"tanggal_review", type date},
        {"outcome_label", type text}
    })
in
    #"Changed Type"
