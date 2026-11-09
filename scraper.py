import os
import time
import re
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

def parse_done_date(jadwal_text):
    # Mencari tanggal yang berlabel (Done) pada teks jadwal rencana
    matches = re.findall(r'(\d{1,2}\s+[A-Za-z]{3}\s+\(Done\))', jadwal_text)
    if matches:
        # Mengambil tanggal pertama yang sudah (Done)
        clean_date = matches[0].replace('(Done)', '').strip()
        return clean_date
    return ""

def clean_motor_name(raw_text):
    # Mengubah "Ganti Motor Waste Conveyor 5..." menjadi "Motor Waste Conveyor 5..."
    text = re.sub(r'^(ganti\s+motor\s*|cek\s+dan\s+dial\s+motor\s+pisau\s*-\s*ganti\s+motor\s+jika\s+ada\s+yang\s+jelek\s+nilainya\s*[:]?\s*)', '', raw_text, flags=re.IGNORECASE)
    # Membuang catatan tambahan di belakang seperti "& Trial", ", kasar", dll
    text = re.split(r'(&|,|\bTrial\b)', text)[0].strip()
    return text if text else raw_text

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
        
        print("4. Memproses dan memfilter baris data...")
        rows = driver.find_elements(By.XPATH, "//table//tbody/tr")
        
        processed_data = []
        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            col_data = [col.text.strip() for col in cols]
            
            if len(col_data) > 8:
                raw_job = col_data[1]
                personil = col_data[3]
                jadwal_teks = col_data[9] # Kolom I (Jadwal Rencana)
                
                # Hanya ambil data yang memiliki status (Done)
                tgl_terakhir = parse_done_date(jadwal_teks)
                if not tgl_terakhir:
                    continue # Lewati jika belum (Done)
                
                nama_motor = clean_motor_name(raw_job)
                keterangan = "" # Dikosongkan sesuai permintaan
                periode = "90"    # Default 90 hari
                
                # Hitung tanggal berkala selanjutnya (+90 hari)
                try:
                    # Parse tanggal format misal "03 Nov"
                    current_year = datetime.now().year
                    parsed_date = datetime.strptime(f"{tgl_terakhir} {current_year}", "%d %b %Y")
                    next_date_obj = parsed_date + timedelta(days=90)
                    tgl_selanjutnya = next_date_obj.strftime("%d %b %Y")
                except:
                    tgl_selanjutnya = ""
                
                # Susun urutan kolom: [Nama Motor, Tanggal Terakhir, Personil, Keterangan, Periode, Tanggal Selanjutnya]
                row_final = [nama_motor, tgl_terakhir, personil, keterangan, periode, tgl_selanjutnya]
                processed_data.append(row_final)
                
        print(f"-> Total data valid (Done) terkumpul: {len(processed_data)} baris.")
        
        if processed_data:
            print("5. Mengirim data rapi ke Google Sheets...")
            response = requests.post(APPS_SCRIPT_URL, json=processed_data)
            print("Respon server Google Sheets:", response.text)

    except Exception as e:
        print("\n[ERROR]:", str(e))
        
    finally:
        driver.quit()

if __name__ == "__main__":
    run_scraper()
