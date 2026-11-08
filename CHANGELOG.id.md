# Changelog

## v2.1.2

Rilis ini memperbaiki kegagalan download berulang (0 bytes, lalu error) yang terjadi bahkan untuk video publik.

### Fitur baru

- **Cek JavaScript di Doctor.** `lumenfetch --doctor` sekarang juga mengecek JavaScript runtime (Deno/Node), yang dibutuhkan untuk signature challenge YouTube.

### Peningkatan

- **Override `player_client` yang dipaksakan dihapus.** Itu memicu eksperimen SABR-only YouTube (cuma 5 format, bukan sekitar 46). Sekarang pakai default yt-dlp yang dirawat maintainer.
- **Error format yang transien ikut di-retry.** Error format sekarang mendapat backoff seperti error koneksi.
- **Crash post-processing tidak lagi menggagalkan video yang sebenarnya utuh.** Crash (mis. embed thumbnail) videonya tetap disimpan dengan warning.
- **Download paralel judul duplikat dapat nama file unik**, tidak saling merusak.

### Perbaikan bug

- **Hasil 0-byte sekarang gagal dengan jujur + bersih-bersih.** Hasil kosong tidak lagi dilaporkan sebagai sukses atau nyampah di folder.
- **File batch ber-prefix BOM tidak lagi dilewati diam-diam**, dan kegagalan per-URL di batch sekarang ditampilkan.

## v2.1.1

Rilis ini membuat English menjadi bahasa tampilan default dan me-refresh halaman PyPI.

### Fitur baru

- **`lumenfetch doctor`.** Mendiagnosa setup dalam hitungan detik, tiap cek dengan saran fix spesifik.
- **Notice self-update.** Memberi tahu kalau ada lumenfetch lebih baru di PyPI.
- **`--ui-lang en|id`.** Bahasa tampilan via flag, `LUMENFETCH_LANG`, atau setting `ui_lang` yang diingat.

### Breaking changes

- **Bahasa tampilan default sekarang English.** Jalankan `lumenfetch --ui-lang id` sekali untuk kembali ke Indonesia; pilihannya diingat.

## v2.1.0

Rilis ini menambahkan doctor setup, notice self-update, dan dukungan SponsorBlock.

### Fitur baru

- **`lumenfetch doctor`.** Mendiagnosa setup dalam hitungan detik: Python, ffmpeg, `curl_cffi`, versi yt-dlp, versi lumenfetch, keterjangkauan YouTube, keterbacaan cookies browser, dan keterulisan config, masing-masing dengan saran fix spesifik.
- **Notice self-update.** Memberi tahu kalau ada lumenfetch lebih baru di PyPI (`pip install --upgrade lumenfetch`), di samping notice yt-dlp yang sudah ada.
- **`--sponsorblock`.** Lewati segmen SponsorBlock, mis. `--sponsorblock sponsor intro outro`.
- **`--write-info-json`.** Simpan metadata video sebagai `.info.json` di sebelah file.
- **`.m3u` otomatis.** Playlist audio (`--playlist all`) sekarang juga nulis file `.m3u`.

### Peningkatan

- **Download paralel yang aman.** Dua worker batch untuk judul yang sama tidak lagi saling menimpa file (reservasi nama atomik, terverifikasi live 2/2).
- **Batch gagal yang bersuara.** Mode batch sekarang menampilkan URL mana yang gagal dan kenapa, bukan gagal diam-diam (termasuk file ber-prefix BOM dari PowerShell).
- **Terminal yang tenang.** Noise mentah `ERROR:` dari yt-dlp dialihkan ke `lumenfetch.log`; terminal cuma menampilkan pesan ramah.
- **Modul baru `core/cli.py` dan `core/doctor.py`.** Parsing argumen dan diagnostik dipisah dari `main.py`; `main.py` dirampingkan.
- **Coverage gate dan trusted publishing.** CI menegakkan coverage gate 80% dan publish ke PyPI tanpa token.
- **Exe Windows.** `lumenfetch.exe` terlampir di release, tanpa perlu Python.

### Perbaikan bug

- **URL batch ber-prefix BOM tidak lagi dilewati diam-diam.**
- **Mode batch tidak lagi menelan error per-URL** (ditampilkan bersama URL yang gagal).
- **Download paralel judul duplikat tidak lagi merusak output satu sama lain.**

## v2.0.0

Lumenfetch sekarang downloader YouTube yang fokus: video MP4 dan audio MP3, tidak yang lain.

### Fitur baru

- **Video MP4.** Quality Best/1080p/720p/480p/360p/Worst dengan thumbnail ter-embed otomatis.
- **Audio MP3.** Bitrate Best/320kbps/192kbps/128kbps.
- **CLI English dan Indonesia.** `--ui-lang en|id`; menu, prompt, tabel, pesan error, dan `--help` sepenuhnya bisa diterjemahkan. English menjadi default baru, diingat setelahnya. Juga via `LUMENFETCH_LANG` atau nilai `ui_lang` di config.
- **Dokumentasi dua bahasa.** `README.md` dan `CONTRIBUTING.md` berbahasa Inggris, dengan versi Indonesia di `README.id.md` dan `CONTRIBUTING.id.md`.

### Breaking changes

- **YouTube-only.** Cuma link `youtube.com`, `youtu.be`, dan `music.youtube.com` yang diterima. Platform lain ditolak dengan pesan yang jelas, bukan error menyesatkan.
- **Dependency yang dihapus.** `instaloader` dan `browser-cookie3` hilang; install jadi lebih ringan. Cookies browser/file untuk YouTube tetap jalan.
- **Template nama file output.** Nama file mengikuti `%(platform)s_%(title)s_%(year)s`, mis. `YouTube_Lofi-Hip-Hop-Radio_2026.mp4`.

### Peningkatan

- **Modul baru `core/i18n.py`.** Kamus teks tampilan (en/id); semua teks user lewat `t("key")`.
- **Taxonomy baru `core/errors.py`.** Setiap kegagalan yt-dlp dipetakan ke kind spesifik (bot-check, cookies, rate-limit, removed, dll) dengan pesan yang actionable, termasuk retry otomatis tanpa cookies kalau database cookies terkunci.
- **`curl_cffi` sekarang dependency wajib** biar lolos bot-check YouTube.
- **Config user pindah** ke folder config OS (`%APPDATA%` di Windows, `~/.config` di Linux, `~/Library/Application Support` di macOS), dengan migrasi sekali dari lokasi lama.
