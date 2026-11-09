import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service
from webdriver_manager.microsoft import EdgeChromiumDriverManager

LOGIN_URL = "http://job.pmp.web.id/login/" 
USERNAME = "hanif"                     
PASSWORD = "#12345678#"              
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyaKVBoR7ictxN1pYu0LAiaHARvltJlwlqV1wDsoz96_enjB7pi6bqAWLkHx-JTEnrx/exec"

def run_scraper():
    print("1. Mempersiapkan browser Microsoft Edge otomatis...")
    options = webdriver.EdgeOptions()
    
    # Menggunakan Edge WebDriver Manager
    driver = webdriver.Edge(service=Service(EdgeChromiumDriverManager().install()), options=options)
    
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
        
        print("5. Berhasil klik login! Menunggu dashboard termuat (6 detik)...")
        time.sleep(6) 
        
        print("6. Mencari tabel data pekerjaan...")
        rows = driver.find_elements(By.XPATH, "//table//tbody/tr")
        print(f"-> Jumlah baris tabel ditemukan: {len(rows)}")
        
        extracted_data = []
        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            col_data = [col.text.strip() for col in cols]
            if col_data:
                extracted_data.append(col_data)
                
        if extracted_data:
            print("7. Mengirim data ke Google Sheets...")
            response = requests.post(APPS_SCRIPT_URL, json=extracted_data)
            print("Respon server Google Sheets:", response.text)
        else:
            print("Peringatan: Tabel data kosong atau tidak terbaca.")

    except Exception as e:
        print("\n[TERJADI ERROR PADA SKRIP]:")
        print(str(e))
        
    finally:
        print("Selesai. Menutup browser dalam 10 detik...")
        time.sleep(10)
        driver.quit()

if __name__ == "__main__":
    run_scraper()