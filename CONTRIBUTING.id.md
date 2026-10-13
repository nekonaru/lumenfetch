# Kontribusi ke Lumenfetch

Makasih udah mau bantu kembangin Lumenfetch. Panduan ini biar kontribusi kamu gampang diproses.

[English](CONTRIBUTING.md) | **Bahasa Indonesia**

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
| `core/constants.py` | Nilai shared (versi, format, batas) | Logic bisnis |
| `core/errors.py` | Klasifikasi error + pesan ramah terpusat | Logic download/deteksi |
| `core/i18n.py` | Katalog string UI (EN default, ID opsional) | Logic bisnis |
| `core/cli.py` | Parsing argumen + bangun pilihan non-interaktif | Logic bisnis |
| `core/doctor.py` | Diagnosa setup (ffmpeg, dep, cookies, jaringan) | Download/deteksi |
| `core/ffmpeg.py` | Deteksi ffmpeg sistem dulu, bundled fallback | Download/deteksi |
| `core/log.py` | Logging file terpusat | Tampilan rich/menu |
| `core/detector.py` | Deteksi info video YouTube via yt-dlp | Mendownload apa pun |
| `core/downloader.py` | Proses download, progress hook, retry | Menampilkan menu/prompt |
| `core/options.py` | Semua interaksi & tampilan menu (rich) | Logic download |
| `core/utils.py` | Helper murni: sanitasi, format, config user | Bergantung ke CLI atau jaringan |
| `main.py` | Menyatukan semua modul lewat CLI + loop utama | Logic bisnis baru |

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

Contoh: `fix: handle playlist YouTube satu video`

## 🐛 Lapor Bug / Request Fitur

Buka [Issues](../../issues) baru, sertakan:
- Link yang bermasalah (kalau ada, hapus info pribadi)
- Pesan error yang muncul di terminal
- Langkah buat reproduce masalahnya

## 🤝 Pull Request

1. Buat branch baru dari `main`, kasih nama yang jelas (misal `fix/playlist-satu-video`)
2. Pastikan `pytest` dan `ruff check .` lulus
3. Jelasin di deskripsi PR apa yang diubah dan kenapa
4. Tunggu review — mungkin ada request perubahan kecil sebelum di-merge
