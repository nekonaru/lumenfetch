<div align="center">

### 📥 Lumenfetch
**Universal media downloader buat terminal - paste link, biar sisanya otomatis.**

<br>

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey?style=flat-square)
![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=flat-square)

</div>

## ✨ Tentang Project

**Lumenfetch** adalah CLI Python yang mengunduh media dari (hampir) situs mana pun - cukup paste link, dia otomatis deteksi platform dan tipe kontennya (video, audio, atau gambar), lalu kasih kamu opsi format & quality yang relevan buat konten itu. Didukung [yt-dlp](https://github.com/yt-dlp/yt-dlp) di belakang layar, jadi cakupannya luas: YouTube, TikTok, Instagram, Facebook, X/Twitter, Threads, Pinterest, Reddit, dan 1000+ situs lainnya.

> _"Satu tool, semua platform - nggak perlu ganti-ganti downloader."_

## 🎯 Fitur

| Fitur | Keterangan |
|-------|------------|
| 🔍 **Auto-detect** | Platform, judul, tipe konten (video/audio/gambar), dan durasi terdeteksi otomatis |
| 🎛 **Opsi dinamis** | Menu quality & format menyesuaikan sendiri sesuai tipe konten yang terdeteksi |
| 🎞 **Video** | Pilihan quality Best/1080p/720p/480p/360p/Worst, format MP4/WEBM/MKV, thumbnail otomatis ter-embed |
| 🎵 **Audio** | Ekstrak ke MP3/M4A/WAV/FLAC dengan pilihan bitrate |
| 🖼 **Gambar & carousel** | Download satu gambar, semua sekaligus, atau pilih nomor tertentu (misal post Instagram multi-foto) |
| 📋 **Auto-paste clipboard** | Kalau ada link valid di clipboard, langsung ditawarkan tanpa perlu paste manual |
| 📊 **Progress bar real-time** | Kecepatan, ukuran, dan estimasi waktu tersisa lewat `rich` |
| 🔄 **Auto-retry** | Error koneksi dicoba ulang otomatis (default 3x), error fatal (private/invalid) langsung dilaporkan |
| 🗂 **Riwayat download** | 20 entri terakhir tersimpan, bisa dilihat kapan saja lewat command `history` |
| ⚙️ **Pengaturan persisten** | Folder default, max retry, auto-paste, dan naming template diingat lewat `config.json` |
| 🍪 **Cookies dari browser** | Opsional, buat konten yang minta login (misal Instagram) - ambil cookies dari Chrome/Firefox/Edge/dll |
| 🧼 **Nama file aman** | Karakter ilegal disanitasi, duplikat otomatis dikasih suffix `(1)`, `(2)`, dst |

## 📦 Requirements

- **Python** 3.9 atau lebih baru
- **Koneksi internet**

> ffmpeg **tidak perlu diinstall manual** - Lumenfetch otomatis mengunduh dan memakai versi bundled-nya sendiri (lewat `static-ffmpeg`) begitu pertama kali dijalankan, persis seperti cara kerja `ffmpeg-static` di project Node.js.

### Belum pernah pakai terminal? Ikuti ini dulu

<details>
<summary><b>🪟 Cara buka terminal di Windows</b></summary>

1. Tekan tombol **Windows**, ketik `PowerShell`, lalu tekan **Enter**
2. Jendela hitam/biru akan terbuka. Itu tempat kamu mengetik perintah
3. Semua perintah `python ...` atau `pip ...` di panduan ini diketik di jendela itu, lalu tekan **Enter**

</details>

<details>
<summary><b>🍎 Cara buka terminal di macOS</b></summary>

1. Tekan **Cmd + Spasi**, ketik `Terminal`, lalu tekan **Enter**
2. Ketik perintah-perintah di panduan ini di situ, lalu tekan **Enter**

</details>

<details>
<summary><b>🐧 Cara buka terminal di Linux</b></summary>

Tekan **Ctrl + Alt + T**, atau cari aplikasi "Terminal" di menu aplikasi.

</details>

### Belum punya Python?

1. Buka [python.org/downloads](https://www.python.org/downloads/) dan unduh versi terbaru
2. **Khusus Windows**: saat instalasi, centang dulu kotak **"Add Python to PATH"** di layar pertama sebelum klik Install
3. Setelah selesai install, cek dengan:

```bash
python --version
# atau
python3 --version
```

## 🚀 Instalasi

**1. Ambil kode project ini**

<details>
<summary><b>Punya Git terinstall</b></summary>

```bash
git clone https://github.com/nekonaru/lumenfetch.git
cd lumenfetch
```

</details>

<details>
<summary><b>Tidak punya Git</b></summary>

1. Buka halaman repository di GitHub
2. Klik tombol hijau **`Code`** → pilih **`Download ZIP`**
3. Ekstrak file ZIP yang terunduh ke folder pilihanmu
4. Di terminal, masuk ke folder hasil ekstrak

</details>

**2. Install dependency**
```bash
pip install -r requirements.txt
```

> Kalau muncul error `externally-managed-environment` (biasanya di Linux):
> ```bash
> pip install -r requirements.txt --break-system-packages
> ```

## 🖥️ Cara Pakai

**Jalankan:**
```bash
python main.py
```

**Masukkan URL saat diminta:**
```
Masukkan URL (q: keluar, history, settings, help): https://youtube.com/watch?v=...
```

Kalau ada link valid di clipboard, Lumenfetch akan menawarkannya duluan - tinggal jawab `y` kalau mau pakai itu.

**Konten otomatis terdeteksi, lalu menu menyesuaikan:**

- **Video** → pilih output (Video/Audio/Gambar thumbnail) → pilih quality → pilih format
- **Audio** → langsung pilih format → pilih bitrate
- **Gambar / carousel** → pilih format → kalau lebih dari satu gambar, pilih "semua" atau ketik nomor tertentu (contoh: `1,3,5`)

**Konfirmasi nama file, lalu proses download berjalan** dengan progress bar real-time (kecepatan, ukuran, ETA). Tekan `Ctrl+C` kapan saja untuk membatalkan dengan aman.

## ⌨️ Command

Diketik langsung di prompt utama, menggantikan URL:

| Command | Fungsi |
|---------|--------|
| `history` | Lihat 20 riwayat download terakhir (tanggal, platform, judul, format, ukuran, status) |
| `settings` | Ganti folder default, max retry, auto-paste clipboard, naming template, atau cookies browser |
| `help` | Tampilkan panduan singkat di dalam aplikasi |
| `q` / `quit` | Keluar dari aplikasi |
| `Ctrl+C` | Batalkan download yang sedang berjalan |

## 🍪 Cookies dari Browser (Opsional)

Beberapa platform, terutama Instagram, sekarang sering memblokir request yang "tidak keliatan login" meskipun kontennya publik. Kalau kamu sering ketemu error semacam itu, aktifkan fitur ini:

1. Buka Lumenfetch, ketik `settings`
2. Pilih `[5] Pakai cookies dari browser`
3. Pilih browser yang kamu pakai buat login ke platform tersebut (Chrome/Firefox/Edge/Brave/Opera/Vivaldi/Safari)

Setelah aktif, Lumenfetch akan meminjam cookies dari browser itu setiap kali mendeteksi atau mendownload konten, seolah request-nya datang dari sesi browser kamu yang sudah login. Cukup pilih `[1] Nonaktifkan` di menu yang sama kalau mau matikan lagi.

> **Catatan:** pastikan browser yang dipilih sedang tidak dalam keadaan tertutup total saat digunakan di beberapa OS (khususnya Chrome di Windows kadang mengunci file cookies saat browser terbuka). Kalau muncul error terkait cookies, coba tutup browser-nya dulu lalu ulangi.

## 🗂 Naming & Konfigurasi

Nama file mengikuti template di `config.json` (default: `%(platform)s_%(title)s_%(year)s`), contoh hasil:

```
YouTube_Lofi-Hip-Hop-Radio_2026.mp4
Instagram_Post-by-username_2026.jpg
```

Preferensi kamu (folder simpan, max retry, auto-paste, naming template, cookies browser, dan riwayat) otomatis tersimpan di `config.json` - dibuat otomatis dengan nilai default saat pertama kali dijalankan, jadi nggak perlu disentuh manual kecuali mau kustomisasi lewat command `settings`.

## ⚠️ Troubleshooting

| Masalah | Solusi |
|---------|--------|
| `ModuleNotFoundError: No module named 'yt_dlp'` / `'rich'` / `'pyperclip'` / `'static_ffmpeg'` | Jalankan ulang `pip install -r requirements.txt` |
| `HTTP Error 403: Forbidden` (biasanya di YouTube) | Update yt-dlp ke versi terbaru: `pip install --upgrade yt-dlp` |
| `Sign in to confirm you're not a bot` (YouTube) | Aktifkan fitur **Cookies dari Browser** di atas |
| `Unexpected response from webpage request` (biasanya di TikTok) | Update yt-dlp ke versi terbaru: `pip install --upgrade yt-dlp` |
| `❌ Konten ini private / tidak bisa diakses` (terutama Instagram) | Coba aktifkan fitur **Cookies dari Browser** di atas |
| `Postingan foto Instagram belum didukung yt-dlp` | Ini keterbatasan yt-dlp sendiri, bukan bug Lumenfetch - yt-dlp memang tidak reliable untuk post foto standalone (non-reel/video) di Instagram. Sudah dilaporkan bertahun-tahun di [issue tracker yt-dlp](https://github.com/yt-dlp/yt-dlp/issues) dan belum ada fix resmi |
| `❌ Format tidak tersedia untuk konten ini` | Coba quality/format lain - tidak semua platform punya semua kombinasi |
| `❌ Koneksi internet bermasalah` terus muncul | Cek koneksi, atau naikkan `max_retry` lewat command `settings` |
| Video berhasil download tapi tidak ada suara | Jarang terjadi karena ffmpeg sudah bundled otomatis, tapi kalau muncul, jalankan ulang aplikasinya (ffmpeg diunduh ulang otomatis kalau file sebelumnya rusak) |

## 🗂️ Struktur Project

```
lumenfetch/
├── main.py                    # Entry point & loop utama
├── core/
│   ├── downloader.py          # Logic download (yt-dlp API) + progress hook + retry
│   ├── detector.py            # Deteksi platform & tipe konten
│   ├── options.py             # Menu & prompt interaktif (rich)
│   └── utils.py               # Sanitasi nama file, format size, config.json
├── tests/
│   └── test_lumenfetch.py     # Unit test (pytest)
├── .github/
│   └── workflows/
│       └── tests.yml          # CI: test & lint otomatis
├── downloads/                 # Folder output default
├── config.json                # Preferensi user (auto-generate, tidak di-commit)
├── requirements.txt
├── requirements-dev.txt       # Dependency tambahan untuk development (pytest, ruff)
├── pyproject.toml             # Konfigurasi ruff
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

**Prinsip pemisahan modul:**
- `detector.py` - murni deteksi info konten, tidak mendownload apa pun
- `downloader.py` - murni proses download & progress, tidak menampilkan menu
- `options.py` - semua interaksi & tampilan menu, tidak ada logic download
- `utils.py` - helper murni (sanitasi, format, baca/tulis config), tidak tahu soal CLI atau jaringan
- `main.py` - menyatukan semuanya lewat satu loop utama

## 🗺️ Roadmap

- [x] **Phase 1 - Core**: struktur project, integrasi yt-dlp dasar, progress bar, config.json
- [x] **Phase 2 - Smart Detection**: auto-detect tipe konten, auto-paste clipboard, preview nama file
- [x] **Phase 3 - Reliability & Multi-platform**: retry otomatis, carousel gambar, cancel graceful
- [x] **Phase 4 - Polish**: menu history, settings, help, naming template kustom

## 🧪 Testing

Ada unit test untuk fungsi-fungsi inti (sanitasi nama file, naming template, resolve duplikat, format ukuran/durasi, config, validasi URL, dll).

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
ruff check .
```

CI (`.github/workflows/tests.yml`) otomatis menjalankan ini di setiap push & pull request ke `main`, di Python 3.9-3.12.

## 🤝 Kontribusi

Mau bantu kembangin Lumenfetch? Baca [`CONTRIBUTING.md`](CONTRIBUTING.md) untuk struktur project dan alur kontribusi.

## 👤 Author

<div align="center">

| [![Nicolas Dwi Dharma](https://github.com/github.png?size=100)](https://github.com/nekonaru) |
|:---:|
| **Nicolas Dwi Dharma** |
| [github.com/nekonaru](https://github.com/nekonaru) |

</div>

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for more information.

<div align="center">

Made with 📥 by **Nicolas Dwi Dharma**

*Star ⭐ repo ini kalau project ini membantumu!*

</div>
