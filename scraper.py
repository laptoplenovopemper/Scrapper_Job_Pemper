import os
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 1. Menangkap Parameter Tanggal dari Web App
date_from_input = os.environ.get("INPUT_DATE_FROM", "").strip()
date_to_input = os.environ.get("INPUT_DATE_TO", "").strip()

if date_from_input and date_to_input:
    START_DATE = date_from_input
    END_DATE = date_to_input
    print(f"=== Menggunakan Tanggal Kustom: {START_DATE} s/d {END_DATE} ===")
else:
    END_DATE = datetime.now().strftime("%Y-%m-%d")
    START_DATE = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    print(f"=== Menggunakan Tanggal Default: {START_DATE} s/d {END_DATE} ===")

def run_scraper():
    scraped_data = []
    print("Membuka browser headless...")
    
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    try:
        target_url = f"https://job.pmp.web.id/?date_from={START_DATE}&date_to={END_DATE}"
        print(f"Mengakses URL Target: {target_url}")
        driver.get(target_url)
        
        # 2. GUNAKAN EXPLICIT WAIT YANG KUAT (Menunggu tabel benar-benar muncul di DOM)
        wait = WebDriverWait(driver, 20)
        
        # Coba tunggu sampai elemen baris tabel pertama muncul (maksimal 20 detik)
        try:
            wait.until(EC.presence_of_element_located((By.XPATH, "//table//tbody/tr")))
            print("Tabel berhasil dimuat oleh browser!")
        except Exception as e:
            print("Peringatan: Tabel tidak kunjung muncul atau kosong pada rentang tanggal ini.")
            driver.save_screenshot("debug_error.png") # Menyimpan screenshot untuk dianalisis jika gagal
            
        # 3. CONTOH EKSTRAKSI DATA DARI TABEL
        rows = driver.find_elements(By.XPATH, "//table//tbody/tr")
        print(f"Ditemukan {len(rows)} baris pada halaman ini.")
        
        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            cols_text = [col.text.strip() for col in cols]
            # Pastikan baris valid dan bukan baris 'Tidak ada data'
            if cols_text and len(cols_text) > 1 and "Tidak ada" not in cols_text[0]:
                scraped_data.append(cols_text)
                
        print(f"Total data terkumpul sementara: {len(scraped_data)}")
        driver.quit()
        return scraped_data

    except Exception as e:
        print(f"Terjadi kesalahan fatal saat scraping: {str(e)}")
        driver.save_screenshot("debug_tampilan.png")
        driver.quit()
        return []

def save_to_google_sheets(data):
    if not data:
        print("Tidak ada data untuk disimpan ke Google Sheets.")
        return

    print("Menyimpan data ke Google Sheets...")
    # Masukkan logika gspread Anda di sini jika sudah siap
    print("Selesai!")

if __name__ == "__main__":
    hasil_data = run_scraper()
    save_to_google_sheets(hasil_data)
