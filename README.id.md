<div align="center">

# 📥 Lumenfetch: YouTube Downloader

**Simpan video YouTube apa pun jadi `.mp4` atau `.mp3`, lengkap dengan pilihan quality, subtitle, dan playlist, langsung dari terminal.**

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![PyPI](https://img.shields.io/pypi/v/lumenfetch?style=flat-square&color=blue)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey?style=flat-square)
![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=flat-square)
![Tests](https://github.com/nekonaru/lumenfetch/actions/workflows/tests.yml/badge.svg)

</div>

[English](README.md) | **Bahasa Indonesia**

## ✨ Tentang Project

**Lumenfetch** adalah CLI Python ringan buat download video YouTube jadi **MP4** atau ekstrak audionya jadi **MP3**. Cukup paste link, dia otomatis deteksi judul, durasi, dan estimasi ukuran file, lalu kasih opsi quality yang relevan. Didukung [yt-dlp](https://github.com/yt-dlp/yt-dlp) di belakang layar, plus `curl_cffi` buat lolos bot-check YouTube.

> _"Satu command, langsung MP4/MP3."_

## 🎯 Fitur

| Fitur | Keterangan |
|-------|------------|
| 🔍 **Auto-detect** | Judul, durasi, dan estimasi ukuran terdeteksi otomatis |
| 🎛 **Opsi dinamis** | Menu quality menyesuaikan sendiri (video / audio saja) |
| 🎞 **Video MP4** | Pilihan quality Best/1080p/720p/480p/360p/Worst, thumbnail otomatis ter-embed |
| 🎵 **Audio MP3** | Pilihan bitrate Best/320kbps/192kbps/128kbps |
| 📜 **Playlist** | Default video pertama saja; `--playlist all` untuk semua sekaligus |
| 💬 **Subtitle & metadata** | Download subtitle + embed ke MP4, opsional via flag/CLI |
| 🌍 **Tampilan EN/ID** | Bahasa CLI via `--ui-lang id`, `LUMENFETCH_LANG`, atau setting yang diingat |
| 📋 **Auto-paste clipboard** | Kalau ada link valid di clipboard, langsung ditawarkan tanpa perlu paste manual - tidak akan nanya ulang isi clipboard yang sama berkali-kali |
| 📊 **Progress bar real-time** | Kecepatan, ukuran, dan estimasi waktu tersisa lewat `rich` |
| 📐 **Estimasi ukuran & waktu** | Muncul di menu pilih quality, dihitung dari data yt-dlp + kecepatan rata-rata download kamu sebelumnya |
| 🔄 **Auto-retry & resume** | Error koneksi dicoba ulang otomatis dengan backoff (default 3x); file parsial `.part` dilanjutkan, bukan diulang dari awal |
| 🗂 **Riwayat download** | 20 entri terakhir tersimpan, bisa dilihat kapan saja lewat command `history` |
| ⚙️ **Pengaturan persisten** | Folder download, max retry, auto-paste, dan naming template diingat |
| 🍪 **Cookies browser/file** | Opsional, buat video age-restricted/private - dari Chrome/Firefox/Edge/dll atau file `cookies.txt` |
| 🧼 **Nama file aman** | Karakter ilegal disanitasi, duplikat otomatis dikasih suffix `(1)`, `(2)`, dst |
| 🔔 **Auto-check update yt-dlp** | Tiap dibuka, dicek ke PyPI apakah ada versi yt-dlp lebih baru - gagal cek (mis. offline) diam-diam diabaikan |

## 📦 Requirements

- **Python** 3.9 atau lebih baru
- **Koneksi internet**
- Library: `yt-dlp`, `rich`, `curl_cffi`, otomatis terinstall bareng `lumenfetch`, tidak perlu diinstall manual

> ffmpeg **tidak perlu diinstall manual** - Lumenfetch memakai ffmpeg sistem kalau ada, kalau tidak otomatis mengunduh versi bundled-nya sendiri (lewat `static-ffmpeg`) begitu pertama kali dibutuhkan.

### Belum pernah pakai terminal? Ikuti ini dulu

<details>
<summary><b>🪟 Cara buka terminal di Windows</b></summary>

1. Tekan tombol **Windows**, ketik `PowerShell`, lalu tekan **Enter**
2. Jendela hitam/biru akan terbuka. Semua perintah `python ...` atau `pip ...` di panduan ini diketik di jendela itu, lalu tekan **Enter**

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
2. **Khusus Windows**: saat instalasi, centang dulu kotak **"Add Python to PATH"** di layar pertama sebelum klik Install. Kalau ini kelewat, perintah `python` nanti tidak akan dikenali
3. Setelah selesai install, buka terminal (lihat panduan di atas) lalu cek dengan:

```bash
python --version
# atau
python3 --version
```

Kalau muncul angka versi (misal `Python 3.12.1`), berarti sudah siap.

## 🚀 Instalasi

### Cara A: Install dari PyPI (paling gampang)

```bash
pip install lumenfetch
```

> Kalau `pip` tidak dikenali, coba:
> ```bash
> python -m pip install lumenfetch
> ```

> Kalau muncul error `externally-managed-environment` (biasanya di Linux):
> ```bash
> pip install lumenfetch --break-system-packages
> ```

Setelah terinstall, command `lumenfetch` langsung bisa dipakai dari terminal mana saja, lanjut ke bagian [Cara Pakai](#️-cara-pakai).

### Cara B: Install dari source (untuk development / mau lihat/ubah kode)

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
4. Di terminal, masuk ke folder hasil ekstrak, contoh:

```bash
cd Downloads/lumenfetch-main
```

</details>

**2. Install dalam mode "editable"**
```bash
pip install -e .
```

> Sama seperti Cara A, tambahkan `--break-system-packages` di akhir kalau muncul error `externally-managed-environment`.

Ini juga mendaftarkan command `lumenfetch`, tapi mengambil kodenya langsung dari folder ini, cocok kalau kamu mau modifikasi kode dan langsung lihat hasilnya tanpa install ulang.

## 🖥️ Cara Pakai

**Jalankan:**
```bash
lumenfetch
```

> Kalau kamu install dari source tanpa `pip install -e .`, jalankan lewat `python main.py` dari dalam folder project, tapi cara Editable Install di atas lebih direkomendasikan.

**Paste link YouTube saat diminta:**
```
Masukkan URL YouTube (q: keluar, history, settings, help): https://youtube.com/watch?v=...
```

Kalau ada link valid di clipboard, Lumenfetch akan menawarkannya duluan - tinggal jawab `y` kalau mau pakai itu.

**Pilih tipe output:**
```
Pilih tipe output:
  [1] Video (MP4)
  [2] Audio (MP3)
```

**Pilih quality (estimasi ukuran & waktu included):**
```
Pilih Quality:
  [1] Best   (default)  (~147.8 MB, ~31 detik)
  [2] 1080p              (~147.8 MB, ~31 detik)
  [3] 720p               (~81.1 MB, ~17 detik)
  [4] 480p               (~42.9 MB, ~9 detik)
```

**Konfirmasi nama file, lalu proses download berjalan** dengan progress bar real-time (kecepatan, ukuran, ETA). Tekan `Ctrl+C` kapan saja untuk membatalkan dengan aman.

**Done! 🎉**
```
✅ Selesai!
   File  : C:\Users\user\Downloads\YouTube_Lofi-Hip-Hop-Radio_2026.mp4
   Ukuran: 81.1 MB
   Waktu : 17 detik
```

## ↻ Resume Otomatis

Kalau proses download terhenti di tengah jalan (koneksi putus, terminal ditutup), file parsial `.part` tetap tersimpan di disk.

Jalankan lagi URL yang sama dan download akan **dilanjutkan** dari posisi terakhir, bukan diulang dari awal. Error koneksi juga dicoba ulang otomatis dengan backoff eksponensial (2s, 4s, 8s... max 30s).

## ⚙️ Preferensi Tersimpan

Folder download, max retry, auto-paste, naming template, dan pilihan cookies kamu otomatis tersimpan di config user dan dipakai lagi sebagai default di sesi berikutnya:

| OS | Lokasi config |
|----|---------------|
| 🪟 Windows | `%APPDATA%\lumenfetch\config.json` |
| 🍎 macOS | `~/Library/Application Support/lumenfetch/config.json` |
| 🐧 Linux | `~/.config/lumenfetch/config.json` |

Log detail tersimpan di `lumenfetch.log` sefolder config (jalankan dengan `-v/--verbose` untuk level debug).

## 🌍 Bahasa Tampilan

Tampilan CLI (menu, prompt, pesan error, dan teks `--help`) tersedia dalam **English** (default) dan **Bahasa Indonesia**.

```bash
lumenfetch --ui-lang id              # Bahasa Indonesia, diingat untuk sesi berikutnya
lumenfetch --ui-lang en              # kembali ke English
LUMENFETCH_LANG=id lumenfetch        # lewat environment variable (Windows: set LUMENFETCH_LANG=id)
```

Urutan prioritas: `--ui-lang` → env `LUMENFETCH_LANG` → `ui_lang` di config user → default `en`.

## 📜 Playlist

Link playlist secara default cuma download **video pertama** (dengan warning), biar satu URL tidak diam-diam membanjiri folder kamu. Buat ambil semuanya sekaligus sebagai file ber-index:

```bash
lumenfetch "https://youtube.com/playlist?list=PLxxxxxx" --playlist all -y
```

## 📦 Batch Download

Tulis daftar URL di file teks (satu per baris, `#` = komentar), lalu:

```bash
lumenfetch --batch daftar.txt --jobs 2
```

## 🍪 Cookies (Opsional)

Video age-restricted atau private butuh login. Kalau ketemu error semacam itu, aktifkan salah satu:

**A. Cookies dari browser:**
1. Buka Lumenfetch, ketik `settings`
2. Pilih `[5] Pakai cookies dari browser/file`
3. Pilih browser di mana kamu sudah login YouTube (Chrome/Firefox/Edge/Brave/Opera/Vivaldi/Safari)

Setelah aktif, Lumenfetch akan meminjam cookies dari browser itu setiap kali mendeteksi atau mendownload konten, seolah request-nya datang dari sesi browser kamu yang sudah login. Cukup pilih `[1] Nonaktifkan` di menu yang sama kalau mau matikan lagi.

> **Penting:** browser yang dipilih harus **benar-benar tertutup total** saat download (file cookies dikunci selama browser terbuka - errornya `Could not copy ... cookie database`). Cek Task Manager dan matikan semua proses browser tersebut (Edge/Chrome sering masih jalan di background).

**B. File cookies (paling reliable, disarankan kalau error cookies terus muncul):**
1. Install extension **"Get cookies.txt LOCALLY"** (Chrome/Edge/Firefox) di browser
2. Buka youtube.com (pastikan sudah login), klik extension → **Export** → simpan mis. `D:\cookies.txt`
3. Di Lumenfetch: `settings` → `[5]` → `[1] Nonaktifkan` → isi path file cookies tadi
4. Atau via CLI: `lumenfetch <URL> --cookies-file D:\cookies.txt`

## 🤖 Mode Non-Interaktif (Scripting/Otomatisasi)

Selain mode tanya-jawab, Lumenfetch juga bisa dijalankan lewat argumen command line, cocok buat dijadwalkan (cron/Task Scheduler) atau dipanggil dari script lain.

```bash
lumenfetch "https://youtube.com/watch?v=..." -t video -f mp4 -q 720p -y
```

**Argumen yang tersedia:**

| Argumen | Keterangan |
|---|---|
| `url` | Link video/playlist YouTube. Mengisi ini + flag lain mengaktifkan mode non-interaktif. |
| `-t/--type {video,audio}` | Tipe output |
| `-f/--format {mp4,mp3}` | Format file output |
| `-q/--quality` | Quality video (Best/1080p/720p/480p/360p/Worst) atau bitrate MP3 (Best/320kbps/192kbps/128kbps) |
| `-o/--output` | Folder penyimpanan custom |
| `--cookies` | Cookies browser (chrome/firefox/edge/brave/opera/vivaldi/safari/none) |
| `--cookies-file` | File cookies format Netscape |
| `--max-retry` | Jumlah retry koneksi |
| `--playlist {single,all}` | Mode playlist |
| `--subs` | Download subtitle bila tersedia |
| `--sub-langs` | Bahasa subtitle, dipisah koma (default: en,id) |
| `--embed-subs` | Embed subtitle ke file MP4 |
| `--embed-metadata` | Embed metadata (judul/artis) ke file hasil |
| `--batch` | File teks berisi daftar URL (satu per baris) |
| `--jobs N` | Paralel batch 1-4 (default 1) |
| `--no-clipboard` | Jangan tawarkan isi clipboard |
| `--ui-lang {en,id}` | Bahasa tampilan CLI (default `en`, diingat setelah dipilih) |
| `-y/--yes` | Lewati konfirmasi nama file |
| `-v/--verbose` | Log detail ke file + console |
| `--history` | Tampilkan riwayat lalu keluar |
| `--version` | Tampilkan versi |

**Contoh lain:**

```bash
# Audio saja, bitrate terbaik
lumenfetch "https://youtube.com/watch?v=..." -t audio -q 320kbps -y

# Seluruh playlist jadi MP4
lumenfetch "https://youtube.com/playlist?list=PLxxx" --playlist all -y

# Dengan subtitle ter-embed
lumenfetch "https://youtube.com/watch?v=..." -t video --subs --embed-subs -y

# Batch banyak URL, 2 paralel
lumenfetch --batch daftar.txt --jobs 2

# Lihat semua opsi
lumenfetch --help
```

## 📂 Struktur Output

Nama file mengikuti template di settings (default: `%(platform)s_%(title)s_%(year)s`):

```
YouTube_Lofi-Hip-Hop-Radio_2026.mp4
YouTube_Lofi-Hip-Hop-Radio_2026.mp3
```

## 🗺️ Folder Default per OS

| Sistem Operasi | Folder Default |
|----------------|----------------|
| 🪟 Windows | `C:\Users\<namauser>\Downloads` |
| 🍎 macOS | `/Users/<namauser>/Downloads` |
| 🐧 Linux | `/home/<namauser>/Downloads` |

Ganti kapan saja lewat command `settings` (`[1]`), path absolut maupun `~` sama-sama bisa.

## ⚠️ Troubleshooting

| Masalah | Solusi |
|---------|--------|
| `ModuleNotFoundError: No module named 'yt_dlp'` / `'rich'` / `'curl_cffi'` | Jalankan ulang `pip install lumenfetch` (atau `pip install -r requirements.txt` dari source) |
| `HTTP Error 403: Forbidden` | Update yt-dlp ke versi terbaru: `pip install --upgrade yt-dlp` |
| `Sign in to confirm you're not a bot` | Aktifkan fitur **Cookies** di atas (browser atau file) |
| `❌ Konten ini private / tidak bisa diakses` | Video private/age-restricted - aktifkan **Cookies** di atas |
| `❌ Format tidak tersedia untuk konten ini` | Coba quality lain |
| `❌ Koneksi internet bermasalah` terus muncul | Cek koneksi, atau naikkan `max_retry` lewat command `settings` |
| Video berhasil download tapi tidak ada suara | Jarang terjadi karena ffmpeg sudah bundled otomatis, tapi kalau muncul, jalankan ulang aplikasinya (bundle diunduh ulang otomatis kalau file sebelumnya rusak) |
| Ganti naming template di `settings` ditolak | Template cuma boleh pakai `%(platform)s`, `%(title)s`, `%(year)s` - ditolak otomatis kalau ada placeholder salah ketik, biar tidak bikin nama file error saat download |
| `⚠️ URL ini playlist berisi N video` | Default cuma video pertama. Gunakan `--playlist all` untuk download semua sebagai file ber-index |
| Batch download | Buat file teks (satu URL per baris, `#` = komentar), lalu `lumenfetch --batch daftar.txt --jobs 2` |
| Resume download | Didukung via `continuedl` yt-dlp + retry backoff eksponensial (2s, 4s, 8s... max 30s). File parsial `.part` dilanjutkan, bukan diulang dari 0 |
| `ffmpeg tidak ditemukan` | Install ffmpeg sistem dulu (lebih ringan), fallback bundled otomatis. Cek dengan `ffmpeg -version` |

## 📝 Catatan Penting

- Cuma link YouTube yang diterima (`youtube.com`, `youtu.be`, `music.youtube.com`) - platform lain ditolak dengan pesan yang jelas, bukan crash
- Pesan `Sign in to confirm you're not a bot` berarti YouTube menantang request otomatis: install/update `curl_cffi` + `yt-dlp`, lalu aktifkan cookies
- Tool ini buat download video yang memang boleh kamu simpan (upload sendiri, Creative Commons, nonton offline). Hormati hak cipta kreator

## 🛠️ Dibuat dengan

![Python](https://img.shields.io/badge/-Python-3776AB?style=flat-square&logo=python&logoColor=white)
![yt-dlp](https://img.shields.io/badge/-yt--dlp-FF6B6B?style=flat-square)
![Rich](https://img.shields.io/badge/-Rich-FAE742?style=flat-square)
![curl-cffi](https://img.shields.io/badge/-curl--cffi-2B579A?style=flat-square)

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
├── requirements.txt           # Daftar dependency (untuk referensi manual)
├── pyproject.toml             # Metadata package + entry point + konfigurasi ruff
├── CONTRIBUTING.md            # Panduan kontribusi
├── LICENSE
├── README.md                  # Dokumentasi utama (English)
└── README.id.md               # Dokumentasi (Bahasa Indonesia)
```

**Prinsip pemisahan modul:**
- `constants.py`, nilai shared (versi, format, batas) biar tidak drift antar modul
- `errors.py`, klasifikasi error terpusat, dipakai detector & downloader bersama
- `detector.py`, murni deteksi info video YouTube, tidak mendownload apa pun
- `downloader.py`, murni proses download MP4/MP3 & progress, tidak menampilkan menu
- `options.py`, semua interaksi & tampilan menu, tidak ada logic download
- `utils.py`, helper murni (sanitasi, format, baca/tulis config), tidak tahu soal CLI atau jaringan
- `main.py`, menyatukan semuanya lewat CLI + loop utama

## 🧪 Testing

Ada unit test per modul (sanitasi nama file, naming template, resolve duplikat, format ukuran/durasi, config, validasi URL YouTube, opts yt-dlp, CLI, dll).

```bash
pip install -e .[dev]
pytest tests/ -v
ruff check .
```

CI (`.github/workflows/tests.yml`) otomatis menjalankan ini di setiap push & pull request ke `main`.

## 🤝 Kontribusi

Mau bantu kembangin Lumenfetch? Baca [`CONTRIBUTING.md`](CONTRIBUTING.md) untuk struktur project dan alur kontribusi.

## ❓ FAQ

<details>
<summary><b>Apakah ini legal / aman dipakai?</b></summary>

Tool ini memakai request yang sama seperti browser kamu saat nonton YouTube, jadi tidak meng-hack apa pun. Tapi gunakan secara bertanggung jawab: download untuk pribadi/offline, dan hormati hak cipta kreator. Jangan upload ulang atau jual konten orang lain.

</details>

<details>
<summary><b>Apakah butuh akun YouTube?</b></summary>

Tidak, untuk video publik. Cuma butuh login (via cookies) untuk video age-restricted/private yang memang bisa kamu akses.

</details>

<details>
<summary><b>Video private / dihapus, bisa didownload?</b></summary>

Tidak. Cuma konten yang memang bisa kamu tonton yang bisa didownload.

</details>

<details>
<summary><b>Prosesnya lama, kenapa?</b></summary>

Kecepatan mengikuti koneksimu. Error koneksi dicoba ulang otomatis dengan backoff, dan download yang terputus dilanjutkan, bukan diulang.

</details>

<details>
<summary><b>Quality mana yang sebaiknya dipilih?</b></summary>

- Mau kualitas terbaik → **Best**
- Mau file kecil buat HP → **720p** atau **480p**
- Cuma butuh audio (musik/podcast) → **MP3 320kbps**

</details>

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
