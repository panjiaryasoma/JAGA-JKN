# Frontend JAGA-JKN — rancangan implementasi

Status: DRAFT untuk review pemilik produk. Baseline backend: `7f24d09` (PR #6).
Instruksi kerja: lanjutkan frontend dari referensi HTML v6.5, boleh merombak desain,
tambahkan landing page dan penjelasan penggunaan. Dokumen ini tidak mengubah
otoritas atau status dokumen governance yang sudah ada.

## Versi sederhana

Pengunjung memahami tujuan JAGA-JKN sebelum masuk. Petugas dapat menemukan badan
usaha, membandingkan bukti per bulan, melihat sumber, lalu mencatat review.
Informasi yang belum diketahui tetap terlihat sebagai belum diketahui.

Alur: Beranda → Panduan / Ruang kerja → Badan usaha → Bukti → Kasus review.
Preview mandiri berisi cuplikan data sintetis dan tidak menyimpan kasus.
Implementasi aplikasi memakai API serta penyimpanan kasus backend sebenarnya.

## Masalah desain referensi

- Langsung membuka investigasi tanpa menjelaskan produk dan tindakan pertama.
- Navigasi kecil, daftar entitas, ringkasan, grafik, dan metadata bersaing sekaligus.
- Informasi primer dan provenance terlalu berdekatan secara visual.
- Kasus lokal pada HTML tidak merepresentasikan workflow persisten backend.

Hipotesis desain: hierarki yang lebih jelas dan informasi bertahap membantu
pengguna memahami tugas. Ini belum merupakan hasil usability testing manusia.
Palet hijau gelap, krem, dan aksen emas dipertahankan; tipografi editorial dipakai
di beranda, sedangkan ruang kerja mengutamakan keterbacaan dan kepadatan data.

## Requirement dan kriteria penerimaan

| ID | Kriteria |
|---|---|
| FE-001 | Beranda menjelaskan fungsi, alur, dan batas prototipe; CTA membuka halaman yang benar. |
| FE-002 | Panduan empat langkah, istilah, serta contoh membuka bukti dapat digunakan tanpa akun. |
| FE-003 | Ringkasan mengambil agregat API untuk satu bulan; true, false, unknown tidak digabung. |
| FE-004 | Direktori menyediakan pencarian, filter, pagination, hasil kosong, dan kegagalan eksplisit. |
| FE-005 | Detail mempertahankan nilai null, mutu, sumber, status ABSTAIN, serta konteks bulan simulasi. |
| FE-006 | Tren tidak menyambung nilai hilang; kepesertaan tidak menyamakan selisih jumlah dengan selisih himpunan pekerja. |
| FE-007 | Autentikasi role berasal dari /me. Token hanya di memori tab, tidak dibundel atau disimpan di browser storage. |
| FE-008 | Kasus, catatan, transisi, rencana/intervensi, outcome, dan riwayat menggunakan API; tidak memalsukan keberhasilan. |
| FE-009 | Retry mutasi memakai payload, If-Match, dan Idempotency-Key yang sama. HTTP 412 perlu memuat dan menilai ulang versi terbaru. |
| FE-010 | Kegagalan data tidak diam-diam berpindah ke contoh atau menjadi angka nol. Respons lama tidak menimpa konteks baru. |
| FE-011 | Model eksperimental terpisah dari penetapan kepatuhan; DISABLED/UNAVAILABLE/ABSTAIN jelas. |
| FE-012 | Navigasi keyboard, fokus dialog, label form, status baca layar, layout sempit, dan reduced motion disediakan. |
| FE-013 | Preview mandiri menggunakan proyeksi publik snapshot yang terverifikasi; cuplikan dan read-only dinyatakan eksplisit. |

## Keputusan implementasi

HTML, CSS, dan JavaScript modules native, tanpa framework atau dependency frontend.
Ukuran lingkup belum memerlukan state framework. Modul domain, API, tampilan,
dan pengendali interaksi dipisah agar dapat diuji dan ditingkatkan bertahap.
FastAPI yang sama melayani halaman dan aset melalui launcher `apps.web` sehingga
API tetap same-origin, tanpa membuka CORS atau mengekspos direktori repository.

Preview satu berkas dibuat secara deterministik dari sumber yang sama. Adapter
preview eksplisit hanya membaca data contoh; tidak menjadi fallback API gagal.
Tidak ada perubahan kebijakan, data training, model, atau autentikasi produksi.

## Penyelesaian teknis dan batas penerimaan

Tes domain/client, integrasi ASGI, build preview, dan governance harus lulus.
Pemeriksaan browser/responsivitas visual dilaporkan sesuai kemampuan lingkungan;
review pengguna dan usability testing tetap dibutuhkan sebelum penerimaan desain.
Commit, push, PR, dan merge mengikuti ACC terpisah dari pekerjaan lokal ini.
