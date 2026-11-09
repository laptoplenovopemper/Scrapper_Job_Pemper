import os
import time
import requests
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

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
    
    try:
        print("2. Membuka halaman login...")
        driver.get(LOGIN_URL)
        time.sleep(2)
        
        driver.find_element(By.ID, "id_username").send_keys(USERNAME)
        driver.find_element(By.ID, "id_password").send_keys(PASSWORD)
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        
        print(f"3. Mengakses data rentang tanggal: {date_from} s.d {date_to}...")
        driver.get(DASHBOARD_URL)
        time.sleep(4)
        
        all_filtered_data = []
        page_count = 1
        
        while True:
            print(f"-> Memeriksa halaman {page_count}...")
            rows = driver.find_elements(By.XPATH, "//table//tbody/tr")
            
            for row in rows:
                cols = row.find_elements(By.TAG_NAME, "td")
                col_data = [col.text.strip() for col in cols]
                
                # Pastikan baris memiliki data tabel yang valid (mengabaikan baris kosong)
                if len(col_data) > 1:
                    # Ambil teks nama pekerjaan (biasanya berada di indeks ke-1 setelah kolom 'No')
                    teks_pekerjaan = col_data[1].lower()
                    
                    # Filter ketat kata kunci "ganti motor"
                    if "ganti motor" in teks_pekerjaan:
                        # Hilangkan kolom 'No' (indeks 0) agar data masuk ke Sheet mulai dari Nama Pekerjaan
                         bersih_data = col_data[1:] 
                        if bersih_data not in all_filtered_data:
                            all_filtered_data.append(bersih_data)
            
            # Cek tombol "Selanjutnya" untuk pagination
            try:
                next_btn = driver.find_element(By.XPATH, "//a[contains(text(), 'Selanjutnya') or contains(text(), 'Next')]")
                parent_li = next_btn.find_element(By.XPATH, "./ancestor::li")
                
                if "disabled" in parent_li.get_attribute("class") or not next_btn.is_displayed():
                    break
                
                next_btn.click()
                time.sleep(3)
                page_count += 1
            except:
                break
                
        print(f"-> Total data valid terkumpul: {len(all_filtered_data)} baris.")
        
        if all_filtered_data:
            print("4. Mengirim data ke Google Sheets...")
            response = requests.post(APPS_SCRIPT_URL, json=all_filtered_data)
            print("Respon server Google Sheets:", response.text)
        else:
            print("Peringatan: Tidak ada data yang cocok.")

    except Exception as e:
        print("\n[TERJADI ERROR]:", str(e))
        
    finally:
        driver.quit()

if __name__ == "__main__":
    run_scraper()
