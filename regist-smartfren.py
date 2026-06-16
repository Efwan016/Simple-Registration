import pandas as pd
import time
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


FILE_EXCEL = 'dagangan.xlsx'
KOLOM_WAJIB = {'No_HP', 'PUK', 'NIK', 'KK'}
URL_AKTIVASI = 'https://www.smartfren.com/activation'


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

# 2. Setup Browser
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

print("\n=== START AUTOMATION REGISTRASI SMARTFREN ===")

for index, row in df.iterrows():
    # Validasi jika kolom No_HP kosong
    if pd.isna(row['No_HP']) or str(row['No_HP']).strip() == '':
        continue

    # Ambil data murni dari baris excel lo
    no_hp = normalisasi_no_hp(ambil_text(row, 'No_HP'))
    nik = ambil_text(row, 'NIK')
    kk = ambil_text(row, 'KK')
    puk = ambil_text(row, 'PUK')

    if not all([no_hp, nik, kk, puk]):
        print(f"⚠️  Baris {index + 1} dilewati karena ada data kosong.")
        continue

    print(f"\n[{index+1}/{len(df)}] Memproses Nomor Smartfren: {no_hp}")
    
    try:
        wait = WebDriverWait(driver, 20)

        # ---------------------------------------------------------
        # STEP 1: Masuk ke Web Aktivasi Smartfren
        # ---------------------------------------------------------
        print("-> Membuka halaman aktivasi Smartfren...")
        driver.get(URL_AKTIVASI)
        
        # Tunggu sampai kolom Nomor Smartfren muncul
        input_smartfren = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[contains(@placeholder, 'Nomor Smartfren')]")))
        time.sleep(1)
        
        print(f"-> Mengisi Nomor Smartfren: {no_hp}")
        isi_input(wait, By.XPATH, "//input[contains(@placeholder, 'Nomor Smartfren')]", no_hp)
        
        # Klik Lanjutkan untuk masuk ke halaman OTP, lalu pilih metode Kode PUK.
        klik_tombol_teks(driver, "Lanjutkan", timeout=30)
        time.sleep(5)
        pastikan_tidak_ditolak_situs(driver)

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

        # ---------------------------------------------------------
        # STEP 4: Input Nomor Kartu Keluarga (Sesuai Menit 0:27 di video lo)
        # ---------------------------------------------------------
        print("-> Menunggu pop-up atau kolom KK muncul...")
        # Klik button 'Mengerti' jika ada notifikasi awal pas foto selfie
        try:
            btn_mengerti = driver.find_element(By.XPATH, "//button[contains(text(), 'Mengerti')]")
            btn_mengerti.click()
            time.sleep(1)
        except:
            pass

        # Halaman liveness sekarang menampilkan pilihan selfie atau KK.
        # Pilih jalur KK dulu supaya kolom Nomor Kartu Keluarga muncul.
        print("-> Memilih metode Masukkan Nomor Kartu Keluarga...")
        klik_tombol_teks(driver, "Masukkan Nomor Kartu Keluarga", timeout=40)
        time.sleep(2)
            
        wait.until(EC.element_to_be_clickable((By.XPATH, "//input[contains(@placeholder, 'Nomor Kartu Keluarga') or contains(@placeholder, 'KK')]")))
        
        print(f"-> Mengisi Nomor KK otomatis: {kk}")
        isi_input(wait, By.XPATH, "//input[contains(@placeholder, 'Nomor Kartu Keluarga') or contains(@placeholder, 'KK')]", kk)
        
        # Klik Lanjutkan Final untuk submit KK
        klik_tombol_teks(driver, "Lanjutkan", timeout=30)
        
        print(f"✅ Nomor {no_hp} Berhasil Diregistrasi di Smartfren!")
        time.sleep(7) # Jeda melihat halaman "Registrasi Berhasil" sebelum lanjut ke baris excel berikutnya
        
    except Exception as err:
        print(f"❌ Terjadi kendala saat memproses nomor {no_hp}: {err}")
        tampilkan_debug_halaman(driver)
        pilihan = input("Mau lanjut ke nomor berikutnya di Excel? (y/n): ")
        if pilihan.lower() != 'y':
            break

print("\n=== SEMUA DATA EXCEL SELESAI DIPROSES ===")
driver.quit()
