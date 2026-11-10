import os
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# 1. PENANGANAN INPUT TANGGAL YANG AMAN
date_from_input = os.environ.get("INPUT_DATE_FROM", "").strip()
date_to_input = os.environ.get("INPUT_DATE_TO", "").strip()

if date_from_input and date_to_input:
    # Konversi dari YYYY-MM-DD (Web App) ke DD/MM/YYYY (Target Web PMP)
    dt_from = datetime.strptime(date_from_input, "%Y-%m-%d")
    dt_to = datetime.strptime(date_to_input, "%Y-%m-%d")
    
    START_DATE = dt_from.strftime("%d/%m/%Y")
    END_DATE = dt_to.strftime("%d/%m/%Y")
    print(f"=== Menggunakan Tanggal Kustom dari Web App: {START_DATE} s/d {END_DATE} ===")
else:
    # Default jika dijalankan via schedule/cron (30 hari terakhir)
    now = datetime.now()
    month_ago = now - timedelta(days=30)
    START_DATE = month_ago.strftime("%d/%m/%Y")
    END_DATE = now.strftime("%d/%m/%Y")
    print(f"=== Menggunakan Tanggal Default (30 Hari Terakhir): {START_DATE} s/d {END_DATE} ===")

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
        # Buka URL Web PMP
        driver.get("https://job.pmp.web.id/")
        
        # -------------------------------------------------------------
        # ISIKAN SELENIUM DENGAN ELEMEN ASLI WEB PMP ANDA DI SINI
        # -------------------------------------------------------------
        # Contoh Pengisian Filter Tanggal di Web PMP:
        # date_from_el = driver.find_element(By.NAME, "date_from")
        # date_from_el.clear()
        # date_from_el.send_keys(START_DATE)
        
        # date_to_el = driver.find_element(By.NAME, "date_to")
        # date_to_el.clear()
        # date_to_el.send_keys(END_DATE)
        
        # driver.find_element(By.XPATH, "//button[@type='submit']").click()
        # -------------------------------------------------------------
        
        # Contoh ekstraksi baris tabel dari web PMP:
        # rows = driver.find_elements(By.XPATH, "//table/tbody/tr")
        # for row in rows:
        #     cols = [c.text for c in row.find_elements(By.TAG_NAME, "td")]
        #     scraped_data.append(cols)
            
        print(f"Scraping selesai! Ditemukan {len(scraped_data)} data.")
        driver.quit()
        return scraped_data

    except Exception as e:
        print(f"Error scraping: {str(e)}")
        driver.quit()
        return []

def save_to_google_sheets(data):
    if not data:
        print("Tidak ada data untuk disimpan ke Google Sheets.")
        return

    # Hubungkan ke Google Sheets melalui gspread / Google Apps Script API Anda
    print("Menyimpan data ke Google Sheets...")
    # ... taruh logika gspread / API simpan ke Google Sheets di sini ...

if __name__ == "__main__":
    hasil = run_scraper()
    save_to_google_sheets(hasil)
