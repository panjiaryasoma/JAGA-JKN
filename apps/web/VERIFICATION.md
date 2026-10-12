# Catatan verifikasi frontend

Tanggal: 12 Oktober 2026. Branch lokal: `panji-frontend-implementation`.
Baseline backend: `7f24d09`. Catatan ini merekam verifikasi lokal sebelum commit
dan publikasi frontend.

## Hasil yang sudah diperiksa

| Pemeriksaan | Hasil | Cakupan |
|---|---|---|
| Tes JavaScript native Node | 24 lulus | Semantik data, autentikasi, batas API, retry identik, adapter contoh, dan template tampilan. |
| Integrasi frontend dan regresi backend | 131 lulus, 1 dilewati | ASGI TestClient, snapshot publik, penyimpanan kasus, role, konflik versi, dan ketahanan saat dataset gagal. |
| Ruff lint dan format | Lulus | Python launcher, aplikasi web, build preview, dan tes frontend. |
| Validator governance | 213 entri manifest lulus | Konsistensi dokumen yang telah diatur repository. |
| Build preview mandiri dan syntax JavaScript | Lulus | Bundle memakai modul/CSS aplikasi yang sama dan tidak memerlukan aset eksternal. |
| Struktur HTML pada 10 keadaan halaman | Lulus | Satu main/h1, ID unik, dan hubungan label dengan kontrol form. |
| Whitespace patch | Lulus | `git diff --check`. |

Satu tes backend yang memerlukan model terlatih dilewati karena artefak model
tersebut tidak tersedia dalam checkout frontend. Hasil ini tidak membuktikan
inferensi model end-to-end dalam antarmuka.

Alur kasus yang diuji mencakup pembuatan dan replay idempotent, mulai review,
konflik HTTP 412, intervensi dan outcome, penolakan penyelesaian oleh reviewer,
penyelesaian oleh supervisor, serta urutan event tanpa duplikasi.
Pengujian tersebut berjalan pada API sebenarnya melalui ASGI, bukan klik browser.

Preview berisi proyeksi publik **8 badan usaha × 24 bulan** dari snapshot sintetis
yang sama. Angka ringkasannya dihitung dari cuplikan ini. Preview hanya membaca
data; login, penyimpanan kasus, dan inferensi model tidak disimulasikan sebagai
operasi yang berhasil. Aplikasi yang dijalankan bersama backend memakai API.

## Batas verifikasi

- Browser, tangkapan layar, layout pada perangkat nyata, interaksi keyboard/dialog,
  dan pembaca layar belum diuji. Skill Sites mewajibkan jalur control-browser untuk
  preview pada lingkungan ini; kapabilitas tersebut tidak tersedia. Tidak ada
  server preview atau browser alternatif yang dijalankan.
- Pemeriksaan struktur HTML bukan audit aksesibilitas atau pemeriksaan visual.
- Penilaian desain dan kemudahan penggunaan masih memerlukan review pengguna.
- Saat catatan ini dibuat, workflow GitHub Actions frontend sudah ditulis, tetapi
  belum dijalankan di remote. Hasil CI berikutnya tersedia di GitHub Actions.
- Hasil ini mendukung review prototipe; tidak menyatakan kesiapan produksi atau
  penerimaan domain.

Perintah menjalankan aplikasi, membangun preview, dan mengulang tes tersedia di
[README.md](README.md). Kriteria implementasi tersedia di
[FRONTEND_PRD.md](FRONTEND_PRD.md).
