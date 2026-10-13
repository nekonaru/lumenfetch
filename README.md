<div align="center">

### 📥 Lumenfetch
**YouTube downloader buat terminal - MP4 & MP3. Paste link, pilih quality, beres.**

<br>

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey?style=flat-square)
![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=flat-square)

</div>

## ✨ Tentang Project

**Lumenfetch** adalah CLI Python buat download video YouTube jadi **MP4** atau ekstrak audionya jadi **MP3** - cukup paste link, dia otomatis deteksi judul, durasi, dan estimasi ukuran, lalu kasih kamu opsi quality yang relevan. Didukung [yt-dlp](https://github.com/yt-dlp/yt-dlp) di belakang layar, plus `curl_cffi` buat lolos bot-check YouTube.

> _"Satu command, langsung MP4/MP3."_

## 🎯 Fitur

| Fitur | Keterangan |
|-------|------------|
| 🔍 **Auto-detect** | Judul, durasi, dan estimasi ukuran terdeteksi otomatis |
| 🎛 **Opsi dinamis** | Menu quality menyesuaikan (video / audio saja) |
| 🎞 **Video MP4** | Pilihan quality Best/1080p/720p/480p/360p/Worst, thumbnail otomatis ter-embed |
| 🎵 **Audio MP3** | Pilihan bitrate Best/320kbps/192kbps/128kbps |
| 📜 **Playlist** | Default video pertama saja; `--playlist all` untuk semua sekaligus |
| 💬 **Subtitle & metadata** | Download subtitle (SRT) + embed ke MP4, opsional via flag/CLI |
| 📋 **Auto-paste clipboard** | Kalau ada link valid di clipboard, langsung ditawarkan tanpa perlu paste manual - tidak akan nanya ulang isi clipboard yang sama berkali-kali |
| 📊 **Progress bar real-time** | Kecepatan, ukuran, dan estimasi waktu tersisa lewat `rich` |
| 📐 **Estimasi ukuran & waktu** | Muncul di menu pilih quality (video/audio), dihitung dari data yt-dlp + kecepatan rata-rata download kamu sebelumnya |
| 🔄 **Auto-retry** | Error koneksi dicoba ulang otomatis (default 3x), error fatal (private/invalid) langsung dilaporkan |
| 🗂 **Riwayat download** | 20 entri terakhir tersimpan, bisa dilihat kapan saja lewat command `history` |
| ⚙️ **Pengaturan persisten** | Folder download (default: folder Downloads OS, ganti kapan saja), max retry, auto-paste, dan naming template diingat lewat `config.json` |
| 🍪 **Cookies browser/file** | Opsional, buat video age-restricted/private - dari Chrome/Firefox/Edge/dll atau file `cookies.txt` |
| 🧼 **Nama file aman** | Karakter ilegal disanitasi, duplikat otomatis dikasih suffix `(1)`, `(2)`, dst |
| 🔔 **Auto-check update yt-dlp** | Tiap dibuka, dicek ke PyPI apakah ada versi yt-dlp lebih baru - gagal cek (mis. offline) diam-diam diabaikan |

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
# atau non-interaktif:
python main.py "https://youtube.com/watch?v=..." -t video -f mp4 -q 720p -y
python main.py --batch daftar.txt --jobs 2
python main.py --history
python main.py --help
```

**Flag CLI:**
```
-t/--type {video,audio}  -f/--format {mp4,mp3}  -q/--quality
-o/--output  --cookies  --cookies-file  --max-retry  --playlist {single,all}
--subs  --sub-langs en,id  --embed-subs  --embed-metadata
--batch file.txt  --jobs 1-4  --no-clipboard  -y/--yes  -v/--verbose
--history  --version
```

**Masukkan URL saat diminta:**
```
Masukkan URL (q: keluar, history, settings, help): https://youtube.com/watch?v=...
```

Kalau ada link valid di clipboard, Lumenfetch akan menawarkannya duluan - tinggal jawab `y` kalau mau pakai itu.

**Link YouTube otomatis terdeteksi, lalu menu menyesuaikan:**

- **Video** → pilih output Video (MP4) / Audio (MP3) → pilih quality
- **Stream audio** → langsung pilih bitrate MP3
- **Playlist** → default video pertama; `--playlist all` untuk semua

**Konfirmasi nama file, lalu proses download berjalan** dengan progress bar real-time (kecepatan, ukuran, ETA). Tekan `Ctrl+C` kapan saja untuk membatalkan dengan aman.

## ⌨️ Command

Diketik langsung di prompt utama, menggantikan URL:

| Command | Fungsi |
|---------|--------|
| `history` | Lihat 20 riwayat download terakhir (tanggal, judul, format, ukuran, status) |
| `settings` | Ganti folder default, max retry, auto-paste clipboard, naming template, atau cookies |
| `help` | Tampilkan panduan singkat di dalam aplikasi |
| `q` / `quit` | Keluar dari aplikasi |
| `Ctrl+C` | Batalkan download yang sedang berjalan |

## 🍪 Cookies (Opsional)

Video age-restricted atau private butuh login. Kalau ketemu error semacam itu, aktifkan salah satu:

**A. Cookies dari browser:**
1. Buka Lumenfetch, ketik `settings`
2. Pilih `[5] Pakai cookies dari browser/file`
3. Pilih browser di mana kamu sudah login YouTube (Chrome/Firefox/Edge/Brave/Opera/Vivaldi/Safari)

Setelah aktif, Lumenfetch akan meminjam cookies dari browser itu setiap kali mendeteksi atau mendownload konten, seolah request-nya datang dari sesi browser kamu yang sudah login. Cukup pilih `[1] Nonaktifkan` di menu yang sama kalau mau matikan lagi.

> **Penting:** browser yang dipilih harus **benar-benar tertutup total** saat download (file cookies dikunci selama browser terbuka - errornya `Could not copy ... cookie database`). Cek Task Manager dan matikan semua proses browser tersebut (Edge/Chrome sering masih jalan di background).

> **Alternatif paling reliable (disarankan kalau error cookies terus muncul):** pakai **file cookies** yang works walau browser terbuka:
> 1. Install extension **"Get cookies.txt LOCALLY"** (Chrome/Edge/Firefox) di browser
> 2. Buka youtube.com (pastikan sudah login), klik extension → **Export** → simpan mis. `D:\cookies.txt`
> 3. Di Lumenfetch: `settings` → `[5]` → `[1] Nonaktifkan` → isi path file cookies tadi
> 4. Atau via CLI: `python main.py <URL> --cookies-file D:\cookies.txt`

## 📐 Estimasi Ukuran & Waktu Download

Pas milih quality buat video atau audio, Lumenfetch nampilin perkiraan ukuran file dan waktu download di sebelah tiap opsi:

```
Pilih Quality:
  [1] Best   (default)  (~147.8 MB, ~31 detik)
  [2] 1080p              (~147.8 MB, ~31 detik)
  [3] 720p               (~81.1 MB, ~17 detik)
  [4] 480p               (~42.9 MB, ~9 detik)
```

Cara kerjanya:

- **Ukuran** dihitung dari data yang yt-dlp udah dapat pas proses "Mendeteksi konten..." (gak ada request tambahan ke platform, jadi gak bikin lambat)
- **Waktu** dihitung dari kecepatan rata-rata beberapa download terakhir kamu yang sukses (bukan angka tebakan generik) - makin sering pakai Lumenfetch, makin akurat estimasinya
- Kalau datanya gak cukup buat ngasih estimasi yang jujur (mis. platform gak expose ukuran file sama sekali, quality tier yang diminta gak tersedia buat konten itu, atau ini baru pertama kali pakai aplikasi jadi belum ada riwayat kecepatan) - estimasinya gak ditampilin sama sekali, daripada nampilin angka ngasal

## 🔔 Auto-check Update yt-dlp

YouTube sering ubah sistemnya - jadi `yt-dlp` juga perlu sering di-update biar tetap kompatibel. Ini bukan "sekali fix, selesai selamanya", tapi proses berkelanjutan (mirip antivirus yang perlu update rutin).

Buat bantu itu, tiap kali Lumenfetch dibuka, otomatis dicek ke PyPI apakah ada versi `yt-dlp` yang lebih baru dari yang terinstall. Kalau ada, muncul notice kayak gini:

```
🔔 Update yt-dlp tersedia
yt-dlp kamu versi 2026.1.1, versi terbaru 2026.8.19 sudah tersedia.
pip install --upgrade yt-dlp
```

Tinggal jalankan command yang ditampilkan. Kalau lagi offline atau PyPI nggak bisa diakses, pengecekan ini gagal diam-diam dan **tidak** menghalangi kamu pakai aplikasinya.

## 🗂 Naming & Konfigurasi

Nama file mengikuti template di `config.json` (default: `%(platform)s_%(title)s_%(year)s`), contoh hasil:

```
YouTube_Lofi-Hip-Hop-Radio_2026.mp4
YouTube_Lofi-Hip-Hop-Radio_2026.mp3
```

Preferensi kamu (folder simpan, max retry, auto-paste, naming template, cookies browser, dan riwayat) otomatis tersimpan di config user
(`%APPDATA%/lumenfetch/config.json` di Windows, `~/.config/lumenfetch/config.json` di Linux, `~/Library/Application Support/lumenfetch/` di macOS)
- dibuat otomatis dengan nilai default saat pertama kali dijalankan. Config lama di `config.json` project root dimigrasi otomatis sekali.
Log detail tersimpan di `lumenfetch.log` sefolder config (pakai `-v/--verbose` untuk level debug).

**Folder download default** otomatis mengikuti folder **Downloads** asli sistem operasi kamu (`~/Downloads` di macOS/Linux, `C:\Users\<nama-kamu>\Downloads` di Windows) - persis seperti kebiasaan browser lain (Chrome, Firefox, Edge, dll), bukan folder relatif di dalam project. Mau ganti ke folder lain? Tinggal:

1. Ketik `settings` di prompt utama
2. Pilih `[1] Ganti folder download default`
3. Ketik path folder yang diinginkan (boleh pakai `~` buat home folder, mis. `~/Documents/Video`, atau path absolut penuh)

> **Catatan:** config tersimpan di folder data user (lihat atas), bukan relatif ke folder project - jadi aman dijalankan dari mana saja.

## ⚠️ Troubleshooting

| Masalah | Solusi |
|---------|--------|
| `ModuleNotFoundError: No module named 'yt_dlp'` / `'rich'` / `'curl_cffi'` / `'pyperclip'` / `'static_ffmpeg'` | Jalankan ulang `pip install -r requirements.txt` |
| `HTTP Error 403: Forbidden` | Update yt-dlp ke versi terbaru: `pip install --upgrade yt-dlp` |
| `Sign in to confirm you're not a bot` | Aktifkan fitur **Cookies** di atas (browser atau file) |
| `❌ Konten ini private / tidak bisa diakses` | Video private/age-restricted - aktifkan **Cookies** di atas |
| `❌ Format tidak tersedia untuk konten ini` | Coba quality lain |
| `❌ Koneksi internet bermasalah` terus muncul | Cek koneksi, atau naikkan `max_retry` lewat command `settings` |
| Video berhasil download tapi tidak ada suara | Jarang terjadi karena ffmpeg sudah bundled otomatis, tapi kalau muncul, jalankan ulang aplikasinya (ffmpeg diunduh ulang otomatis kalau file sebelumnya rusak) |
| Ganti naming template di `settings` ditolak | Template cuma boleh pakai `%(platform)s`, `%(title)s`, `%(year)s` - ditolak otomatis kalau ada placeholder salah ketik, biar tidak bikin nama file error saat download |
| `⚠️ URL ini playlist berisi N video` | Default cuma video pertama. Gunakan `--playlist all` untuk download semua sebagai file ber-index |
| Batch download | Buat file teks (satu URL per baris, `#` = komentar), lalu `python main.py --batch daftar.txt --jobs 2` |
| Resume download | Didukung via `continuedl` yt-dlp + retry backoff eksponensial (2s, 4s, 8s... max 30s). File parsial `.part` dilanjutkan, bukan diulang dari 0 |
| `ffmpeg tidak ditemukan` | Install ffmpeg sistem dulu (lebih ringan), fallback bundled otomatis. Cek dengan `ffmpeg -version` |

## 🗂️ Struktur Project

```
lumenfetch/
├── main.py                    # Entry point, CLI args, batch, loop utama
├── core/
│   ├── constants.py           # Single source of truth (versi, format, batas)
│   ├── errors.py              # Taxonomy error terpusat (klasifikasi + pesan ramah)
│   ├── ffmpeg.py              # Deteksi ffmpeg sistem dulu, bundled fallback
│   ├── log.py                 # Logging file terpusat
│   ├── downloader.py          # Download MP4 / ekstrak MP3 + resume + retry backoff
│   ├── detector.py            # Deteksi info video YouTube
│   ├── options.py             # Menu & prompt interaktif (rich)
│   ├── update_checker.py      # Auto-check versi terbaru yt-dlp di PyPI
│   └── utils.py               # Sanitasi nama file, format size, config user
├── tests/
│   ├── conftest.py            # Fixture global (no-sleep) + SAMPLE_VIDEO_FORMATS
│   ├── test_utils.py
│   ├── test_detector.py
│   ├── test_downloader.py
│   ├── test_options.py
│   ├── test_main.py
│   └── test_features.py       # Fitur (CLI, backoff, batch, ffmpeg, cookies, log)
├── .github/
│   └── workflows/
│       └── tests.yml          # CI: test & lint otomatis
├── downloads/                 # Folder placeholder (bukan lokasi download aktual - lihat "Naming & Konfigurasi")
├── requirements.txt
├── requirements-dev.txt       # Dependency tambahan untuk development (pytest, ruff)
├── pyproject.toml             # Metadata project + entry point + konfigurasi ruff
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

**Prinsip pemisahan modul:**
- `constants.py` - nilai shared (versi, format, batas) biar tidak drift antar modul
- `errors.py` - klasifikasi error terpusat, dipakai detector & downloader bersama
- `detector.py` - murni deteksi info video YouTube, tidak mendownload apa pun
- `downloader.py` - murni proses download MP4/MP3 & progress, tidak menampilkan menu
- `options.py` - semua interaksi & tampilan menu, tidak ada logic download
- `utils.py` - helper murni (sanitasi, format, baca/tulis config), tidak tahu soal CLI atau jaringan
- `main.py` - menyatukan semuanya lewat CLI + loop utama

## 🗺️ Roadmap

- [x] **Phase 1 - Core**: struktur project, integrasi yt-dlp dasar, progress bar, config user
- [x] **Phase 2 - Smart Detection**: auto-detect video YouTube, auto-paste clipboard, preview nama file
- [x] **Phase 3 - Reliability**: resume, retry backoff eksponensial, playlist, cancel graceful
- [x] **Phase 4 - Polish**: menu history, settings, help, naming template, subtitle & metadata
- [x] **Phase 5 - Fokus YouTube**: scope MP4/MP3 saja (v2.0.0) - hapus jalur multi-platform & dep berat

## 🧪 Testing

Ada unit test per modul (sanitasi nama file, naming template, resolve duplikat, format ukuran/durasi, config, validasi URL YouTube, opts yt-dlp, CLI, dll).

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
