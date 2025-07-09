# AERORA - Servo Control System

**AERORA - Servo Control System** adalah sistem kontrol servo berbasis Python yang memungkinkan pengujian, monitoring, dan analisis gerakan motor **Dynamixel** (XL-320 dan XM-430) menggunakan dua pendekatan:

- ✅ **Non-GroupSync Write**
- ✅ **GroupSync Write**

Proyek ini dilengkapi GUI berbasis `CustomTkinter` serta fitur logging, pengambilan data performa sistem, pemulihan komunikasi, dan analisis hasil gerakan dari file `.csv`.

---

## 📁 Struktur Direktori

AERORA/
├── main.py # Entry point GUI utama
├── Aerora.py # Modul fungsi pendukung (baca file, port, dsb)
├── motion/ # Folder berisi file CSV gerakan servo
├── data/ # Folder hasil data logging otomatis
├── requirements.txt # Daftar dependensi
└── README.md # Dokumentasi

---

## 🚀 Fitur Utama

- 🔌 Koneksi ke servo via port serial
- 🧠 Deteksi servo aktif secara dinamis dari file CSV
- 📊 Logging waktu tulis/baca, error, CPU, dan RAM
- 🔁 Recovery komunikasi otomatis saat gagal tulis/baca
- 🧪 Analisis hasil `GroupSync` vs `NonGroup` melalui file CSV
- 🖥️ GUI ramah pengguna dengan `CustomTkinter`

---

## 📌 Versi

| Versi  | Tanggal Rilis  | Deskripsi Singkat                               |
|--------|----------------|-------------------------------------------------|
| v1.0.0 | 9 Juli 2025    | Rilis awal: GUI + Group vs NonGroup             |
| v1.0.0 | 9 Juli 2025    | Update: Memperbarui README dan requirements.txt |

---

## 🚀 Cara Menjalankan

### 1. Install Python v 3.10
Disarankan menggunakan Python versi 3.10.x karena lebih stabil dan kompatibel dengan semua dependensi.

- Kunjungi https://www.python.org/downloads/release/python-31011/
- Windows installer (64-bit): https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe 
- MacOS: 
```bash
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    brew install python@3.10
```
- Linux:
```bash
    sudo apt update
    sudo apt install python3.10 python3.10-venv python3.10-dev
```
- wpython-3.10.11-amd64.exe

### 2. Instalasi Python (Windows)
Jalankan file installer
    - ✅ Centang Add Python 3.10 to PATH
    - Klik Customize installation

Pada halaman berikutnya, aktifkan semua opsi
    - ✅ Centang juga:
    - "Install for all users"
    - "Add Python to environment variables"
    - Klik Install

### 3. Clone Repository
```bash
    git clone https://github.com/Pandu28r/aerora-servo-control.git
    cd aerora-servo-control
```

### 4. Buat dan Aktifkan Virtual Environment
Setelah Python 3.10 terpasang:
- Windows:
```bash
    python -m venv venv
    venv\Scripts\activate
```
- MacOS:
```bash
    python3.10 -m venv venv
    source venv/bin/activate
```
- Linux:
```bash
    python3.10 -m venv venv
    source venv/bin/activate
```

### 5. **Instalasi Dependency**
Gunakan virtual environment, lalu install:

```bash
    pip install -r requirements.txt
```

### 6. **Format File CSV Input (Motion)**
Pastikan file motion disimpan di folder motion/. Perhatikan juga
format filenya (contoh ada di motion/example.csv)

### 7. **Jalankan Program**
Windows:
```bash
    python main.py
```
Linux / MacOS:
```bash
    python3 main.py
```

### 8. **Cara memakai GUI**

**Lakukan Koneksi Port**
| Sistem Operasi | Contoh Port            | Keterangan                          |
| -------------- | ---------------------- | ----------------------------------- |
| Windows        | `COM3`, `COM6`         | Gunakan port COM yang terdeteksi    |
| Linux          | `/dev/ttyUSB0`         | Umumnya berbasis USB-UART converter |
| macOS          | `/dev/tty.usbserial-*` | Perangkat berbasis FTDI/serial      |

**Masukkan Nama File CSV**
Isikan nama file (tanpa .csv) pada kolom input (misal: angkat_tangan)

**Jalankan Gerakan**
Pilih metode:
NonGroup: Menulis dan membaca ke setiap servo secara individual
GroupSync: Menulis dan membaca semua servo secara paralel (lebih cepat)

Tombol kontrol:
⏸ Pause gerakan
▶ Continue dari posisi pause
⏹ Stop gerakan dan reset ulang

### 9. **Hasil Logging**
Hasil Logging
Setelah gerakan dijalankan, file hasil akan otomatis disimpan di folder data/.

Format nama file:
groupsync_namafile_27servo_20250708_093100.csv
nongroup_namafile_27servo_20250708_093205.csv

### 10. **Melakukan Analisis**
Pastikan sudah menjalankan kedua metode (Group dan NonGroup)
- Klik tombol Analisis
- Akan muncul jendela:
    - Hasil Group
    - Hasil NonGroup
    - Interpretasi perbandingan

**Catatan Penting**
- Jangan jalankan gerakan tanpa koneksi servo aktif.
- Pastikan file CSV valid dan sesuai struktur.
- CSV hasil gerakan bisa digunakan untuk laporan atau peneliti

---

## 📘 Hak Cipta & Penggunaan

Proyek ini merupakan bagian dari penelitian _SYNTA 3 - Bantuan Inovasi Mahasiswa Universitas Negeri Malang oleh:

**Myrza Pandu Pamungkas**  
Universitas Negeri Malang – Teknik Informatika

Seluruh kode dan dokumentasi pada repositori ini hanya digunakan sebagai pelengkap penelitian.  
Tidak diperkenankan untuk digunakan, disalin, dimodifikasi, atau disebarluaskan tanpa izin tertulis dari pemilik.

© 2025 Myrza Pandu Pamungkas. All rights reserved.