import os
import time
import requests
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Rentang waktu 1 bulan terakhir hingga hari ini
date_to = datetime.now().strftime("%Y-%m-%d")
date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

LOGIN_URL = "http://job.pmp.web.id/login/"
DASHBOARD_URL = f"http://job.pmp.web.id/?date_from={date_from}&date_to={date_to}&pic=&line=&mesin=&sub_mesin=&departemen=&bagian=&sub_bagian=&s="

USERNAME = os.getenv("SCRAPER_USERNAME")                     
PASSWORD = os.getenv("SCRAPER_PASSWORD")              
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyaKVBoR7ictxN1pYu0LAiaHARvltJlwlqV1wDsoz96_enjB7pi6bqAWLkHx-JTEnrx/exec"

def run_scraper():
    print("1. Menyiapkan browser Chrome otomatis (Headless)...")
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 10)
    
    try:
        print("2. Membuka halaman login...")
        driver.get(LOGIN_URL)
        time.sleep(2)
        
        print("3. Mengisi kredensial...")
        driver.find_element(By.ID, "id_username").send_keys(USERNAME)
        driver.find_element(By.ID, "id_password").send_keys(PASSWORD)
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        
        print(f"4. Mengakses data rentang tanggal: {date_from} s.d {date_to}...")
        driver.get(DASHBOARD_URL)
        time.sleep(4)
        
        all_filtered_data = []
        page_count = 1
        
        # 5. Perulangan halaman (Pagination) dengan filter ketat "ganti motor"
        while True:
            print(f"-> Memeriksa halaman {page_count}...")
            rows = driver.find_elements(By.XPATH, "//table//tbody/tr")
            
            for row in rows:
                cols = row.find_elements(By.TAG_NAME, "td")
                col_data = [col.text.strip() for col in cols]
                
                if col_data:
                    # Ambil teks pada kolom nama pekerjaan (biasanya indeks ke-1)
                    teks_pekerjaan = col_data[1].lower() if len(col_data) > 1 else col_data[0].lower()
                    
                    # FILTER KETAT: Hanya ambil baris yang mengandung kata "ganti motor"
                    if "ganti motor" in teks_pekerjaan:
                        if col_data not in all_filtered_data:
                            all_filtered_data.append(col_data)
            
            # Cek tombol "Selanjutnya" untuk halaman berikutnya
            try:
                next_btn = driver.find_element(By.XPATH, "//a[contains(text(), 'Selanjutnya') or contains(text(), 'Next')]")
                if "disabled" in next_btn.get_attribute("class") or not next_btn.is_displayed():
                    break
                next_btn.click()
                time.sleep(3)
                page_count += 1
            except:
                break
                
        print(f"-> Total data valid dengan filter 'Ganti Motor': {len(all_filtered_data)} baris.")
        
        if all_filtered_data:
            print("6. Mengirim data terfilter ke Google Sheets...")
            response = requests.post(APPS_SCRIPT_URL, json=all_filtered_data)
            print("Respon server Google Sheets:", response.text)
        else:
            print("Peringatan: Tidak ada data yang cocok dengan kata kunci 'Ganti Motor'.")

    except Exception as e:
        print("\n[TERJADI ERROR PADA SKRIP]:", str(e))
        
    finally:
        driver.quit()

if __name__ == "__main__":
    run_scraper()
