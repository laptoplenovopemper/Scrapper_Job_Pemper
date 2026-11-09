import os
import time
import requests
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service
from webdriver_manager.microsoft import EdgeChromiumDriverManager

LOGIN_URL = "http://job.pmp.web.id/login/" 

# Mengambil kredensial secara aman (dari GitHub Secrets atau fallback manual jika dijalankan lokal)
USERNAME = os.getenv("SCRAPER_USERNAME", "hanif")                     
PASSWORD = os.getenv("SCRAPER_PASSWORD", "#12345678#")              
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyaKVBoR7ictxN1pYu0LAiaHARvltJlwlqV1wDsoz96_enjB7pi6bqAWLkHx-JTEnrx/exec"

def run_scraper():
    print("1. Mempersiapkan browser otomatis...")
    options = webdriver.EdgeOptions()
    
    # Aktifkan baris di bawah ini jika ingin browser berjalan tersembunyi (tanpa muncul di layar)
    # options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    
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
        
        print("5. Menunggu dashboard termuat...")
        time.sleep(6) 
        
        print("6. Mengambil dan memfilter data tabel...")
        rows = driver.find_elements(By.XPATH, "//table//tbody/tr")
        
        filtered_data = []
        satu_bulan_lalu = datetime.now() - timedelta(days=30)
        
        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            col_data = [col.text.strip() for col in cols]
            
            if col_data:
                # Asumsi struktur kolom: [0] = Tanggal, [1] = Deskripsi Pekerjaan / Keterangan
                teks_pekerjaan = col_data[1].lower() if len(col_data) > 1 else col_data[0].lower()
                
                # Filter kata kunci "ganti motor"
                if "ganti motor" in teks_pekerjaan:
                    # Opsional: Validasi rentang waktu 1 bulan terakhir jika kolom tanggal tersedia
                    try:
                        # Sesuaikan format tanggal di web Anda (misal: 'YYYY-MM-DD' atau 'DD/MM/YYYY')
                        tgl_str = col_data[0]
                        tgl_job = datetime.strptime(tgl_str, "%Y-%m-%d") # Ubah format jika berbeda
                        if tgl_job >= satu_bulan_lalu:
                            filtered_data.append(col_data)
                    except:
                        # Jika kolom tanggal tidak cocok formatnya, tetap ambil data berdasarkan kata kunci
                        filtered_data.append(col_data)
                
        print(f"-> Total data cocok dengan filter 'Ganti Motor': {len(filtered_data)} baris.")
        
        if filtered_data:
            print("7. Mengirim data terfilter ke Google Sheets...")
            response = requests.post(APPS_SCRIPT_URL, json=filtered_data)
            print("Respon server Google Sheets:", response.text)
        else:
            print("Peringatan: Tidak ada data yang cocok dengan kriteria filter.")

    except Exception as e:
        print("\n[TERJADI ERROR PADA SKRIP]:")
        print(str(e))
        
    finally:
        print("Selesai. Menutup browser...")
        driver.quit()

if __name__ == "__main__":
    run_scraper()
