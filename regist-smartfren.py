import pandas as pd
import time
import sys
import csv
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


FILE_EXCEL = 'dagangan.xlsx'
FILE_LAPORAN = 'laporan_registrasi_smartfren.csv'
KOLOM_WAJIB = {'No_HP', 'PUK', 'NIK', 'KK'}
URL_AKTIVASI = 'https://www.smartfren.com/activation'
STATUS_BERHASIL = 'berhasil'
STATUS_NOMOR_BERMASALAH = 'nomor_bermasalah'
STATUS_PUK_BERMASALAH = 'puk_bermasalah'
STATUS_NIK_BERMASALAH = 'nik_kk_bermasalah'
STATUS_TIDAK_DIKENALI = 'tidak_dikenali'


def ambil_text(row, nama_kolom):
    nilai = row[nama_kolom]
    if pd.isna(nilai):
        return ''
    return str(nilai).strip()


def normalisasi_no_hp(no_hp):
    no_hp = str(no_hp).strip()
    if no_hp and not no_hp.startswith('0'):
        no_hp = '0' + no_hp
    return no_hp


def buat_data_kartu(dataframe):
    kartu = []
    sudah_ada = set()

    for _, row in dataframe.iterrows():
        no_hp = normalisasi_no_hp(ambil_text(row, 'No_HP'))
        puk = ambil_text(row, 'PUK')
        if not no_hp or not puk:
            continue

        key = (no_hp, puk)
        if key in sudah_ada:
            continue

        kartu.append({'No_HP': no_hp, 'PUK': puk})
        sudah_ada.add(key)

    return kartu


def buat_data_identitas(dataframe):
    identitas = []
    sudah_ada = set()

    for _, row in dataframe.iterrows():
        nik = ambil_text(row, 'NIK')
        kk = ambil_text(row, 'KK')
        if not nik or not kk:
            continue

        key = (nik, kk)
        if key in sudah_ada:
            continue

        identitas.append({'NIK': nik, 'KK': kk})
        sudah_ada.add(key)

    return identitas


def potong_teks(teks, panjang=500):
    teks = " ".join(str(teks).split())
    if len(teks) <= panjang:
        return teks
    return teks[:panjang] + "..."


def buat_laporan_kosong():
    return {
        'percobaan': [],
        'nomor_berhasil': [],
        'nik_kk_tidak_bisa': [],
        'nomor_gagal': [],
    }


def alasan_singkat(status, pesan):
    pesan_lower = str(pesan).lower()

    if status == STATUS_BERHASIL:
        if 'aktif' in pesan_lower:
            return 'Nomor sudah aktif'
        return 'Nomor berhasil/sudah terdaftar'
    if status == STATUS_PUK_BERMASALAH:
        return 'PUK salah/tidak valid'
    if status == STATUS_NOMOR_BERMASALAH:
        return 'Nomor/server Smartfren bermasalah'
    if status == STATUS_NIK_BERMASALAH:
        if '3' in pesan_lower and 'nik' in pesan_lower:
            return 'NIK limit/penuh'
        if 'kartu keluarga' in pesan_lower or 'kk' in pesan_lower:
            return 'KK bermasalah/tidak sesuai'
        return 'NIK/KK bermasalah'
    return 'Status tidak dikenali'


def status_nik_dari_laporan(nik, rows_berhasil, rows_identitas_gagal):
    nik_berhasil = [row for row in rows_berhasil if row['NIK'] == nik]
    nik_gagal = [row for row in rows_identitas_gagal if row['NIK'] == nik]

    for row in nik_gagal:
        pesan_lower = str(row['Pesan']).lower()
        if '3' in pesan_lower and 'nik' in pesan_lower:
            return 'LIMIT/PENUH - jangan dipakai lagi', 'NIK sudah terdaftar di batas maksimal'

    if nik_gagal:
        return 'BERMASALAH', alasan_singkat(nik_gagal[-1]['Status'], nik_gagal[-1]['Pesan'])
    if nik_berhasil:
        return 'MASIH BISA DIPAKAI', f"Terbukti berhasil di {len(nik_berhasil)} nomor"
    return 'BELUM ADA HASIL FINAL', 'Belum ada sukses/gagal identitas'


def simpan_laporan(laporan):
    rows_berhasil = laporan['nomor_berhasil']
    rows_identitas_gagal = laporan['nik_kk_tidak_bisa']
    rows_gagal = laporan['nomor_gagal'] + rows_identitas_gagal

    semua_nik = {}
    for row in laporan['percobaan']:
        key = (row['NIK'], row['KK'])
        semua_nik[key] = row

    with open(FILE_LAPORAN, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile)

        writer.writerow(['BAGIAN 1 - NOMOR YANG BERHASIL'])
        writer.writerow(['No_HP', 'PUK', 'NIK', 'KK', 'Status', 'Alasan Singkat'])
        for row in rows_berhasil:
            writer.writerow([
                row['No_HP'],
                row['PUK'],
                row['NIK'],
                row['KK'],
                row['Status'],
                alasan_singkat(row['Status'], row['Pesan']),
            ])

        writer.writerow([])
        writer.writerow(['BAGIAN 2 - NOMOR YANG GAGAL / PERCOBAAN GAGAL'])
        writer.writerow(['No_HP', 'PUK', 'NIK', 'KK', 'Status', 'Alasan Singkat'])
        for row in rows_gagal:
            writer.writerow([
                row['No_HP'],
                row['PUK'],
                row['NIK'],
                row['KK'],
                row['Status'],
                alasan_singkat(row['Status'], row['Pesan']),
            ])

        writer.writerow([])
        writer.writerow(['BAGIAN 3 - CATATAN STATUS NIK'])
        writer.writerow(['NIK', 'KK', 'Status NIK', 'Catatan'])
        for (nik, kk), _ in semua_nik.items():
            status_nik, catatan = status_nik_dari_laporan(nik, rows_berhasil, rows_identitas_gagal)
            writer.writerow([nik, kk, status_nik, catatan])


def catat_laporan(laporan, kategori, no_hp, puk, nik, kk, status, aksi, pesan):
    data = {
        'Waktu': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'No_HP': no_hp,
        'PUK': puk,
        'NIK': nik,
        'KK': kk,
        'Status': status,
        'Aksi': aksi,
        'Pesan': potong_teks(pesan),
    }

    laporan['percobaan'].append(data)
    if kategori == 'berhasil':
        laporan['nomor_berhasil'].append(data)
    elif kategori == 'nik_kk_tidak_bisa':
        laporan['nik_kk_tidak_bisa'].append(data)
    elif kategori == 'nomor_gagal':
        laporan['nomor_gagal'].append(data)


def isi_input(wait, by, selector, nilai):
    input_element = wait.until(EC.element_to_be_clickable((by, selector)))
    driver = input_element.parent
    driver.execute_script(
        """
        const el = arguments[0];
        const value = arguments[1];
        const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        setter.call(el, value);
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
        """,
        input_element,
        nilai,
    )

    nilai_terisi = input_element.get_attribute("value")
    if nilai_terisi != nilai:
        raise ValueError(f"Input {selector} terisi '{nilai_terisi}', seharusnya '{nilai}'")

    return input_element


def klik_tombol_teks(driver, teks, timeout=20):
    xpath = f"//button[contains(normalize-space(.), '{teks}')]"
    try:
        tombol = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((By.XPATH, xpath)))
    except TimeoutException:
        tombol = None
        batas_waktu = time.time() + timeout
        while time.time() < batas_waktu:
            for kandidat in driver.find_elements(By.CSS_SELECTOR, "button"):
                if teks.lower() in kandidat.text.strip().lower():
                    tombol = kandidat
                    break
            if tombol:
                break
            time.sleep(0.5)

        if not tombol:
            raise

    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", tombol)
    time.sleep(0.3)
    try:
        tombol.click()
    except Exception:
        driver.execute_script("arguments[0].click();", tombol)
    return tombol


def tampilkan_debug_halaman(driver):
    print(f"   URL sekarang: {driver.current_url}")
    print(f"   Judul halaman: {driver.title}")
    body_text = driver.find_element(By.TAG_NAME, "body").text.strip()
    if body_text:
        print("   Teks halaman:")
        print("   " + body_text[:1000].replace("\n", "\n   "))

    inputs = driver.find_elements(By.CSS_SELECTOR, "input, textarea, select")
    if inputs:
        print("   Input yang terdeteksi:")
        for input_element in inputs:
            print(
                "   - "
                f"type={input_element.get_attribute('type')!r}, "
                f"name={input_element.get_attribute('name')!r}, "
                f"id={input_element.get_attribute('id')!r}, "
                f"placeholder={input_element.get_attribute('placeholder')!r}, "
                f"value={input_element.get_attribute('value')!r}"
            )

    buttons = driver.find_elements(By.CSS_SELECTOR, "button")
    if buttons:
        print("   Tombol yang terdeteksi:")
        for button in buttons:
            teks = button.text.strip().replace("\n", " | ")
            print(f"   - text={teks!r}, disabled={button.get_attribute('disabled')!r}")


def pastikan_tidak_ditolak_situs(driver):
    body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
    if "tidak dapat memproses permintaan" in body_text:
        raise RuntimeError("Smartfren sedang menolak request: tidak dapat memproses permintaan saat ini")


def deteksi_status_smartfren(teks_halaman):
    teks = teks_halaman.lower()

    nomor_sudah_aktif = (
        ("nomor" in teks or "nomer" in teks or "kartu" in teks or "sim" in teks)
        and ("sudah aktif" in teks or "telah aktif" in teks)
    )
    if nomor_sudah_aktif:
        return STATUS_BERHASIL

    if "tidak dapat memproses permintaan" in teks:
        return STATUS_NOMOR_BERMASALAH

    if "puk" in teks and (
        "salah" in teks
        or "tidak valid" in teks
        or "invalid" in teks
        or "gagal" in teks
        or "bermasalah" in teks
    ):
        return STATUS_PUK_BERMASALAH

    nik_maksimal = (
        "nik" in teks
        and ("sudah terdaftar" in teks or "telah terdaftar" in teks)
        and ("3" in teks or "tiga" in teks or "xlsmart" in teks)
    )
    if nik_maksimal:
        return STATUS_NIK_BERMASALAH

    if ("nik" in teks or "ktp" in teks or "kartu keluarga" in teks or "kk" in teks) and (
        "tidak valid" in teks
        or "tidak terdaftar" in teks
        or "tidak sesuai" in teks
        or "gagal" in teks
        or "bermasalah" in teks
    ):
        return STATUS_NIK_BERMASALAH

    if "berhasil" in teks or "selamat" in teks or "aktivasi selesai" in teks or "registrasi selesai" in teks:
        return STATUS_BERHASIL

    return STATUS_TIDAK_DIKENALI


def baca_status_halaman(driver):
    teks = driver.find_element(By.TAG_NAME, "body").text
    return deteksi_status_smartfren(teks), teks


def tunggu_hasil_smartfren(driver, timeout=30):
    batas_waktu = time.time() + timeout
    teks_terakhir = ""

    while time.time() < batas_waktu:
        status, teks_terakhir = baca_status_halaman(driver)
        if status != STATUS_TIDAK_DIKENALI:
            return status, teks_terakhir
        time.sleep(1)

    return STATUS_TIDAK_DIKENALI, teks_terakhir

# 1. Baca data dari Excel (Semua kolom dibaca sebagai TEXT murni)
try:
    df = pd.read_excel(FILE_EXCEL, dtype=str)
except Exception as e:
    print(f"❌ Eror: File '{FILE_EXCEL}' gak ketemu atau rusak! Detail: {e}")
    sys.exit(1)

kolom_hilang = KOLOM_WAJIB.difference(df.columns)
if kolom_hilang:
    print(f"❌ Eror: Kolom wajib belum ada di '{FILE_EXCEL}': {', '.join(sorted(kolom_hilang))}")
    sys.exit(1)

kartu_list = buat_data_kartu(df)
identitas_list = buat_data_identitas(df)

if not kartu_list:
    print(f"❌ Eror: Tidak ada data No_HP/PUK yang valid di '{FILE_EXCEL}'.")
    sys.exit(1)

if not identitas_list:
    print(f"❌ Eror: Tidak ada data NIK/KK yang valid di '{FILE_EXCEL}'.")
    sys.exit(1)

# 2. Setup Browser
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

print("\n=== START AUTOMATION REGISTRASI SMARTFREN ===")
print(f"Total kartu: {len(kartu_list)} | Total identitas: {len(identitas_list)}")
laporan = buat_laporan_kosong()
print(f"Laporan CSV akan dibuat setelah bot selesai: {FILE_LAPORAN}")

try:
    index_kartu = 0
    index_identitas = 0

    while index_kartu < len(kartu_list) and index_identitas < len(identitas_list):
        kartu = kartu_list[index_kartu]
        identitas = identitas_list[index_identitas]
        no_hp = kartu['No_HP']
        puk = kartu['PUK']
        nik = identitas['NIK']
        kk = identitas['KK']

        print(
            f"\n[Kartu {index_kartu + 1}/{len(kartu_list)} | "
            f"NIK {index_identitas + 1}/{len(identitas_list)}] "
            f"Memproses Nomor Smartfren: {no_hp} dengan NIK: {nik}"
        )
    
        try:
            wait = WebDriverWait(driver, 20)

            # ---------------------------------------------------------
            # STEP 1: Masuk ke Web Aktivasi Smartfren
            # ---------------------------------------------------------
            print("-> Membuka halaman aktivasi Smartfren...")
            driver.get(URL_AKTIVASI)
            
            # Tunggu sampai kolom Nomor Smartfren muncul
            wait.until(EC.element_to_be_clickable((By.XPATH, "//input[contains(@placeholder, 'Nomor Smartfren')]")))
            time.sleep(1)
            
            print(f"-> Mengisi Nomor Smartfren: {no_hp}")
            isi_input(wait, By.XPATH, "//input[contains(@placeholder, 'Nomor Smartfren')]", no_hp)
            
            # Klik Lanjutkan untuk masuk ke halaman OTP, lalu pilih metode Kode PUK.
            klik_tombol_teks(driver, "Lanjutkan", timeout=30)
            time.sleep(5)
            pastikan_tidak_ditolak_situs(driver)

            status_awal, teks_awal = baca_status_halaman(driver)
            if status_awal == STATUS_BERHASIL:
                aksi = "Nomor sudah aktif/berhasil, lanjut nomor berikutnya dengan NIK/KK yang sama"
                print(f"✅ {aksi}.")
                catat_laporan(laporan, 'berhasil', no_hp, puk, nik, kk, status_awal, aksi, teks_awal)
                index_kartu += 1
                time.sleep(2)
                continue
            if status_awal == STATUS_NOMOR_BERMASALAH:
                aksi = "Nomor bermasalah, lanjut nomor berikutnya dengan NIK/KK yang sama"
                print(f"-> {aksi}.")
                catat_laporan(laporan, 'nomor_gagal', no_hp, puk, nik, kk, status_awal, aksi, teks_awal)
                index_kartu += 1
                time.sleep(2)
                continue

            # ---------------------------------------------------------
            # STEP 2: Pilih metode Kode PUK, lalu input PUK.
            # ---------------------------------------------------------
            print("-> Memilih metode Kode PUK...")
            klik_tombol_teks(driver, "Kode PUK", timeout=30)

            print("-> Menunggu kolom PUK siap...")
            wait.until(EC.element_to_be_clickable((By.XPATH, "//input[contains(@placeholder, 'Nomor PUK')]")))
            
            print(f"-> Mengisi Nomor PUK otomatis: {puk}")
            isi_input(wait, By.XPATH, "//input[contains(@placeholder, 'Nomor PUK')]", puk)
            
            # Klik Lanjutkan Verifikasi PUK
            klik_tombol_teks(driver, "Lanjutkan", timeout=30)
            
            # Kasih jeda tunggu status "Nomor PUK telah terverifikasi" muncul dan hilang
            time.sleep(4)

            # ---------------------------------------------------------
            # STEP 3: Isi Informasi Identitas (Sesuai Menit 0:20 di video lo)
            # ---------------------------------------------------------
            print("-> Menunggu form Identitas (NIK/KTP) terbuka...")
            wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//input[contains(@placeholder, 'Nomor KTP') or contains(@placeholder, 'NIK')]")
                )
            )
            
            print(f"-> Mengisi Nomor NIK/KTP otomatis: {nik}")
            isi_input(wait, By.XPATH, "//input[contains(@placeholder, 'Nomor KTP') or contains(@placeholder, 'NIK')]", nik)
            
            # Centang Syarat & Ketentuan Smartfren
            checkbox_sk = driver.find_element(By.XPATH, "//input[@type='checkbox']")
            driver.execute_script("arguments[0].click();", checkbox_sk)
            
            # Klik Register NIK
            klik_tombol_teks(driver, "Register", timeout=30)
            time.sleep(3)

            status_setelah_nik, teks_setelah_nik = baca_status_halaman(driver)
            if status_setelah_nik == STATUS_NIK_BERMASALAH:
                aksi = "NIK/KK bermasalah, nomor yang sama dicoba dengan NIK/KK berikutnya"
                print(f"-> {aksi}.")
                catat_laporan(laporan, 'nik_kk_tidak_bisa', no_hp, puk, nik, kk, status_setelah_nik, aksi, teks_setelah_nik)
                index_identitas += 1
                time.sleep(2)
                continue

            # ---------------------------------------------------------
            # STEP 4: Input Nomor Kartu Keluarga (Sesuai Menit 0:27 di video lo)
            # ---------------------------------------------------------
            print("-> Menunggu pop-up atau kolom KK muncul...")
            # Klik button 'Mengerti' jika ada notifikasi awal pas foto selfie
            try:
                btn_mengerti = driver.find_element(By.XPATH, "//button[contains(text(), 'Mengerti')]")
                btn_mengerti.click()
                time.sleep(1)
            except Exception:
                pass

            # Halaman liveness sekarang menampilkan pilihan selfie atau KK.
            # Pilih jalur KK dulu supaya kolom Nomor Kartu Keluarga muncul.
            print("-> Memilih metode Masukkan Nomor Kartu Keluarga...")
            klik_tombol_teks(driver, "Masukkan Nomor Kartu Keluarga", timeout=40)
            time.sleep(2)

            status_setelah_metode_kk, teks_setelah_metode_kk = baca_status_halaman(driver)
            if status_setelah_metode_kk == STATUS_NIK_BERMASALAH:
                aksi = "NIK/KK bermasalah, nomor yang sama dicoba dengan NIK/KK berikutnya"
                print(f"-> {aksi}.")
                catat_laporan(
                    laporan,
                    'nik_kk_tidak_bisa',
                    no_hp,
                    puk,
                    nik,
                    kk,
                    status_setelah_metode_kk,
                    aksi,
                    teks_setelah_metode_kk,
                )
                index_identitas += 1
                time.sleep(2)
                continue
                
            wait.until(EC.element_to_be_clickable((By.XPATH, "//input[contains(@placeholder, 'Nomor Kartu Keluarga') or contains(@placeholder, 'KK')]")))
            
            print(f"-> Mengisi Nomor KK otomatis: {kk}")
            isi_input(wait, By.XPATH, "//input[contains(@placeholder, 'Nomor Kartu Keluarga') or contains(@placeholder, 'KK')]", kk)
            
            # Klik Lanjutkan Final untuk submit KK
            klik_tombol_teks(driver, "Lanjutkan", timeout=30)

            print("-> Menunggu hasil akhir Smartfren...")
            status_akhir, teks_akhir = tunggu_hasil_smartfren(driver, timeout=30)
            print(f"-> Status terdeteksi: {status_akhir}")
            print(f"-> Pesan situs: {potong_teks(teks_akhir)}")

            if status_akhir == STATUS_BERHASIL:
                aksi = "Nomor berhasil diregistrasi, lanjut nomor berikutnya dengan NIK/KK yang sama"
                print(f"✅ {aksi}.")
                catat_laporan(laporan, 'berhasil', no_hp, puk, nik, kk, status_akhir, aksi, teks_akhir)
                index_kartu += 1
            elif status_akhir == STATUS_NIK_BERMASALAH:
                aksi = "NIK/KK bermasalah, nomor yang sama dicoba dengan NIK/KK berikutnya"
                print(f"-> {aksi}.")
                catat_laporan(laporan, 'nik_kk_tidak_bisa', no_hp, puk, nik, kk, status_akhir, aksi, teks_akhir)
                index_identitas += 1
            else:
                aksi = "Nomor/PUK/status bermasalah, lanjut nomor berikutnya dengan NIK/KK yang sama"
                print(f"-> {aksi}.")
                catat_laporan(laporan, 'nomor_gagal', no_hp, puk, nik, kk, status_akhir, aksi, teks_akhir)
                index_kartu += 1

            time.sleep(5)
        
        except Exception as err:
            print(f"❌ Terjadi kendala saat memproses nomor {no_hp}: {err}")
            tampilkan_debug_halaman(driver)
            status_error, teks_error = baca_status_halaman(driver)
            if status_error == STATUS_NIK_BERMASALAH:
                kategori = 'nik_kk_tidak_bisa'
                aksi = "NIK/KK bermasalah, nomor yang sama dicoba dengan NIK/KK berikutnya"
                index_identitas += 1
            else:
                kategori = 'nomor_gagal'
                aksi = "Nomor/PUK/error bermasalah, lanjut nomor berikutnya dengan NIK/KK yang sama"
                index_kartu += 1
            catat_laporan(laporan, kategori, no_hp, puk, nik, kk, status_error, aksi, teks_error or str(err))
            time.sleep(2)

    if index_kartu >= len(kartu_list):
        print("\n✅ Semua kartu/nomor Smartfren sudah diproses.")
    elif index_identitas >= len(identitas_list):
        print("\n⚠️  Data NIK/KK sudah habis, masih ada nomor Smartfren yang belum selesai.")
finally:
    simpan_laporan(laporan)
    print(f"Laporan CSV sudah dibuat: {FILE_LAPORAN}")
    print("\n=== SEMUA DATA EXCEL SELESAI DIPROSES ===")
    driver.quit()
