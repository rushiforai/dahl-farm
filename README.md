# 🚀 Dahl Global API Auto-Farm

Alat otomatisasi cerdas berkecepatan tinggi untuk menghasilkan dan mengelola API Key gratis dari **[Dahl Global](https://dahl.global)** secara massal, dilengkapi dengan filter proxy cerdas, rotasi Tor pool, dan integrasi otomatis ke **9Router**.

---

> [!IMPORTANT]
> **Membutuhkan Proxy agar Tidak Menghambat Proses Farm (Anti Rate-Limit 429)**
> Server Dahl Global membatasi pendaftaran akun per alamat IP (*HTTP 429 Too Many Requests*). Oleh karena itu, **penggunaan proxy (HTTP / SOCKS5) sangat diwajibkan** agar proses farming akun berjalan lancar, cepat, dan tidak terhambat oleh jeda cooldown IP.
>
> 💡 *Tidak punya proxy pribadi?* Anda tidak perlu mencari atau membeli proxy manual! Repository ini sudah dilengkapi **Auto-Scraper & Health Checker Proxy bawaan** (`filter_proxies.py` atau Menu `[2]` pada `run.bat`) yang otomatis mencari dan memvalidasi proxy publik aktif secara gratis.

---

## ✨ Fitur Utama

- 🤖 **Auto-Signup & Provisioning**: Otomatis membuat username acak, mendaftar akun, mengalokasikan saldo token gratis (*free token grant*) ke API key baru, dan memverifikasi kelayakan inferensi.
- 🎲 **Gacha Proxy Farm**: Memilih proxy hidup secara acak dari daftar yang terverifikasi untuk menghindari pembatasan IP (*Rate Limit HTTP 429*).
- 🔍 **Built-in Proxy Checker & Scraper**: Fitur auto-scrape dari berbagai repositori publik dan pengecekan latency secara paralel real-time.
- 🧅 **Tor Pool Multi-Instance**: Mendukung pembuatan cluster instans Tor lokal untuk rotasi identitas otomatis tanpa batas.
- 🔌 **Auto-Inject ke 9Router**: Otomatis memasukkan API key yang berhasil di-farm langsung ke database SQLite aplikasi [9Router](https://github.com/9router) tanpa perlu copy-paste manual satu per satu.
- 📁 **Manajemen Kredensial Terstruktur**: Menyimpan data akun (username, user ID, fingerprint login, API key) ke folder lokal secara rapi.

---

## 📋 Prasyarat Sistem

1. **Python 3.8 atau lebih baru**.
2. **Koneksi Internet**.
3. **Proxy (HTTP / SOCKS5)**: Diperlukan untuk rotasi IP agar farming tidak terhambat limit (bisa di-generate otomatis via fitur scraper bawaan).
4. *(Opsional)* Aplikasi **9Router** jika ingin memanfaatkan fitur auto-inject.
5. *(Opsional)* Binary **Tor** jika ingin menggunakan mode farm via Tor pool.

---

## 🛠️ Panduan Instalasi

1. **Clone repository ini:**
   ```bash
   git clone https://github.com/zidnifarchanramadhan-lang/dahl-farm.git
   cd dahl-farm
   ```

2. **Pasang dependensi Python yang dibutuhkan:**
   ```bash
   pip install -r requirements.txt
   ```

---

## 📖 Tutorial Penggunaan Lengkap

Terdapat dua cara mudah untuk menjalankan automasi ini:

### Cara 1: Menggunakan Menu Interaktif Windows (Paling Mudah)

Cukup klik dua kali file **`run.bat`** (atau ketik `run.bat` di terminal Command Prompt / PowerShell):

```
============================================================
     DAHL GLOBAL FARM (PASTI MENGGUNAKAN PROXY)
============================================================

 [1] Farm Akun (Wajib Pakai Proxy - Anti 429 dan Auto 9Router)
 [2] Filter / Cari Proxy Aktif Baru (filter_proxies.bat)
 [3] Inject Ulang Semua Key Tersimpan ke 9Router
 [4] Lihat Daftar Akun yang Sudah Terkumpul
 [5] Cek / Verifikasi Token API Key
 [0] Keluar

============================================================
Pilih menu [1-5, 0]:
```

#### Alur Penggunaan yang Disarankan:
1. **Langkah 1**: Pilih menu **`[2]`** terlebih dahulu untuk mencari proxy publik aktif yang lolos verifikasi Dahl Global. Script akan memeriksa proxy dan menyimpannya otomatis ke `proxies_good.txt`.
2. **Langkah 2**: Pilih menu **`[1]`** untuk mulai melakukan farming akun. Masukkan jumlah akun yang ingin dibuat (misal: `5` atau `10`). Script akan merotasi proxy dan menyuntikkan token yang berhasil ke 9Router.
3. **Langkah 3**: Pilih menu **`[4]`** untuk melihat rekapitulasi akun dan token yang sudah berhasil dikumpulkan.

---

### Cara 2: Menjalankan via Command Line (CLI)

Anda juga dapat menjalankan perintah langsung melalui terminal:

#### 1. Memfilter & Mencari Proxy Aktif
Mencari 20 proxy hidup dan siap pakai:
```bash
python filter_proxies.py 20
```
> *Catatan:* Jika belum ada file proxy lokal, script akan otomatis mengunduh ribuan proxy gratis dari internet dan mengetesnya satu per satu dengan multi-threading (80 worker paralel).

#### 2. Menjalankan Gacha Proxy Farm (Disarankan)
Membuat 10 akun dengan rotasi acak dari `proxies_good.txt` dan auto-inject ke 9Router:
```bash
python dahl_farm.py gachafarm 10
```

Jika tidak ingin auto-inject ke 9Router, tambahkan flag `--no-inject`:
```bash
python dahl_farm.py gachafarm 10 --no-inject
```

#### 3. Farm Menggunakan Proxy Tunggal atau File Kustom
```bash
# Menggunakan satu proxy tertentu:
python dahl_farm.py proxyfarm 5 --proxy socks5://127.0.0.1:1080

# Menggunakan daftar file proxy kustom:
python dahl_farm.py proxyfarm 10 --file daftar_proxy_saya.txt
```

#### 4. Mode Sequential (Standar Tanpa Proxy)
```bash
python dahl_farm.py farm 5 --delay 45
```
*(Gunakan delay secukupnya agar IP internet Anda tidak terkena rate limit)*

#### 5. Menginjeksi Token Tersimpan ke 9Router
Untuk memasukkan semua token yang sudah pernah di-farm sebelumnya ke 9Router:
```bash
python dahl_farm.py inject9
```

#### 6. Menampilkan Akun dan Uji API Key
```bash
# Menampilkan semua akun yang sudah terkumpul di folder creds/
python dahl_farm.py list

# Menguji apakah sebuah API Key masih aktif dan merespon
python dahl_farm.py check dahl_YOUR_API_KEY_HERE
```

---

## ⚙️ Integrasi 9Router & Konfigurasi Path

Script secara default otomatis mendeteksi database lokal 9Router di lokasi standar:
- **Windows**: `%APPDATA%\9router\db\data.sqlite` (`C:\Users\YOUR_USERNAME\AppData\Roaming\9router\db\data.sqlite`)
- **Linux / macOS**: `~/.9router/db/data.sqlite`

### Mengatur Path Kustom (Opsional):
Jika Anda menginstal 9Router di lokasi non-standar, Anda dapat menyetel environment variable:
```bash
# PowerShell:
$env:YOUR_9ROUTER_DB_PATH="D:\custom_path\9router\db\data.sqlite"

# Command Prompt (cmd):
set YOUR_9ROUTER_DB_PATH=D:\custom_path\9router\db\data.sqlite

# Linux/macOS:
export YOUR_9ROUTER_DB_PATH=/path/to/your/9router/db/data.sqlite
```

---

## 📂 Struktur Direktori Proyek

```
dahl-farm/
├── dahl_farm.py           # Core script automasi pendaftaran, API allocation, dan 9Router injection
├── filter_proxies.py      # Multi-threaded proxy scraper & health checker
├── filter_proxies.bat     # Shortcut bat untuk memfilter proxy di Windows
├── run.bat                # Menu konsol interaktif utama (All-in-One CLI UI)
├── farm.bat               # Shortcut cepat untuk menjalankan proses farming
├── requirements.txt       # Daftar dependensi Python (httpx, socksio)
├── proxies.example.txt    # Contoh template format proxy yang didukung
├── keys.example.txt       # Template format penyimpanan API key
├── .env.example           # Contoh konfigurasi environment variable
├── .gitignore             # Menjaga kerahasiaan kredensial dan cache lokal
└── creds/                 # (Lokal) Folder penyimpanan kredensial akun hasil farm (tidak di-upload)
```

---

## 🔒 Catatan Keamanan & Privasi

> [!WARNING]
> Folder `creds/` dan file `keys.txt` berisi *fingerprint* autentikasi dan token API aktif Anda. **Jangan pernah mengunggah atau membagikan isi folder tersebut ke publik.** 
> File-file ini telah otomatis dikecualikan pada file `.gitignore`.

---

## ⚖️ Disclaimer

Proyek ini dibuat untuk tujuan edukasi dan riset interoperabilitas API. Pengguna bertanggung jawab penuh atas penggunaan script ini sesuai dengan ketentuan layanan (*Terms of Service*) penyedia terkait.
