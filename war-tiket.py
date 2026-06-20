import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# URL Target Waiting Room Antrean BTS dari Tiket.com
URL_TARGET = "https://queue.tiket.com/?c=tiket&e=btsgosday333&ver=javascript-4.4.4&cver=405&man=%5BProduction%5D%20Waiting%20Room%20%281%29&t=https%3A%2F%2Fwww.tiket.com%2Fid-id%2Fto-do%2Fbts-jakarta-3rdshowday%3Futm_logic%3D0F140273D7D3AB3F4857FBBEC47FDC5A%26utm_section%3DpageModule%253B6a2645dbf8124c456408e7be&kupver=cloudflare-4.4.3"

print("\n=== START BOT WAR TIKET BTS ARIRANG ===")

# Menggunakan Undetected Chromedriver agar lolos sensor Cloudflare / Bot Detection
options = uc.ChromeOptions()
options.add_argument("--start-maximized")
options.add_argument("--disable-popup-blocking")

driver = uc.Chrome(options=options, version_main=149)

try:
    # 1. Buka Halaman Waiting Room Antrean
    print("-> Membuka halaman antrean tiket.com...")
    driver.get(URL_TARGET)
    
    # 2. Standby Menunggu Antrean Dibuka (Deteksi Otomatis Tanpa Delay)
    print("-> Bot standby di waiting room. Menunggu waktu perhitungan mundur habis...")
    
    # Set batas tunggu maksimal (misal 2 jam / 7200 detik) sampai tombol beli tiket muncul
    wait_long = WebDriverWait(driver, 7200)
    
    # Skenario A: Begitu antrean selesai, halaman otomatis redirect atau memunculkan elemen utama
    # Kita kunci elemen kontainer halaman pembelian tiket tiket.com setelah lolos antrean
    print("-> Siap menembak tombol tiket instan tanpa delay begitu masuk antrean utama...")
    
    # Ganti selektor di bawah ini dengan ID/Class tombol order tiket.com jika sudah masuk halaman produk
    # Contoh: Mencari tombol yang mengandung teks 'Pilih Tiket' atau 'Beli Sekarang'
    tombol_tiket = wait_long.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Pilih Tiket') or contains(text(), 'Beli')]")))
    
    # Klik instan tanpa delay!
    tombol_tiket.click()
    print("✅ Tombol tiket berhasil diklik dengan kecepatan tinggi!")
    
    # Jeda semi-otomatis untuk memilih kategori kursi secara manual demi keamanan akun lo
    input("\n⌨️ Silakan selesaikan pembayaran di browser Chrome lo, lalu tekan [ENTER] di sini untuk menutup bot...")

except Exception as e:
    print(f"❌ Terjadi kendala saat war tiket: {e}")

print("\n=== WAR SELESAI ===")
driver.quit()