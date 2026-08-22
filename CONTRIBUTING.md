# Kontribusi ke Lumenfetch

Makasih udah mau bantu kembangin Lumenfetch. Panduan ini biar kontribusi kamu gampang diproses.

## 🛠 Setup Development

1. Fork & clone repo ini
2. Install dependency (termasuk tools testing & lint):
   ```bash
   pip install -r requirements-dev.txt
   ```
3. Pastikan `ffmpeg` sudah terinstall di sistem kamu (lihat bagian Requirements di README)

## 🗂 Struktur & Prinsip Modul

Lumenfetch sengaja dipisah per tanggung jawab, tolong dijaga konsistensinya kalau nambah/ubah kode:

| File | Tanggung jawab | Tidak boleh |
|------|-----------------|-------------|
| `core/detector.py` | Deteksi platform, judul, tipe konten via yt-dlp | Mendownload apa pun |
| `core/downloader.py` | Proses download, progress hook, retry | Menampilkan menu/prompt |
| `core/options.py` | Semua interaksi & tampilan menu (rich) | Logic download |
| `core/utils.py` | Helper murni: sanitasi, format, config.json | Bergantung ke CLI atau jaringan |
| `main.py` | Menyatukan semua modul lewat satu loop | Logic bisnis baru |

Kalau nambah fitur, coba taruh di modul yang paling sesuai dulu sebelum bikin file baru.

## ✅ Sebelum Bikin Pull Request

Jalankan ini dulu di root project:

```bash
pytest tests/ -v
ruff check .
```

Pastikan semua test lulus dan tidak ada warning lint baru. GitHub Actions juga bakal jalanin ini otomatis di setiap PR.

## 📝 Commit Message

Pakai prefix singkat biar history gampang dibaca:

- `feat:` — fitur baru
- `fix:` — perbaikan bug
- `docs:` — perubahan dokumentasi (README, CONTRIBUTING, dll)
- `refactor:` — perubahan struktur kode tanpa mengubah perilaku
- `test:` — nambah/ubah test

Contoh: `fix: handle carousel gambar dengan 1 gambar saja`

## 🐛 Lapor Bug / Request Fitur

Buka [Issues](../../issues) baru, sertakan:
- Platform/link yang bermasalah (kalau ada, hapus info pribadi)
- Pesan error yang muncul di terminal
- Langkah buat reproduce masalahnya

## 🤝 Pull Request

1. Buat branch baru dari `main`, kasih nama yang jelas (misal `fix/carousel-single-image`)
2. Pastikan `pytest` dan `ruff check .` lulus
3. Jelasin di deskripsi PR apa yang diubah dan kenapa
4. Tunggu review — mungkin ada request perubahan kecil sebelum di-merge
