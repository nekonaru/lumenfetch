<div align="center">
  <h1>Lumenfetch: Pengunduh YouTube</h1>
  <p><b>Simpan video YouTube apa pun sebagai <code>.mp4</code> atau <code>.mp3</code>, dengan pemilih kualitas, subtitle, dan playlist,<br/>
  langsung dari terminalmu.</b></p>

  <a href="https://pypi.org/project/lumenfetch/"><img src="https://img.shields.io/pypi/v/lumenfetch?style=flat-square&color=blue" alt="PyPI" /></a>
  <a href="https://github.com/nekonaru/lumenfetch/actions"><img src="https://github.com/nekonaru/lumenfetch/actions/workflows/tests.yml/badge.svg" alt="Tests" /></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python" /></a>
  <a href="https://github.com/nekonaru/lumenfetch/releases"><img src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey?style=flat-square" alt="Platform" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="License" /></a>
  <a href="https://github.com/nekonaru/lumenfetch"><img src="https://img.shields.io/badge/Status-Active-brightgreen?style=flat-square" alt="Status" /></a>
</div>

<br />

[English](README.md) | **Bahasa Indonesia**

> [!CAUTION]
> Tool ini untuk mengunduh video yang memang berhak kamu simpan (unggahanmu sendiri, Creative Commons, tontonan offline). Hormati hak cipta kreator. Jangan mengunggah ulang atau menjual konten orang lain.

---

## Daftar Isi

- [Tentang](#tentang)
- [Fitur](#fitur)
- [Persyaratan](#persyaratan)
- [Instalasi](#instalasi)
- [Penggunaan](#penggunaan)
- [Resume Otomatis](#resume-otomatis)
- [Preferensi Tersimpan](#preferensi-tersimpan)
- [Bahasa Tampilan](#bahasa-tampilan)
- [Playlist](#playlist)
- [Unduhan Batch](#unduhan-batch)
- [Cookie (Opsional)](#cookie-opsional)
- [Mode Non-Interaktif (Skrip/Otomasi)](#mode-non-interaktif-skripotomasi)
- [Struktur Output](#struktur-output)
- [Folder Default per OS](#folder-default-per-os)
- [Pemecahan Masalah](#pemecahan-masalah)
- [Catatan Penting](#catatan-penting)
- [Dibangun Dengan](#dibangun-dengan)
- [Struktur Proyek](#struktur-proyek)
- [Pengujian](#pengujian)
- [Continuous Integration](#continuous-integration)
- [Kontribusi](#kontribusi)
- [FAQ](#faq)
- [Penulis](#penulis)
- [Lisensi](#lisensi)

---

## Tentang

**Lumenfetch** adalah CLI Python ringan yang mengunduh video YouTube sebagai **MP4** atau mengekstrak audionya sebagai **MP3**. Cukup tempel link dan aplikasi mendeteksi judul, durasi, serta perkiraan ukuran file secara otomatis, lalu menawarkan pilihan kualitas yang relevan. Ditenagai [yt-dlp](https://github.com/yt-dlp/yt-dlp) di balik layar, plus `curl_cffi` untuk melewati pemeriksaan bot YouTube.

> _"Satu perintah, langsung ke MP4/MP3."_

---

## Fitur

### Pengunduhan

| Fitur | Deskripsi |
|-------|-----------|
| **Video MP4** | Kualitas Best/1080p/720p/480p/360p/Worst, thumbnail disematkan otomatis |
| **Audio MP3** | Bitrate Best/320kbps/192kbps/128kbps |
| **Playlist** | Hanya video pertama secara default; `--playlist all` untuk seluruh daftar |
| **M3U otomatis** | Playlist audio (`--playlist all`) juga menulis file `.m3u` |
| **Subtitle & metadata** | Unduh subtitle + sematkan ke MP4, opsional lewat flag |
| **Nama file aman** | Karakter terlarang dibersihkan, duplikat mendapat akhiran `(1)`, `(2)` |
| **Cookie browser/file** | Opsional, untuk video dibatasi usia atau privat, dari Chrome/Firefox/Edge/dll. atau file `cookies.txt` |

### Deteksi dan Opsi

| Fitur | Deskripsi |
|-------|-----------|
| **Deteksi otomatis** | Judul, durasi, dan perkiraan ukuran terdeteksi otomatis |
| **Opsi dinamis** | Menu kualitas menyesuaikan diri (video vs audio) |
| **Perkiraan ukuran & waktu** | Ditampilkan di samping setiap pilihan kualitas, dihitung dari data yt-dlp + kecepatan unduhmu sebelumnya |
| **Tempel otomatis dari clipboard** | Link valid di clipboard langsung ditawarkan, tidak pernah ditanya dua kali untuk konten yang sama |

### Keandalan

| Fitur | Deskripsi |
|-------|-----------|
| **Coba ulang & resume otomatis** | Error koneksi dicoba ulang dengan exponential backoff (default 3x); file `.part` parsial dilanjutkan, bukan diulang dari awal |
| **Doctor** | `lumenfetch --doctor` mendiagnosis setup (ffmpeg, dependensi, cookie, jaringan) |
| **Pemberitahuan update diri** | Memberi tahu saat lumenfetch yang lebih baru ada di PyPI |
| **Cek update yt-dlp** | Memeriksa PyPI untuk yt-dlp yang lebih baru setiap kali mulai, diabaikan diam-diam saat offline |

### Antarmuka dan Pengaturan

| Fitur | Deskripsi |
|-------|-----------|
| **Progres real-time** | Kecepatan, ukuran, dan ETA lewat `rich` |
| **Antarmuka Inggris/Indonesia** | Bahasa tampilan lewat `--ui-lang id`, `LUMENFETCH_LANG`, atau pengaturan yang diingat |
| **Riwayat unduhan** | 20 entri terakhir, bisa dilihat kapan saja dengan perintah `history` (`history clear` menghapusnya) |
| **Pengaturan tersimpan** | Folder unduhan, max retry, auto-paste, dan template penamaan diingat |

---

## Persyaratan

| Dependensi | Versi Minimum | Catatan |
|------------|---------------|---------|
| **Python** | 3.9 | Wajib |
| **Koneksi internet** | apa saja | Wajib |
| **Library** | lihat catatan | `yt-dlp`, `rich`, `curl_cffi`, terinstal otomatis bersama `lumenfetch`, tidak perlu instal manual |
| **ffmpeg** | apa saja | Tidak wajib diinstal manual, lihat catatan di bawah |

> [!TIP]
> ffmpeg **tidak perlu diinstal manual**. Lumenfetch memakai ffmpeg sistemmu jika ada, jika tidak ia mengunduh sendiri salinan bawaannya (lewat `static-ffmpeg`) otomatis saat pertama dipakai, seperti `ffmpeg-static` di proyek Node.js.

### Belum pernah memakai terminal? Mulai dari sini

<details>
<summary><b>Membuka terminal di Windows</b></summary>

1. Tekan tombol **Windows**, ketik `PowerShell`, lalu tekan **Enter**
2. Jendela hitam/biru akan terbuka. Ketik semua perintah `python ...` / `pip ...` dari panduan ini di sana, lalu tekan **Enter**

</details>

<details>
<summary><b>Membuka terminal di macOS</b></summary>

1. Tekan **Cmd + Space**, ketik `Terminal`, lalu tekan **Enter**
2. Ketik perintah dari panduan ini di sana, lalu tekan **Enter**

</details>

<details>
<summary><b>Membuka terminal di Linux</b></summary>

Tekan **Ctrl + Alt + T**, atau cari aplikasi "Terminal" di menu aplikasimu.

</details>

### Belum punya Python?

1. Buka [python.org/downloads](https://www.python.org/downloads/) dan unduh versi terbaru
2. **Khusus Windows**: di layar pertama installer, centang **"Add Python to PATH"** sebelum menekan Install
3. Setelah terinstal, buka terminal (lihat di atas) dan cek dengan:

```bash
python --version
# atau
python3 --version
```

Jika nomor versi muncul (misalnya `Python 3.12.1`), kamu sudah siap.

> [!WARNING]
> Di Windows, jika kotak **"Add Python to PATH"** terlewat, perintah `python` tidak akan dikenali nantinya.

---

## Instalasi

### Opsi A: Instal dari PyPI (paling mudah)

```bash
pip install lumenfetch
```

> [!TIP]
> Jika `pip` tidak dikenali, coba `python -m pip install lumenfetch`.

> [!NOTE]
> Jika muncul error `externally-managed-environment` (biasanya di Linux), jalankan:
> ```bash
> pip install lumenfetch --break-system-packages
> ```

Setelah terinstal, perintah `lumenfetch` bisa dijalankan dari terminal mana pun, lanjut ke [Penggunaan](#penggunaan).

### Opsi B: Instal dari source (untuk pengembangan / membaca kode)

#### 1. Ambil kodenya

<details>
<summary><b>Sudah menginstal Git</b></summary>

```bash
git clone https://github.com/nekonaru/lumenfetch.git
cd lumenfetch
```

</details>

<details>
<summary><b>Belum punya Git</b></summary>

1. Buka halaman repositori di GitHub
2. Klik tombol hijau **`Code`**, lalu pilih **`Download ZIP`**
3. Ekstrak ZIP yang diunduh ke folder pilihanmu
4. Di terminal, masuk ke folder hasil ekstrak, contoh:

```bash
cd Downloads/lumenfetch-main
```

</details>

#### 2. Instal dalam mode "editable"

```bash
pip install -e .
```

> [!NOTE]
> Sama seperti Opsi A, tambahkan `--break-system-packages` jika muncul error `externally-managed-environment`.

Ini juga mendaftarkan perintah `lumenfetch`, tetapi kodenya dipakai langsung dari folder ini, praktis jika kamu ingin mengubah kode dan melihat hasilnya tanpa instal ulang.

---

## Penggunaan

> [!NOTE]
> Contoh tampilan di bawah memakai bahasa default CLI (English). Gunakan `--ui-lang id` untuk tampilan berbahasa Indonesia.

**Jalankan:**

```bash
lumenfetch
```

> [!NOTE]
> Jika kamu menginstal dari source tanpa `pip install -e .`, jalankan lewat `python main.py` dari dalam folder proyek, tetapi instalasi editable di atas lebih disarankan.

**Tempel URL YouTube saat diminta:**

```
Enter YouTube URL (q: quit, history, settings, help): https://youtube.com/watch?v=...
```

Jika ada link valid di clipboard, Lumenfetch menawarkannya lebih dulu, cukup jawab `y` untuk memakainya.

**Pilih tipe output:**

```
Choose output type:
  [1] Video (MP4)
  [2] Audio (MP3)
```

**Pilih kualitas (sudah termasuk perkiraan ukuran & ETA):**

```
Choose Quality:
  [1] Best   (default)  (~147.8 MB, ~31 seconds)
  [2] 1080p              (~147.8 MB, ~31 seconds)
  [3] 720p               (~81.1 MB, ~17 seconds)
  [4] 480p               (~42.9 MB, ~9 seconds)
```

**Konfirmasi nama file, lalu unduhan berjalan** dengan progress bar real-time (kecepatan, ukuran, ETA). Tekan `Ctrl+C` kapan saja untuk membatalkan dengan aman.

**Selesai!**

```
Done!
   File  : C:\Users\user\Downloads\YouTube_Lofi-Hip-Hop-Radio_2026.mp4
   Size: 81.1 MB
   Time : 17 seconds
```

---

## Resume Otomatis

Jika unduhan berhenti di tengah jalan (koneksi putus, terminal ditutup), file `.part` parsial tetap ada di disk.

Cukup jalankan URL yang sama lagi dan yt-dlp **melanjutkan** dari titik terakhir, bukan mulai dari awal. Error koneksi juga dicoba ulang otomatis dengan exponential backoff (2d, 4d, 8d... maks 30d).

---

## Preferensi Tersimpan

Folder unduhan, max retry, auto-paste, template penamaan, dan pilihan cookie disimpan otomatis di folder config pengguna dan dipakai sebagai default di sesi berikutnya:

| OS | Lokasi config |
|----|---------------|
| Windows | `%APPDATA%\lumenfetch\config.json` |
| macOS | `~/Library/Application Support/lumenfetch/config.json` |
| Linux | `~/.config/lumenfetch/config.json` |

Log detail disimpan di `lumenfetch.log` pada folder yang sama (jalankan dengan `-v/--verbose` untuk level debug).

---

## Bahasa Tampilan

CLI (menu, prompt, pesan, dan teks `--help`) tersedia dalam **English** (default) dan **Bahasa Indonesia**.

```bash
lumenfetch --ui-lang id              # Bahasa Indonesia, diingat untuk sesi berikutnya
lumenfetch --ui-lang en              # kembali ke English
LUMENFETCH_LANG=id lumenfetch        # lewat environment variable (Windows: set LUMENFETCH_LANG=id)
```

Urutan prioritas: `--ui-lang` → env `LUMENFETCH_LANG` → `ui_lang` di config pengguna → default `en`.

---

## Playlist

URL playlist hanya mengunduh **video pertama** secara default (dengan peringatan), sehingga satu URL tidak pernah diam-diam membanjiri foldermu. Untuk mengambil seluruh daftar sebagai file berindeks:

```bash
lumenfetch "https://youtube.com/playlist?list=PLxxxxxx" --playlist all -y
```

---

## Unduhan Batch

Taruh satu URL per baris di file teks (`#` = komentar), lalu:

```bash
lumenfetch --batch daftar.txt --jobs 2
```

---

## Cookie (Opsional)

Video dibatasi usia atau privat membutuhkan login. Jika kamu menemui error seperti itu, aktifkan salah satu cara ini:

### A. Cookie browser

1. Buka Lumenfetch, ketik `settings`
2. Pilih `[5] Use browser/file cookies`
3. Pilih browser tempat kamu login ke YouTube (Chrome/Firefox/Edge/Brave/Opera/Vivaldi/Safari)

> [!IMPORTANT]
> Browser yang dipilih harus **ditutup sepenuhnya** saat mengunduh (file cookie-nya terkunci selama browser terbuka, errornya tampak seperti `Could not copy ... cookie database`). Cek Task Manager dan matikan semua prosesnya (Edge/Chrome sering tetap berjalan di latar belakang).

### B. File cookie (paling andal, disarankan jika error cookie terus muncul)

1. Pasang ekstensi **"Get cookies.txt LOCALLY"** (Chrome/Edge/Firefox)
2. Buka youtube.com (pastikan kamu sudah login), klik ekstensinya, lalu **Export** dan simpan misalnya `D:\cookies.txt`
3. Di Lumenfetch: `settings` → `[5]` → `[1] Disable` → masukkan path file cookie
4. Atau lewat CLI: `lumenfetch <URL> --cookies-file D:\cookies.txt`

---

## Mode Non-Interaktif (Skrip/Otomasi)

Selain mode tanya-jawab, Lumenfetch juga berjalan lewat argumen command line, praktis untuk penjadwalan (cron/Task Scheduler) atau dipanggil dari skrip lain.

```bash
lumenfetch "https://youtube.com/watch?v=..." -t video -f mp4 -q 720p -y
```

### Argumen yang tersedia

| Argumen | Deskripsi |
|---|---|
| `url` | URL video/playlist YouTube. Mengisinya mengaktifkan mode non-interaktif bila digabung dengan flag lain. |
| `-t/--type {video,audio}` | Tipe output |
| `-f/--format {mp4,mp3}` | Format output |
| `-q/--quality` | Kualitas video (Best/1080p/720p/480p/360p/Worst) atau bitrate MP3 (Best/320kbps/192kbps/128kbps) |
| `-o/--output` | Folder output kustom |
| `--cookies` | Cookie browser (chrome/firefox/edge/brave/opera/vivaldi/safari/none) |
| `--cookies-file` | File cookie berformat Netscape |
| `--max-retry` | Jumlah percobaan ulang koneksi |
| `--playlist {single,all}` | Mode playlist |
| `--subs` | Unduh subtitle jika tersedia |
| `--sub-langs` | Bahasa subtitle, dipisah koma (default: en,id) |
| `--embed-subs` | Sematkan subtitle ke file MP4 |
| `--embed-metadata` | Sematkan metadata (judul/artis) ke file output |
| `--sponsorblock [cats...]` | Lewati segmen SponsorBlock (misalnya `--sponsorblock sponsor intro outro`) |
| `--write-info-json` | Simpan metadata video sebagai `.info.json` di samping file |
| `--batch` | File teks berisi URL (satu per baris) |
| `--jobs N` | Paralelisme batch 1-4 (default 1) |
| `--no-clipboard` | Jangan tawarkan isi clipboard |
| `--ui-lang {en,id}` | Bahasa tampilan (default `en`, diingat setelah diatur) |
| `--doctor` | Diagnosis setup (ffmpeg, dependensi, cookie, jaringan) lalu keluar |
| `-y/--yes` | Lewati konfirmasi nama file |
| `-v/--verbose` | Logging detail ke file + konsol |
| `--history` | Tampilkan riwayat lalu keluar |
| `--version` | Tampilkan versi |

### Contoh lainnya

```bash
# Audio saja, bitrate terbaik
lumenfetch "https://youtube.com/watch?v=..." -t audio -q 320kbps -y

# Seluruh playlist sebagai MP4
lumenfetch "https://youtube.com/playlist?list=PLxxx" --playlist all -y

# Dengan subtitle tersemat
lumenfetch "https://youtube.com/watch?v=..." -t video --subs --embed-subs -y

# Batch URL, 2 sekaligus
lumenfetch --batch daftar.txt --jobs 2

# Lihat semua opsi
lumenfetch --help
```

---

## Struktur Output

Nama file mengikuti template di pengaturan (default: `%(platform)s_%(title)s_%(year)s`):

```
YouTube_Lofi-Hip-Hop-Radio_2026.mp4
YouTube_Lofi-Hip-Hop-Radio_2026.mp3
```

---

## Folder Default per OS

| OS | Folder default |
|----|----------------|
| Windows | `C:\Users\<username>\Downloads` |
| macOS | `/Users/<username>/Downloads` |
| Linux | `/home/<username>/Downloads` |

Ubah kapan saja lewat perintah `settings` (`[1]`), path absolut dan `~` sama-sama diterima.

---

## Pemecahan Masalah

| Masalah | Solusi |
|---------|--------|
| `ModuleNotFoundError: No module named 'yt_dlp'` / `'rich'` / `'curl_cffi'` | Jalankan ulang `pip install lumenfetch` (atau `pip install -r requirements.txt` dari source) |
| `HTTP Error 403: Forbidden` | Update yt-dlp: `pip install --upgrade yt-dlp` |
| `Sign in to confirm you're not a bot` | Aktifkan **Cookie** di atas (browser atau file) |
| `Private / unavailable content` | Video privat/dibatasi usia, aktifkan **Cookie** di atas |
| `Format not available for this content` | Coba kualitas lain |
| `Connection trouble` terus muncul | Periksa koneksimu, atau naikkan `max_retry` lewat `settings` |
| Video hasil unduhan tanpa suara | Jarang terjadi karena ffmpeg sudah bawaan, tetapi jika terjadi, restart aplikasi (bundel diunduh ulang otomatis jika rusak) |
| Template penamaan ditolak di `settings` | Hanya `%(platform)s`, `%(title)s`, `%(year)s` yang diizinkan, ditolak otomatis saat salah ketik agar nama file tidak pernah rusak |
| `Playlist with N videos` | Hanya video pertama secara default. Gunakan `--playlist all` untuk semuanya sebagai file berindeks |
| `ffmpeg not found` | Instal ffmpeg sistem dulu (lebih ringan), fallback bawaan otomatis. Cek dengan `ffmpeg -version` |
| `YouTube needs a JavaScript runtime` | Instal Deno (`winget install DenoLand.Deno`) atau Node.js, diperlukan untuk menyelesaikan tantangan signature YouTube |

---

## Catatan Penting

- Hanya link YouTube yang diterima (`youtube.com`, `youtu.be`, `music.youtube.com`), platform lain ditolak dengan pesan yang jelas, bukan crash
- Pesan `Sign in to confirm you're not a bot` berarti YouTube sedang menantang permintaan otomatis: instal/update `curl_cffi` + `yt-dlp`, lalu aktifkan cookie
- Tool ini untuk mengunduh video yang memang berhak kamu simpan (unggahanmu sendiri, Creative Commons, tontonan offline). Hormati hak cipta kreator

---

## Dibangun Dengan

<div align="center">

![Python](https://img.shields.io/badge/-Python-3776AB?style=flat-square&logo=python&logoColor=white)
![yt-dlp](https://img.shields.io/badge/-yt--dlp-FF6B6B?style=flat-square)
![Rich](https://img.shields.io/badge/-Rich-FAE742?style=flat-square)
![curl-cffi](https://img.shields.io/badge/-curl--cffi-2B579A?style=flat-square)

</div>

---

## Struktur Proyek

```
lumenfetch/
├── main.py                    # Entry point, argumen CLI, batch, loop utama
├── core/
│   ├── constants.py           # Sumber kebenaran tunggal (versi, format, batas)
│   ├── errors.py              # Taksonomi error pusat (klasifikasi + pesan ramah)
│   ├── i18n.py                # String UI (English default, Indonesia lewat --ui-lang)
│   ├── cli.py                 # Parsing argumen + penyusunan pilihan non-interaktif
│   ├── doctor.py              # Diagnosis setup (ffmpeg, dependensi, cookie, jaringan)
│   ├── ffmpeg.py              # ffmpeg sistem dulu, fallback bawaan
│   ├── log.py                 # Logging file terpusat
│   ├── downloader.py          # Unduh MP4 / ekstrak MP3 + resume + retry backoff
│   ├── detector.py            # Deteksi info video YouTube
│   ├── options.py             # Menu & prompt interaktif (rich)
│   ├── update_checker.py      # Cek otomatis yt-dlp yang lebih baru di PyPI
│   └── utils.py               # Pembersihan nama file, format ukuran, config pengguna
├── tests/
│   ├── conftest.py            # Fixture global (tanpa sleep) + SAMPLE_VIDEO_FORMATS
│   ├── test_utils.py
│   ├── test_detector.py
│   ├── test_downloader.py
│   ├── test_options.py
│   ├── test_main.py
│   └── test_features.py       # Fitur (CLI, backoff, batch, ffmpeg, cookie, log)
├── .github/
│   └── workflows/
│       └── tests.yml          # CI: tes otomatis & lint
├── requirements.txt           # Daftar dependensi (untuk referensi manual)
├── pyproject.toml             # Metadata paket + entry point + konfigurasi ruff
├── CONTRIBUTING.md            # Panduan kontribusi
├── LICENSE
├── README.md                  # Dokumentasi utama (Inggris)
└── README.id.md               # Dokumentasi (Bahasa Indonesia)
```

### Prinsip pemisahan modul

| Modul | Prinsip |
|-------|---------|
| `constants.py` | Nilai bersama (versi, format, batas) agar modul tidak pernah melenceng |
| `errors.py` | Klasifikasi error pusat yang dipakai detector & downloader bersama-sama |
| `detector.py` | Murni mendeteksi info video YouTube, tidak pernah mengunduh apa pun |
| `downloader.py` | Murni pemrosesan MP4/MP3 & progres, tidak pernah menampilkan menu |
| `options.py` | Semua interaksi pengguna & menu, tanpa logika unduhan |
| `utils.py` | Helper murni (pembersihan, format, baca/tulis config), tidak tahu apa-apa soal CLI atau jaringan |
| `main.py` | Menyatukan semuanya lewat CLI + loop utama |

---

## Pengujian

Unit test per modul (pembersihan nama file, template penamaan, penyelesaian duplikat, format ukuran/durasi, config, validasi URL YouTube, opsi yt-dlp, CLI, dan lainnya).

```bash
pip install -e .[dev]
pytest tests/ -v
ruff check .
```

---

## Continuous Integration

| Workflow | Fungsi |
|----------|--------|
| `tests.yml` | Tes otomatis & lint, berjalan di setiap push & pull request ke `main` |

---

## Kontribusi

Ingin membantu mengembangkan Lumenfetch? Baca [`CONTRIBUTING.md`](CONTRIBUTING.md) untuk struktur proyek dan alur kontribusi.

---

## FAQ

<details>
<summary><b>Apakah ini legal / aman dipakai?</b></summary>

Tool ini memakai permintaan yang sama dengan yang dibuat browsermu saat kamu menonton YouTube, jadi tidak meretas apa pun. Tetapi pakailah dengan bertanggung jawab: unduh untuk pemakaian pribadi/offline, dan hormati hak cipta kreator. Jangan mengunggah ulang atau menjual konten orang lain.

</details>

<details>
<summary><b>Apakah saya perlu akun YouTube?</b></summary>

Tidak, tidak untuk video publik. Kamu hanya perlu login (lewat cookie) untuk video dibatasi usia atau privat yang memang bisa kamu akses.

</details>

<details>
<summary><b>Video privat / yang sudah dihapus, bisakah diunduh?</b></summary>

Tidak. Hanya konten yang benar-benar bisa ditonton akunmu yang bisa diunduh.

</details>

<details>
<summary><b>Kenapa prosesnya lambat?</b></summary>

Kecepatan unduh mengikuti koneksimu. Error koneksi dicoba ulang otomatis dengan backoff, dan unduhan yang terputus dilanjutkan, bukan diulang dari awal.

</details>

<details>
<summary><b>Kualitas mana yang sebaiknya dipilih?</b></summary>

- Ingin yang terbaik yang tersedia: **Best**
- Ingin file lebih kecil untuk penyimpanan ponsel: **720p** atau **480p**
- Audio saja untuk musik/podcast: **MP3 320kbps**

</details>

---

## Penulis

<div align="center">

| [![Nicolas Dwi Dharma](https://github.com/github.png?size=100)](https://github.com/nekonaru) |
|:---:|
| **Nicolas Dwi Dharma** |
| [github.com/nekonaru](https://github.com/nekonaru) |

</div>

---

## Lisensi

Didistribusikan di bawah **Lisensi MIT**. Lihat [`LICENSE`](LICENSE) untuk informasi lebih lanjut.
