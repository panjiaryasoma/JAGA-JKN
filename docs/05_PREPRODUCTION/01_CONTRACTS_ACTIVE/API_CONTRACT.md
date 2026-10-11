---
project: JAGA-JKN
status: DRAFT
version: 0.2.0
owner: Panji
authority: Backend API Implementation Contract
last_updated: 2026-10-09
---

# API contract — backend prototipe v1

Target implementasi dan pengujian pada branch backend sesuai instruksi pemilik proyek. Penerimaan produk tetap DRAFT; ini tidak mengesahkan B1/B2 atau fitur/label ML. Requirement BE-001..BE-019 mengacu PRD.

## Endpoint

JSON UTF-8. Prototipe dijalankan pada loopback. Endpoint baca snapshot/health/capabilities bersifat publik; kasus dan /me memerlukan Bearer token demo. Deployment publik/data nyata memerlukan kontrak akses tersendiri. Dokumentasi: /docs; OpenAPI: /openapi.json.

| Method | Path | Respons berhasil |
|---|---|---|
| GET | /health/live | 200, status alive tanpa dependensi dataset |
| GET | /health/ready | 200, status ready dan dataset_id jika snapshot valid serta database bisa dibuka dengan schema v1 |
| GET | /api/v1/dataset | 200, envelope metadata snapshot |
| GET | /api/v1/badan-usaha | 200, envelope halaman profil |
| GET | /api/v1/badan-usaha/{id_badan_usaha} | 200, envelope satu profil |
| GET | /api/v1/badan-usaha/{id_badan_usaha}/evidence | 200, envelope halaman bukti bulanan |
| GET | /api/v1/badan-usaha/{id_badan_usaha}/evidence/{periode_bulan} | 200, envelope satu bukti bulanan |
| GET | /api/v1/dashboard?periode_bulan=YYYY-MM | 200, agregat satu bulan eksplisit |
| GET | /api/v1/capabilities | 200, status masing-masing komponen |
| GET | /api/v1/ml/status | 200, NOT_CONFIGURED; prediction_available false |

ID: BU- diikuti tepat empat angka. Periode: bulan kalender YYYY-MM, tahun 0001–9999. Bulan simulasi di masa depan sah. ID/bulan sah yang tidak ditemukan → 404; format salah → 422. Riwayat kosong setelah filter → 200 data kosong; perusahaan tidak ada tetap 404.

## Query

Daftar: q (1–100 karakter setelah trim, substring nama/ID case-insensitive), provinsi/skala_usaha/kode_kbli (exact-match, 1–100 karakter), page (default 1), page_size (default 20).

Riwayat: period_from/period_to opsional dan inklusif, page (default 1), page_size (default 24). Rentang terbalik → 422. Urutan ID/bulan ascending. Page 1–100000, page_size 1–100; angka query berupa integer desimal positif tanpa pecahan. Halaman di luar hasil → daftar kosong dengan total sama. Filter sebelum pagination. Parameter tidak dikenal/duplikat → 422 pada endpoint yang didefinisikan.

## Envelope

Respons data: {data: ..., meta: {dataset_id: "sha256:...", source_commit: "<40 hex>", is_synthetic: true, ml_status: "NOT_CONFIGURED", policy_status: "UNRESOLVED"}}.

Respons daftar menambahkan pagination: {page, page_size, total, total_pages}; total_pages=0 bila total=0. Dataset ID adalah hash JSON kanonis manifest yang mengikat hash kedua CSV. source_commit merupakan provenance yang dideklarasikan manifest administrator; kecocokan byte dibuktikan SHA-256, tanpa klaim pemeriksaan asal Git secara online.

Metadata: jumlah perusahaan/baris bukti, periode simulasi, versi asumsi, seed aktual (baseline 42/43), nama dan SHA-256 file. Profil hanya berisi id_badan_usaha, nama_badan_usaha (nama terstandarisasi dari kurasi), bentuk_badan_hukum, kode_kbli, sektor_industri, skala_usaha, provinsi, kantor_cabang_bpjs. Teks kosong yang sah → null.

## Bukti bulanan

Record: id_badan_usaha, periode_bulan, source_record_id, registration, wage, contribution, overall_review_state, human_review_recommendation, observed_discrepancy_types.

Setiap kelompok mempertahankan evidence_valid, evidence_quality, evidence_reasons, source_metadata_valid, period_binding_valid, source_ids, source_periods, rule_id, rule_result, rule_reason, review_state, review_reason, lineage, authority (authorized/id/rule_version/applicable_period_verified/effective_from/effective_to/source_ids).

- Registration: reference_worker_count, observed_registered_worker_count, missing_worker_count, unexpected_worker_count, discrepancy_detected, worker_set_valid, worker_set_error, explanation_metadata_valid, explanation_reason.
- Wage: reference_wage_signal_rp, observed_wage_signal_rp, wage_discrepancy_signal_rp, discrepancy_detected, semantic_consistency_valid.
- Contribution: observed_payment_state, validated_payment_state, payment_gap_observed, semantic_consistency_valid, payment_evidence_reason.

Prefix kelompok dihilangkan bila sudah terwakili objek; suffix _json menjadi array. Token daftar NONE → array kosong. Angka kosong → null, bukan 0. Rupiah integer eksak maksimum 2^53−1 tanpa float. Boolean CSV hanya True/False; kosong hanya untuk observasi nullable. UNKNOWN pada validated_payment_state dipertahankan. Data rusak tidak dipulihkan dengan default kosong.

Baseline menerima rule/review ABSTAIN, authority false/UNVERIFIED, applicable_period_verified false, serta periode otorisasi null. Perubahan membutuhkan kontrak berikutnya; API tidak menghitung ulang aturan. Mutu HIGH/MEDIUM/LOW terpisah dari keputusan. Label ground truth, profil simulator, worker IDs, NPWP, telepon, dan exposure tidak termasuk respons mana pun.

## Integritas dan pemuatan

CSV dimuat sekali saat lifespan dari root lokal, maksimal 64 MiB/file; manifest maksimal 64 KiB. Hash dan parsing memakai byte yang sama. Manifest hanya menerima dua nama CSV kurasi. Snapshot immutable; perubahan file di disk tidak mengubah snapshot proses yang telah siap. Restart untuk memuat snapshot baru. HTTP tidak menerima upload, URL sumber, atau path lokal.

Loader memeriksa tipe/enum, kolom wajib/header duplikat, jumlah baris, ID unik, kunci perusahaan-bulan/source_record_id unik, foreign key, tanggal, dan grid lengkap sesuai periode manifest. is_synthetic setiap record harus true. Angka/boolean/JSON rusak dan status baseline tak didukung ditolak. File hilang → DATASET_UNAVAILABLE; manifest/hash/struktur salah → DATASET_INVALID. Readiness dan API data menjadi 503, liveness tetap 200. Tidak ada reload otomatis atau dataset kosong sebagai fallback.

## Error dan log

Envelope: {error: {code, message, request_id, details: []}}. Detail validasi: location, code, message; tanpa salinan nilai input. Server membuat UUID untuk setiap request; X-Request-ID keluaran sama dengan body error. ID dari header input tidak digunakan.

| HTTP | Code |
|---|---|
| 404 | NOT_FOUND |
| 405 | METHOD_NOT_ALLOWED (header Allow dipertahankan) |
| 422 | VALIDATION_ERROR |
| 401 | UNAUTHORIZED (WWW-Authenticate: Bearer) |
| 403 | FORBIDDEN |
| 409 | CASE_ALREADY_OPEN / INVALID_TRANSITION / OPEN_INTERVENTIONS / INVALID_RECURRENCE / IDEMPOTENCY_CONFLICT |
| 412 | VERSION_CONFLICT |
| 428 | PRECONDITION_REQUIRED |
| 503 | DATASET_UNAVAILABLE / DATASET_INVALID / PERSISTENCE_UNAVAILABLE / AUTH_NOT_CONFIGURED |
| 500 | INTERNAL_ERROR |

Input baca diperiksa sebelum ketersediaan dataset; autentikasi dapat mendahului validasi pada endpoint terlindungi. Log akses: request ID, method, template route, status, durasi; tanpa query/body/nama/ID badan usaha. CORS tidak dibuka otomatis. Cache-Control: no-store pada semua respons. OpenAPI menggunakan model kode dan mendokumentasikan envelope error.

## Dashboard dan kemampuan

Dashboard mewajibkan periode_bulan yang ada di snapshot. Respons memakai envelope data/meta, memuat periode_bulan, company_count, serta kelompok registration/wage/contribution. Masing-masing kelompok memuat discrepancy {true,false,unknown}, quality {HIGH,MEDIUM,LOW}, abstain_count. Contribution menghitung payment_gap_observed. Jumlah kategori tiap kelompok sama dengan company_count. Tidak menggabungkan observasi menjadi skor risiko. Periode yang sah tetapi tidak tersedia → 404.

Capabilities memakai {data: {scope: SYNTHETIC_PROTOTYPE, snapshot, case_store, authentication, ml, policy}}. Status snapshot/database AVAILABLE/UNAVAILABLE; auth DEMO_STATIC_TOKEN/NOT_CONFIGURED, ML NOT_CONFIGURED, policy UNRESOLVED. Database diperiksa kembali pada setiap request readiness/capabilities. Readiness menguji koneksi dan schema, bukan jaminan kapasitas disk atau durability infrastruktur. Dataset yang telah dimuat tetap tersedia dari memory walaupun file sumber dihapus; database hilang menghasilkan 503 tanpa membuat database kosong selama proses berjalan.

## Endpoint workflow terlindungi

Authorization: Bearer <token>. Identitas dan role ditentukan konfigurasi server. Tidak ada parameter aktor/role di body. Semua endpoint berikut memakai model dengan extra=forbid. GET detail memberi ETag kasus; daftar memiliki pagination. Case ID/intervention ID UUID kanonis lowercase.

| Method | Path (prefix /api/v1) | Request body / query | Berhasil |
|---|---|---|---|
| GET | /me | — | 200, {data: {actor_id,role,auth_mode}} |
| GET | /cases | status, id_badan_usaha, periode_bulan, page/page_size | 200, {data: [...],pagination} |
| POST | /cases | id_badan_usaha, periode_bulan, reason, recurrence_of? | 201, MutationResult |
| GET | /cases/{case_id} | — | 200, {data: CaseDetail}, ETag |
| GET | /cases/{case_id}/events | page/page_size | 200, {data: [...],pagination} |
| POST | /cases/{case_id}/transitions | action, reason | 200, MutationResult |
| POST | /cases/{case_id}/notes | text | 200, MutationResult |
| POST | /cases/{case_id}/interventions | kind, note, due_at? | 201, MutationResult |
| POST | /cases/{case_id}/interventions/{intervention_id}/outcomes | outcome, note | 200, MutationResult |

CaseSummary: case_id, id_badan_usaha, periode_bulan, status, version, reason, status_reason, created_at, updated_at, created_by, recurrence_of, dataset. CaseDetail menambahkan evidence_snapshot dan interventions. Tiap kasus membawa DatasetRef sendiri karena daftar dapat memuat kasus dari snapshot berbeda. Urutan kasus created_at/case_id ascending; event ascending version. Catatan/status_reason tidak dipakai untuk mengubah bukti atau keputusan aturan sumber.

MutationResult: {data: {case_id,status,version,event_id,intervention_id}}. intervention_id null kecuali rencana/outcome intervensi. Header: ETag: "vN", Location: /api/v1/cases/{id}, Idempotent-Replay: true/false. Event: event_id,case_id,version,actor_id,actor_role,action,payload,created_at. Payload menyimpan input yang telah divalidasi dan dinormalisasi; token tidak tersimpan.

Semua POST mewajibkan Idempotency-Key 8–128 karakter ASCII [A-Za-z0-9_-]. Selain pembukaan kasus, If-Match wajib dengan format kuat "vN" (N positif); tidak mendukung wildcard/list/weak ETag. POST /cases menolak If-Match. Key tersimpan per actor_id tanpa expiry di prototipe. Retry identik, termasuk If-Match lama, mengembalikan hasil mutasi semula tanpa event baru. Perubahan payload/path/versi dengan key sama → 409. Untuk mendapatkan keadaan terkini setelah retry, lakukan GET detail. Role diperiksa lagi sebelum replay tindakan supervisor.

Alasan/catatan di-trim, wajib 1–2000 karakter, NUL ditolak. due_at menerima ISO datetime dengan timezone eksplisit, dinormalisasi UTC dalam rentang tahun 0001–9999. Semua timestamp event berasal dari clock server UTC. Action/kind/outcome dan aturan state mengikuti CASE_LIFECYCLE_SPEC.md. RESOLVED/DISMISSED/REOPEN memerlukan SUPERVISOR. Frontend menangani 412 dengan GET terbaru lalu meminta pengguna mengevaluasi ulang perubahan; gunakan key baru untuk keputusan baru.

Pembuatan kasus menyimpan snapshot bukti secara transaksional. Operasi berikutnya dapat berjalan atas snapshot kasus saat dataset aktif gagal. Replay pembukaan juga tidak memerlukan pemuatan ulang dataset. Tidak tersedia PUT/PATCH/DELETE, upload dokumen, ekspor data pribadi, pengiriman pesan, prediksi ML, atau pemicu sanksi. CORS tidak diaktifkan; frontend lokal menggunakan proxy /api ke loopback backend.
