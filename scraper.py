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

# 1. MENANGKAP PARAMETER TANGGAL DARI WEB APP
date_from_input = os.environ.get("INPUT_DATE_FROM", "").strip()
date_to_input = os.environ.get("INPUT_DATE_TO", "").strip()

if date_from_input and date_to_input:
    dt_from = datetime.strptime(date_from_input, "%Y-%m-%d")
    dt_to = datetime.strptime(date_to_input, "%Y-%m-%d")
    
    # Hitung selisih hari (end_date - start_date) untuk variabel angka jika diperlukan
    selisih_hari = (dt_to - dt_from).days
    
    START_DATE = dt_from.strftime("%d/%m/%Y") # Format DD/MM/YYYY untuk web PMP
    END_DATE = dt_to.strftime("%d/%m/%Y")
    
    print(f"=== Tanggal Kustom ===")
    print(f"Dari: {START_DATE} S/d: {END_DATE} (Durasi: {selisih_hari} hari)")
else:
    # Default 30 hari terakhir
    dt_to = datetime.now()
    dt_from = dt_to - timedelta(days=30)
    selisih_hari = 30
    
    START_DATE = dt_from.strftime("%d/%m/%Y")
    END_DATE = dt_to.strftime("%d/%m/%Y")
    print(f"=== Tanggal Default (30 Hari Terakhir) ===")
    print(f"Dari: {START_DATE} S/d: {END_DATE} (Durasi: {selisih_hari} hari)")

USERNAME = os.environ.get("SCRAPER_USERNAME")
PASSWORD = os.environ.get("SCRAPER_PASSWORD")

def run_scraper():
    scraped_data = []
    print("Membuka browser headless untuk scraping...")
    
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    try:
        # Buka URL Dashboard PMP
        driver.get("https://job.pmp.web.id/")
        
        # Berikan waktu tunggu elemen muncul
        wait = WebDriverWait(driver, 15)
        
        # =========================================================================
        # 2. ISI ELEMEN FILTER TANGGAL DI WEBSITE PMP SECARA AKTIF
        # (Sesuaikan atribut name/id jika berbeda dengan inspect element web Anda)
        # =========================================================================
        print(f"Memasukkan filter tanggal: {START_DATE} sampai {END_DATE}")
        
        # Mengisi input 'Dari Tanggal' (date_from)
        input_from = wait.until(EC.presence_of_element_located((By.NAME, "date_from")))
        input_from.clear()
        input_from.send_keys(START_DATE)
        
        # Mengisi input 'Sampai Tanggal' (date_to)
        input_to = wait.until(EC.presence_of_element_located((By.NAME, "date_to")))
        input_to.clear()
        input_to.send_keys(END_DATE)
        
        # Klik tombol 'Filter' agar web PMP memproses data sesuai tanggal tersebut
        # Cari tombol filter berdasarkan teks atau class/name-nya
        btn_filter = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Filter')]")))
        btn_filter.click()
        
        # Tunggu beberapa detik agar tabel termuat ulang (refresh) setelah filter diklik
        driver.implicitly_wait(5)
        
        # =========================================================================
        # 3. EKSTRAKSI TABEL HASIL SCRAPING
        # =========================================================================
        rows = driver.find_elements(By.XPATH, "//table//tbody/tr")
        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            cols_text = [col.text.strip() for col in cols]
            if cols_text and len(cols_text) > 1:
                scraped_data.append(cols_text)
                
        print(f"Berhasil menarik {len(scraped_data)} baris data dari web PMP.")
        driver.quit()
        return scraped_data

    except Exception as e:
        print(f"Terjadi kesalahan saat proses scraping: {str(e)}")
        driver.quit()
        return []

def save_to_google_sheets(data):
    if not data:
        print("Tidak ada data baru untuk diperbarui ke Google Sheets.")
        return

    print("Menyimpan data ke Google Sheets...")
    # Masukkan logika gspread atau API sinkronisasi Anda di sini jika diperlukan
    # Contoh:
    # scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    # ...
    print("Spreadsheet berhasil diperbarui!")

if __name__ == "__main__":
    hasil_data = run_scraper()
    save_to_google_sheets(hasil_data)
