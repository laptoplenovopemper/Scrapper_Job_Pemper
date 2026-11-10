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

# 1. MENANGKAP PARAMETER TANGGAL LANGSUNG DALAM FORMAT YYYY-MM-DD
date_from_input = os.environ.get("INPUT_DATE_FROM", "").strip()
date_to_input = os.environ.get("INPUT_DATE_TO", "").strip()

if date_from_input and date_to_input:
    START_DATE = date_from_input # Format sudah YYYY-MM-DD dari Web App
    END_DATE = date_to_input
    print(f"=== Menggunakan Tanggal Kustom: {START_DATE} s/d {END_DATE} ===")
else:
    # Default 30 hari terakhir jika dijalankan otomatis
    END_DATE = datetime.now().strftime("%Y-%m-%d")
    START_DATE = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    print(f"=== Menggunakan Tanggal Default: {START_DATE} s/d {END_DATE} ===")

USERNAME = os.environ.get("SCRAPER_USERNAME")
PASSWORD = os.environ.get("SCRAPER_PASSWORD")

def run_scraper():
    scraped_data = []
    print("Membuka browser headless...")
    
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    try:
        # 2. LANGSUNG AKSES URL DENGAN PARAMETER QUERY TANGGAL
        target_url = f"https://job.pmp.web.id/?date_from={START_DATE}&date_to={END_DATE}"
        print(f"Mengakses URL Target: {target_url}")
        driver.get(target_url)
        
        # Beri waktu halaman memuat data
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.XPATH, "//table//tbody/tr")))
        
        # 3. CONTOH EKSTRAKSI TABEL (Menarik baris data dari halaman yang tampil)
        rows = driver.find_elements(By.XPATH, "//table//tbody/tr")
        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            cols_text = [col.text.strip() for col in cols]
            if cols_text and len(cols_text) > 1:
                scraped_data.append(cols_text)
                
        print(f"Berhasil mengambil {len(scraped_data)} baris data.")
        driver.quit()
        return scraped_data

    except Exception as e:
        print(f"Terjadi kesalahan saat scraping: {str(e)}")
        driver.quit()
        return []

def save_to_google_sheets(data):
    if not data:
        print("Tidak ada data untuk disimpan ke Google Sheets.")
        return

    print("Menyimpan data ke Google Sheets...")
    # Masukkan kredensial dan logika gspread untuk menulis ke Google Sheets di sini
    # Contoh:
    # scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    # credentials = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    # gc = gspread.authorize(credentials)
    # sheet = gc.open_by_key("1TJHsAW2_xdunVovqQ2yOwNfKyaXsutyHdOx7A9Cw4gs").sheet1
    # sheet.clear() # Bersihkan data lama
    # sheet.append_rows(data)
    print("Data berhasil disimpan!")

if __name__ == "__main__":
    hasil_data = run_scraper()
    save_to_google_sheets(hasil_data)
