import pandas as pd
import time
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


FILE_EXCEL = 'dagangan.xlsx'
KOLOM_WAJIB = {'No_HP', 'PUK', 'NIK', 'KK'}
URL_REGISTRASI = 'https://registrasi.xl.co.id/'
PESAN_NIK_TIDAK_TERDAFTAR = "nik_tidak_terdaftar"
PESAN_NIK_MAKSIMAL = "nik_maksimal"
PESAN_KARTU_TERDAFTAR = "kartu_terdaftar"
PESAN_BERHASIL = "berhasil"
PESAN_TIDAK_DIKENALI = "tidak_dikenali"


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


def buka_form_puk(driver, wait):
    driver.get(URL_REGISTRASI)

    print("-> Memilih Non-Biometric Registration...")
    tombol_non_biometric = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Non-Biometric Registration')]"))
    )
    tombol_non_biometric.click()

    print("-> Memilih registrasi Menggunakan PUK...")
    tombol_puk = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Menggunakan PUK')]")))
    tombol_puk.click()

    print("-> Form PUK sudah terbuka, menunggu kolom nomor muncul...")
    wait.until(EC.presence_of_element_located((By.NAME, "nomor_hp")))


def tampilkan_debug_halaman(driver):
    print(f"   URL sekarang: {driver.current_url}")
    print(f"   Judul halaman: {driver.title}")
    body_text = driver.find_element(By.TAG_NAME, "body").text.strip()
    if body_text:
        print("   Teks halaman:")
        print("   " + body_text[:800].replace("\n", "\n   "))

    inputs = driver.find_elements(By.CSS_SELECTOR, "input, textarea, select")
    if inputs:
        print("   Input yang terdeteksi:")
        for input_element in inputs:
            print(
                "   - "
                f"type={input_element.get_attribute('type')!r}, "
                f"name={input_element.get_attribute('name')!r}, "
                f"id={input_element.get_attribute('id')!r}, "
                f"placeholder={input_element.get_attribute('placeholder')!r}"
            )

    buttons = driver.find_elements(By.CSS_SELECTOR, "button")
    if buttons:
        print("   Tombol yang terdeteksi:")
        for button in buttons:
            teks = button.text.strip().replace("\n", " | ")
            print(
                "   - "
                f"text={teks!r}, "
                f"disabled={button.get_attribute('disabled')!r}"
            )


def klik_tombol_teks(driver, wait, daftar_teks, timeout=20):
    xpath_teks = " or ".join([f"contains(normalize-space(.), '{teks}')" for teks in daftar_teks])
    xpath = f"//button[{xpath_teks}]"

    tombol = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((By.XPATH, xpath)))
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", tombol)
    time.sleep(0.3)
    try:
        tombol.click()
    except Exception:
        driver.execute_script("arguments[0].click();", tombol)

    return tombol


def potong_teks(teks, panjang=1000):
    teks = " ".join(teks.split())
    if len(teks) <= panjang:
        return teks
    return teks[:panjang] + "..."


def deteksi_hasil_registrasi(teks_halaman):
    teks = teks_halaman.lower()

    if "nik tidak terdaftar" in teks:
        return PESAN_NIK_TIDAK_TERDAFTAR

    nik_maksimal = (
        "nik" in teks
        and ("sudah terdaftar" in teks or "telah terdaftar" in teks)
        and ("3" in teks or "tiga" in teks or "max" in teks or "maks" in teks)
    )
    if nik_maksimal:
        return PESAN_NIK_MAKSIMAL

    kartu_terdaftar = (
        ("kartu" in teks or "nomor" in teks or "msisdn" in teks)
        and ("sudah terdaftar" in teks or "telah terdaftar" in teks)
    )
    if kartu_terdaftar:
        return PESAN_KARTU_TERDAFTAR

    if "berhasil" in teks and ("registrasi" in teks or "terdaftar" in teks):
        return PESAN_BERHASIL

    return PESAN_TIDAK_DIKENALI


def tunggu_hasil_registrasi(driver, timeout=30):
    batas_waktu = time.time() + timeout
    teks_terakhir = ""

    while time.time() < batas_waktu:
        teks_terakhir = driver.find_element(By.TAG_NAME, "body").text
        hasil = deteksi_hasil_registrasi(teks_terakhir)
        if hasil != PESAN_TIDAK_DIKENALI:
            return hasil, teks_terakhir
        time.sleep(1)

    return PESAN_TIDAK_DIKENALI, teks_terakhir

# 1. Baca data dari Excel dengan memaksa semua kolom dibaca sebagai TEXT murni
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

print("\n=== START AUTOMATION REGISTRASI AXIS/XL ===")
print(f"Total kartu: {len(kartu_list)} | Total identitas: {len(identitas_list)}")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

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
            f"Memproses Nomor: {no_hp} dengan NIK: {nik}"
        )
        
        try:
            wait = WebDriverWait(driver, 15)
            buka_form_puk(driver, wait)
            
            time.sleep(2) # Jeda sedetik biar form stabil
            
            print("-> Mengetik data kartu otomatis menggunakan atribut NAME (Anti-Geser)...")
            
            # 1. Kolom Nomor HP
            isi_input(wait, By.NAME, "nomor_hp", no_hp)
            
            # 2. Mengisi NIK
            isi_input(wait, By.NAME, "nomor_nik", nik)
            
            # 3. Mengisi Nomor KK
            isi_input(wait, By.NAME, "nomor_kk", kk)
            
            # 4. Mengisi Nomor PUK
            isi_input(wait, By.NAME, "nomor_puk", puk)
            
            # Otomatis Centang Kotak Persetujuan S&K
            print("-> Mencentang persetujuan Syarat & Ketentuan...")
            checkbox_sk = wait.until(EC.element_to_be_clickable((By.ID, "termsAccepted")))
            driver.execute_script("arguments[0].click();", checkbox_sk)
            
            print("✅ Data sukses terisi otomatis!")

            # Klik tombol "Lanjutkan" dulu untuk lanjut ke tahap CAPTCHA.
            print("-> Mengklik tombol Lanjutkan untuk membuka CAPTCHA...")
            klik_tombol_teks(driver, wait, ["Lanjutkan"], timeout=60)
            
            # SEMI-OTOMATIS (JEDA CAPTCHA)
            print("\n👉 SILAKAN LIHAT LAYAR BROWSER CHROME LO!")
            print("👉 Bereskan CAPTCHA / Verifikasi Gambar secara manual jika ada.")
            print("⚠️  JANGAN klik tombol 'Registrasi' di web, biar bot yang klik.")
            
            input("\n⌨️  Jika Captcha SUDAH selesai, klik di terminal ini lalu Tekan [ENTER]...")
            
            # Klik tombol final "Registrasi" setelah CAPTCHA selesai.
            print("-> Mengklik tombol Registrasi...")
            klik_tombol_teks(driver, wait, ["Registrasi"], timeout=60)

            print("-> Menunggu hasil registrasi...")
            hasil, teks_hasil = tunggu_hasil_registrasi(driver, timeout=30)
            print(f"-> Hasil terdeteksi: {hasil}")
            print(f"-> Pesan situs: {potong_teks(teks_hasil)}")

            if hasil in (PESAN_NIK_TIDAK_TERDAFTAR, PESAN_NIK_MAKSIMAL):
                print("-> NIK diganti, nomor yang sama akan dicoba ulang.")
                index_identitas += 1
            elif hasil in (PESAN_KARTU_TERDAFTAR, PESAN_BERHASIL):
                print("-> Nomor diganti, NIK yang sama tetap dipakai.")
                index_kartu += 1
            else:
                pilihan = input(
                    "Hasil belum dikenali. Ketik 'n' untuk ganti NIK, "
                    "'k' untuk ganti kartu, atau lainnya untuk berhenti: "
                ).strip().lower()
                if pilihan == 'n':
                    index_identitas += 1
                elif pilihan == 'k':
                    index_kartu += 1
                else:
                    break

            time.sleep(5)
            
        except Exception as err:
            print(f"❌ Terjadi kendala saat memproses nomor {no_hp}: {err}")
            tampilkan_debug_halaman(driver)
            pilihan = input(
                "Ketik 'n' untuk ulang nomor ini dengan NIK berikutnya, "
                "'k' untuk lanjut kartu berikutnya, atau lainnya untuk berhenti: "
            ).strip().lower()
            if pilihan == 'n':
                index_identitas += 1
            elif pilihan == 'k':
                index_kartu += 1
            else:
                break

    if index_kartu >= len(kartu_list):
        print("\n✅ Semua kartu/nomor sudah diproses.")
    elif index_identitas >= len(identitas_list):
        print("\n⚠️  Data NIK/KK sudah habis, masih ada nomor yang belum selesai.")
finally:
    print("\n=== SEMUA DATA EXCEL SELESAI DIPROSES ===")
    driver.quit()
