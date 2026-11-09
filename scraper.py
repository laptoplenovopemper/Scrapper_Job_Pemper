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
SEARCH_KEYWORD = "Ganti Motor"
DASHBOARD_URL = f"http://job.pmp.web.id/?date_from={date_from}&date_to={date_to}&pic=&line=&mesin=&sub_mesin=&departemen=&bagian=&sub_bagian=&search={SEARCH_KEYWORD.replace(' ', '+')}"

USERNAME = os.getenv("SCRAPER_USERNAME")                     
PASSWORD = os.getenv("SCRAPER_PASSWORD")              
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyaKVBoR7ictxN1pYu0LAiaHARvltJlwlqV1wDsoz96_enjB7pi6bqAWLkHx-JTEnrx/exec"

def run_scraper():
    print("1. Menyiapkan browser Chrome Headless...")
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
        
        print(f"3. Mengakses data pencarian '{SEARCH_KEYWORD}'...")
        driver.get(DASHBOARD_URL)
        time.sleep(5)
        
        print("4. Mengambil data baris tabel...")
        rows = driver.find_elements(By.XPATH, "//table//tbody/tr")
        
        extracted_data = []
        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            col_data = [col.text.strip() for col in cols]
            
            if len(col_data) > 1:
                # CEK & SKIP: Jangan masukkan baris jika itu adalah teks header bawaan website
                if "nama pekerjaan" in col_data[1].lower():
                    continue
                
                bersih_data = col_data[1:] # Membuang nomor urut tabel web
                extracted_data.append(bersih_data)
                
        print(f"-> Total data bersih: {len(extracted_data)} baris.")
        
        if extracted_data:
            print("5. Mengirim data ke Google Sheets...")
            response = requests.post(APPS_SCRIPT_URL, json=extracted_data)
            print("Respon server Google Sheets:", response.text)

    except Exception as e:
        print("\n[ERROR]:", str(e))
        
    finally:
        driver.quit()

if __name__ == "__main__":
    run_scraper()
