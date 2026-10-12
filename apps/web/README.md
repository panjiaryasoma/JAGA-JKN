# Frontend JAGA-JKN

Landing page, panduan penggunaan, dan ruang telaah bukti sintetis. Frontend dan
backend berjalan pada satu origin; tidak membutuhkan Node untuk menjalankan app.
HTML/CSS/JavaScript modules native, tanpa runtime framework, CDN, atau font eksternal.
Status: implementasi prototipe untuk review; penerimaan desain/domain belum difreeze.

## Jalankan aplikasi

Dari root repository, dengan Python 3.12/3.13 dan uv sesuai backend:

```bash
uv sync --locked
uv run --locked python -m apps.web --demo
```

Buka **http://127.0.0.1:8000/**. Launcher menghasilkan kunci akses reviewer dan
supervisor di terminal. Klik **Masuk sebagai petugas**, lalu masukkan salah satu
kunci. Tanpa masuk, direktori, bukti, ringkasan, dan panduan tetap tersedia.
`--port 8001` memilih port lain. Launcher selalu bind ke loopback.

Token hanya di memori tab, hilang saat reload/keluar. Kasus tersimpan di database
backend (`var/jaga-jkn.sqlite3` secara default), sehingga bertahan setelah restart.
Launcher `--demo` mengganti kunci setiap restart, bukan menghapus kasus.
Untuk kunci yang dikonfigurasi pengelola, jalankan tanpa `--demo`; konfigurasi sama
dengan [backend](../api/README.md). Autentikasi ini khusus prototipe lokal.

## Halaman dan perilaku

- `#/`: beranda, contoh bukti yang bersumber dari snapshot, alur interaktif, FAQ.
- `#/guide`: empat langkah penggunaan, contoh yang dapat dibuka, penjelasan istilah.
- `#/workspace`: agregat bulanan, true/false/unknown terpisah, pencarian cepat.
- `#/companies`: pencarian nama/ID, filter exact-match, pagination.
- `#/companies/BU-0001?month=2025-12`: perbandingan, tren, tabel, sumber dan mutu.
- `#/cases`: autentikasi, filter kasus, detail, event, transisi, catatan, rencana dan outcome.
- `#/data`: cakupan, identitas snapshot, hash sumber, kesiapan fitur.

Parameter bulan/filter masuk ke hash URL; back/forward memulihkan konteks.
Nama perusahaan bukan identifier. Nilai null tidak diubah menjadi nol. Status
ABSTAIN, data tidak tersedia, dan API gagal dibedakan. Eksperimen ML hanya diminta
setelah pengguna memilihnya, jika backend melaporkan READY dan petugas sudah masuk.

Mutasi memakai Idempotency-Key. Bila respons hilang, dialog mempertahankan perintah
dan hanya menawarkan retry identik. Tab memberi peringatan sebelum ditinggalkan
saat status simpan belum pasti. HTTP 412 memerlukan pemuatan versi terbaru dan
konfirmasi penilaian ulang; tidak ada retry otomatis dengan versi baru. Draft yang
belum tersimpan hanya berada di memori, bukan penyimpanan browser.

## Preview mandiri

```bash
uv run --locked python -m scripts.build_web_preview
```

Hasil: `apps/web/dist/JAGA_JKN_frontend_preview.html`. Buka berkas di browser modern.
Preview memuat **8 badan usaha × 24 bulan**, dari proyeksi publik snapshot yang sama;
bukan seluruh 500 badan usaha. Hanya read-only, tidak memalsukan login, kasus,
atau model. Kegagalan API live tidak pernah beralih ke data preview.

`--refresh-sample` membangun ulang `static/sample.mjs` melalui loader snapshot yang
memeriksa hash dan skema. Tinjau perubahan data tersebut sebelum commit.
Preview dibuat dari modul dan CSS aplikasi yang sama, tanpa sumber desain kedua.

## Pengujian

Node 22+ hanya diperlukan untuk tes JavaScript:

```bash
node --test apps/web/tests/*.test.mjs
uv run --locked pytest tests/frontend tests/backend -q
uv run --locked ruff check apps/web tests/frontend scripts/build_web_preview.py
uv run --locked ruff format --check apps/web tests/frontend scripts/build_web_preview.py
uv run --locked python -m scripts.build_web_preview
```

Workflow `frontend.yml` menjalankan tes, syntax bundle, build, dan pemeriksaan Python.
Tes backend yang membutuhkan model terlatih tetap mengikuti gate ML CI terpisah.
Hasil lokal dan batas pemeriksaan tercatat di [VERIFICATION.md](VERIFICATION.md).

## Desain dan struktur

Rancangan: [FRONTEND_PRD.md](FRONTEND_PRD.md). Hijau gelap/krem/emas dari referensi
v6.5 dipertahankan; beranda menjelaskan produk, ruang kerja memisahkan ringkasan,
direktori, detail bukti, dan kasus. Provenance dibuka bertahap melalui disclosure.
Navigasi mobile, label form, fokus dialog native, tab keyboard, reduced motion,
dan tabel alternatif grafik tersedia dalam implementasi.

`domain.mjs` menangani semantik, `api.mjs` komunikasi/akses, `views.mjs` template
dengan escaping, `app.mjs` interaksi/routing, `demo.mjs` adapter contoh yang eksplisit.
`app.py` menambahkan halaman dan direktori aset ke aplikasi API yang sama, tanpa
membuka direktori repository. CSP khusus frontend mempertahankan dokumentasi API.

Baseline branch frontend: `7f24d09`, melanjutkan PR #6 backend serving. Merge PR #6
dan publikasi frontend mengikuti keputusan pemilik repo; implementasi ini tidak
menyatakan frontend produksi atau penerimaan domain.
