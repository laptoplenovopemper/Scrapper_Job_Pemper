import os
import time
import requests
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

LOGIN_URL = "http://job.pmp.web.id/login/" 

# Mengambil kredensial dari GitHub Secrets secara aman
USERNAME = os.getenv("SCRAPER_USERNAME")                     
PASSWORD = os.getenv("SCRAPER_PASSWORD")              
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyaKVBoR7ictxN1pYu0LAiaHARvltJlwlqV1wDsoz96_enjB7pi6bqAWLkHx-JTEnrx/exec"

def run_scraper():
    print("1. Menyiapkan browser Chrome otomatis (Headless)...")
    options = webdriver.ChromeOptions()
    
    # Argumen wajib agar bisa berjalan di server cloud GitHub Actions
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    try:
        print("2. Membuka halaman login...")
        driver.get(LOGIN_URL)
        time.sleep(3)
        
        print("3. Mengisi username dan password...")
        driver.find_element(By.ID, "id_username").send_keys(USERNAME)
        driver.find_element(By.ID, "id_password").send_keys(PASSWORD)
        
        print("4. Mengklik tombol login...")
        login_btn = driver.find_element(By.XPATH, "//button[@type='submit']")
        login_btn.click()
        
        print("5. Menunggu dashboard termuat...")
        time.sleep(6) 
        
        print("6. Mengambil dan memfilter data tabel (Kata kunci: 'Ganti Motor')...")
        rows = driver.find_elements(By.XPATH, "//table//tbody/tr")
        
        filtered_data = []
        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            col_data = [col.text.strip() for col in cols]
            
            if col_data:
                # Mengambil teks pekerjaan untuk dicek kata kuncinya
                teks_pekerjaan = col_data[1].lower() if len(col_data) > 1 else col_data[0].lower()
                
                # Filter kata kunci "ganti motor"
                if "ganti motor" in teks_pekerjaan:
                    filtered_data.append(col_data)
                
        print(f"-> Total data cocok dengan filter: {len(filtered_data)} baris.")
        
        if filtered_data:
            print("7. Mengirim data ke Google Sheets...")
            response = requests.post(APPS_SCRIPT_URL, json=filtered_data)
            print("Respon server Google Sheets:", response.text)
        else:
            print("Peringatan: Tidak ada data dengan kata kunci 'Ganti Motor'.")

    except Exception as e:
        print("\n[TERJADI ERROR PADA SKRIP]:")
        print(str(e))
        
    finally:
        print("Selesai. Menutup browser...")
        driver.quit()

if __name__ == "__main__":
    run_scraper()
