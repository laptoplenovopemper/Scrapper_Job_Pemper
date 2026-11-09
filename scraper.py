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

def parse_and_format_date(date_str):
    # Membersihkan dan mengubah berbagai format tanggal menjadi DD-MM-YY
    date_str = date_str.replace('(Done)', '').strip()
    
    # Coba berbagai kemungkinan format tanggal yang masuk
    formats = ["%d %b %Y", "%d %b", "%Y-%m-%d", "%d/%m/%Y"]
    parsed_date = None
    
    for fmt in formats:
        try:
            # Jika format tidak memiliki tahun, gunakan tahun saat ini
            if "%Y" not in fmt and "%y" not in fmt:
                temp_str = f"{date_str} {datetime.now().year}"
                parsed_date = datetime.strptime(temp_str, f"{fmt} %Y")
            else:
                parsed_date = datetime.strptime(date_str, fmt)
            break
        except:
            continue
            
    if parsed_date:
        return parsed_date.strftime("%d-%m-%y")
    return date_str

def clean_motor_name(raw_text):
    text = re.sub(r'^(ganti\s+motor\s*)', '', raw_text, flags=re.IGNORECASE)
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
                jadwal_teks = col_data[9]
                
                # ABAIKAN jika mengandung kata "dial motor"
                if "dial motor" in raw_job.lower():
                    continue
                
                # Ambil tanggal yang sudah (Done)
                matches = re.findall(r'(\d{1,2}\s+[A-Za-z]{3}\s+\(Done\))', jadwal_teks)
                if not matches:
                    continue
                
                raw_tgl = matches[0].replace('(Done)', '').strip()
                tgl_terakhir = parse_and_format_date(raw_tgl)
                
                nama_motor = clean_motor_name(raw_job)
                keterangan = "" 
                periode = "90"
                
                # Hitung Tanggal Berkala Selanjutnya (+90 hari) dan format DD-MM-YY
                try:
                    current_year = datetime.now().year
                    parsed_dt = datetime.strptime(f"{raw_tgl} {current_year}", "%d %b %Y")
                    next_dt = parsed_dt + timedelta(days=90)
                    tgl_selanjutnya = next_dt.strftime("%d-%m-%y")
                except:
                    tgl_selanjutnya = ""
                
                row_final = [nama_motor, tgl_terakhir, personil, keterangan, periode, tgl_selanjutnya]
                processed_data.append(row_final)
                
        print(f"-> Total data valid terkumpul: {len(processed_data)} baris.")
        
        if processed_data:
            print("5. Mengirim data bersih ke Google Sheets...")
            response = requests.post(APPS_SCRIPT_URL, json=processed_data)
            print("Respon server Google Sheets:", response.text)

    except Exception as e:
        print("\n[ERROR]:", str(e))
        
    finally:
        driver.quit()

if __name__ == "__main__":
    run_scraper()
