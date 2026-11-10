import os
import time
import requests
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

LOGIN_URL = "http://job.pmp.web.id/login/" 
USERNAME = os.environ.get("SCRAPER_USERNAME", "hanif") # Bisa ambil dari Secrets GitHub atau fallback ke default
PASSWORD = os.environ.get("SCRAPER_PASSWORD", "#12345678#")
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyaKVBoR7ictxN1pYu0LAiaHARvltJlwlqV1wDsoz96_enjB7pi6bqAWLkHx-JTEnrx/exec"

# Menangkap parameter tanggal dari Web App (Format: YYYY-MM-DD)
date_from_input = os.environ.get("INPUT_DATE_FROM", "").strip()
date_to_input = os.environ.get("INPUT_DATE_TO", "").strip()

def run_scraper():
    options = Options()
    options.add_argument("--headless") # Wajib untuk server GitHub Actions
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    # Menggunakan Chrome karena menggunakan ubuntu-latest di GitHub Actions
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    try:
        print("Membuka halaman login...")
        driver.get(LOGIN_URL)
        time.sleep(3)
        
        # Proses login menggunakan elemen yang sama seperti script lokal Anda
        driver.find_element(By.ID, "id_username").send_keys(USERNAME)
        driver.find_element(By.ID, "id_password").send_keys(PASSWORD)
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        time.sleep(5) # Tunggu proses login selesai dan masuk dashboard
        
        # Jika ada parameter tanggal kustom dari Web App, langsung akses URL filternya setelah login
        if date_from_input and date_to_input:
            target_url = f"http://job.pmp.web.id/?date_from={date_from_input}&date_to={date_to_input}"
            print(f"Mengakses filter tanggal kustom: {target_url}")
            driver.get(target_url)
            time.sleep(4) # Tunggu tabel memperbarui data sesuai tanggal
            
        filtered_data = []
        
        # Ambil data dari tabel (bisa disesuaikan jika ingin melooping halaman lebih dari 1)
        rows = driver.find_elements(By.XPATH, "//table//tbody/tr")
        print(f"Ditemukan {len(rows)} baris pada halaman ini.")
        
        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            col_data = [col.text.strip() for col in cols]
            
            if col_data:
                teks_pekerjaan = col_data[1].lower() if len(col_data) > 1 else col_data[0].lower()
                if "ganti motor" in teks_pekerjaan:
                    filtered_data.append(col_data)
                
        if filtered_data:
            response = requests.post(APPS_SCRIPT_URL, json=filtered_data)
            print("Berhasil kirim data ke Google Sheets:", response.text)
        else:
            print("Tidak ada data 'ganti motor' yang ditemukan pada rentang ini.")

    except Exception as e:
        print("Error saat scraping:", str(e))
        
    finally:
        driver.quit()

if __name__ == "__main__":
    run_scraper()
