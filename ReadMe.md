<div align="center">

# Bot Registrasi Kartu SIM

<p>
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.12">
  <img src="https://img.shields.io/badge/Selenium-Automation-43B02A?style=for-the-badge&logo=selenium&logoColor=white" alt="Selenium">
  <img src="https://img.shields.io/badge/Excel-Input_Data-217346?style=for-the-badge&logo=microsoft-excel&logoColor=white" alt="Excel">
  <img src="https://img.shields.io/badge/Chrome-Browser-4285F4?style=for-the-badge&logo=googlechrome&logoColor=white" alt="Chrome">
</p>

Bot otomatisasi untuk membantu mengisi form registrasi kartu SIM dari data Excel menggunakan Selenium dan Google Chrome.

</div>

---

## Ringkasan

<table>
  <tr>
    <td><b>Operator</b></td>
    <td><b>Script</b></td>
    <td><b>Mode</b></td>
  </tr>
  <tr>
    <td><b>Axis / XL</b></td>
    <td><code>bot-regist.py</code></td>
    <td>Registrasi via PUK, dengan jeda manual untuk CAPTCHA</td>
  </tr>
  <tr>
    <td><b>Smartfren</b></td>
    <td><code>regist-smartfren.py</code></td>
    <td>Aktivasi kartu via nomor, PUK, NIK, dan KK</td>
  </tr>
</table>

> [!IMPORTANT]
> Gunakan bot ini hanya untuk nomor, NIK, KK, dan PUK yang sah serta memang berhak kamu proses.

---

## Kebutuhan

<table>
  <tr>
    <td><b>Python</b></td>
    <td>Python 3.12 atau versi kompatibel</td>
  </tr>
  <tr>
    <td><b>Browser</b></td>
    <td>Google Chrome</td>
  </tr>
  <tr>
    <td><b>Internet</b></td>
    <td>Koneksi stabil untuk membuka website operator dan mengunduh ChromeDriver</td>
  </tr>
  <tr>
    <td><b>Input</b></td>
    <td>File <code>dagangan.xlsx</code> di folder project</td>
  </tr>
</table>

Install dependency:

```bash
pip install pandas selenium webdriver-manager openpyxl
```

Jika memakai virtual environment yang sudah ada di folder ini:

```bash
source env/bin/activate
```

---

## Format Excel

Bot membaca file bernama `dagangan.xlsx`. Nama kolom harus sama persis seperti tabel berikut:

| Kolom | Keterangan | Contoh |
| --- | --- | --- |
| `No_HP` | Nomor kartu yang akan diregistrasi | `081234567890` |
| `PUK` | Kode PUK kartu | `12345678` |
| `NIK` | Nomor Induk Kependudukan | `3200000000000000` |
| `KK` | Nomor Kartu Keluarga | `3200000000000000` |

> [!NOTE]
> Semua data dibaca sebagai teks supaya angka panjang seperti NIK, KK, dan nomor HP tidak berubah format.

---

## Membuat Template Excel

Edit data contoh di file `create-excle.py`:

```python
list_hp = ["Number_Your_Phone"]
list_puk = ["Number_Your_PUK"]
list_nik = ["Number_Your_NIK"]
list_kk = ["Number_Your_KK"]
```

Lalu jalankan:

```bash
python create-excle.py
```

Output yang dibuat:

```text
dagangan.xlsx
```

> [!WARNING]
> Script `create-excle.py` akan membuat atau menimpa file `dagangan.xlsx`.

---

## Menjalankan Axis / XL

```bash
python bot-regist.py
```

Alur otomatisasi:

1. Membaca data dari `dagangan.xlsx`.
2. Membuka halaman `https://registrasi.xl.co.id/`.
3. Memilih `Non-Biometric Registration`.
4. Memilih registrasi menggunakan PUK.
5. Mengisi nomor HP, NIK, KK, dan PUK.
6. Mencentang persetujuan syarat dan ketentuan.
7. Membuka tahap CAPTCHA.

Saat CAPTCHA muncul, terminal akan menampilkan instruksi:

```text
Jika Captcha SUDAH selesai, klik di terminal ini lalu Tekan [ENTER]...
```

Selesaikan CAPTCHA di browser, kembali ke terminal, lalu tekan `ENTER`. Setelah itu bot akan klik tombol `Registrasi` dan membaca hasil dari halaman.

### Status Yang Dideteksi

| Status | Arti |
| --- | --- |
| `berhasil` | Registrasi berhasil |
| `kartu_terdaftar` | Nomor/kartu sudah terdaftar |
| `nik_tidak_terdaftar` | NIK tidak dikenali oleh sistem |
| `nik_maksimal` | NIK sudah mencapai batas maksimal |
| `tidak_dikenali` | Bot belum bisa membaca hasil halaman |

Jika NIK bermasalah, bot akan mencoba NIK berikutnya untuk nomor yang sama. Jika kartu berhasil atau sudah terdaftar, bot lanjut ke nomor berikutnya.

---

## Menjalankan Smartfren

```bash
python regist-smartfren.py
```

Alur otomatisasi:

1. Membaca data dari `dagangan.xlsx`.
2. Membuka halaman `https://www.smartfren.com/activation`.
3. Mengisi nomor Smartfren.
4. Memilih metode `Kode PUK`.
5. Mengisi PUK.
6. Mengisi NIK.
7. Mencentang syarat dan ketentuan.
8. Memilih metode `Masukkan Nomor Kartu Keluarga`.
9. Mengisi nomor KK.
10. Mengirim form registrasi.

Jika terjadi kendala, bot akan menampilkan debug halaman dan bertanya:

```text
Mau lanjut ke nomor berikutnya di Excel? (y/n):
```

Ketik `y` untuk lanjut ke nomor berikutnya, atau `n` untuk berhenti.

---

## Catatan Penting

> [!TIP]
> Jalankan command dari folder project supaya file `dagangan.xlsx` terbaca dengan benar.

- Jangan tutup browser Chrome selama bot berjalan.
- Jangan ubah nama file `dagangan.xlsx` kecuali konstanta `FILE_EXCEL` di script juga diubah.
- Pastikan nama kolom Excel sama persis: `No_HP`, `PUK`, `NIK`, `KK`.
- Jika nomor HP tidak diawali `0`, script akan menambahkan `0` otomatis.
- `webdriver-manager` akan mengunduh ChromeDriver yang sesuai saat bot dijalankan.
- Tampilan website operator dapat berubah kapan saja. Jika selector tombol/input berubah, script mungkin perlu disesuaikan.

---

## Troubleshooting

### File Excel Tidak Ditemukan

Pastikan `dagangan.xlsx` ada di folder yang sama dengan script:

```bash
cd /home/vrz1668/Desktop/bot-registrasi
python bot-regist.py
```

### Kolom Wajib Belum Ada

Pastikan file Excel punya empat kolom ini:

```text
No_HP, PUK, NIK, KK
```

### Browser Tidak Terbuka

Pastikan Google Chrome sudah terpasang dan dependency sudah di-install:

```bash
pip install pandas selenium webdriver-manager openpyxl
```

### Hasil Axis / XL Tidak Dikenali

Bot akan meminta pilihan manual:

```text
n = ganti NIK
k = ganti kartu
lainnya = berhenti
```

Pilih berdasarkan pesan yang tampil di halaman browser.

---

<div align="center">

<b>Dibuat untuk membantu proses input data lebih cepat, tetap dengan kontrol manual saat website membutuhkan verifikasi.</b>

</div>
