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

# Mengatur rentang waktu otomatis 1 bulan terakhir hingga hari ini
date_to = datetime.now().strftime("%Y-%m-%d")
date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

# URL dengan filter tanggal otomatis 1 bulan
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
        
        print(f"4. Mengakses data dengan rentang tanggal: {date_from} s.d {date_to}...")
        driver.get(DASHBOARD_URL)
        time.sleep(4)
        
        print("5. Memasukkan kata kunci pencarian 'Ganti Motor'...")
        try:
            # Mencari kolom search pada tabel Daily Jobs
            search_box = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='search' or contains(@placeholder, '')]")))
            # Alternatif: mencari input di dalam area Daily Jobs
            search_inputs = driver.find_elements(By.TAG_NAME, "input")
            for inp in search_inputs:
                if inp.get_attribute("type") == "text" or inp.get_attribute("type") == "search":
                    inp.clear()
                    inp.send_keys("Ganti Motor")
                    break
            time.sleep(3) # Menunggu hasil pencarian terfilter
        except Exception as e:
            print("Peringatan saat mengisi kolom search:", str(e))
        
        all_extracted_data = []
        page_count = 1
        
        # 6. Looping untuk mengambil data dari halaman aktif hingga halaman berikutnya (Pagination)
        while True:
            print(f"-> Mengambil data dari halaman {page_count}...")
            rows = driver.find_elements(By.XPATH, "//table//tbody/tr")
            
            for row in rows:
                cols = row.find_elements(By.TAG_NAME, "td")
                col_data = [col.text.strip() for col in cols]
                if col_data and col_data not in all_extracted_data:
                    all_extracted_data.append(col_data)
            
            # Cek apakah tombol "Selanjutnya" (Next) ada dan bisa diklik
            try:
                next_btn = driver.find_element(By.XPATH, "//a[contains(text(), 'Selanjutnya') or contains(text(), 'Next')]")
                # Jika tombol disabled atau tidak bisa diklik, hentikan perulangan
                if "disabled" in next_btn.get_attribute("class") or not next_btn.is_displayed():
                    break
                
                # Klik tombol halaman selanjutnya
                next_btn.click()
                time.sleep(3)
                page_count += 1
            except:
                # Jika tombol selanjutnya sudah tidak ditemukan, berarti sudah di halaman terakhir
                break
                
        print(f"-> Total keseluruhan data terkumpul: {len(all_extracted_data)} baris.")
        
        if all_extracted_data:
            print("7. Mengirim data ke Google Sheets...")
            response = requests.post(APPS_SCRIPT_URL, json=all_extracted_data)
            print("Respon server Google Sheets:", response.text)
        else:
            print("Peringatan: Tidak ada data yang ditemukan.")

    except Exception as e:
        print("\n[TERJADI ERROR PADA SKRIP]:")
        print(str(e))
        
    finally:
        print("Selesai. Menutup browser...")
        driver.quit()

if __name__ == "__main__":
    run_scraper()
