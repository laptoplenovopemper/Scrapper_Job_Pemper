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

def universal_date_converter(date_str):
    """
    Fungsi konverter universal: Menerima segala jenis format tanggal mentah,
    lalu menyeragamkannya menjadi format DD-MM-YY secara konsisten.
    """
    # Bersihkan dari teks status
    clean_str = re.sub(r'\((Done|Open)\)', '', date_str).strip()
    current_year = datetime.now().year
    
    # Daftar berbagai variasi format tanggal yang mungkin muncul dari web
    formats = [
        "%d %b %Y", "%d %b %y", "%d %B %Y", "%d %B", "%d %b", 
        "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d-%m-%y"
    ]
    
    parsed_date = None
    for fmt in formats:
        try:
            if "%Y" not in fmt and "%y" not in fmt:
                # Jika format tidak memiliki tahun, pasangkan dengan tahun aktif
                parsed_date = datetime.strptime(f"{clean_str} {current_year}", f"{fmt} %Y")
            else:
                parsed_date = datetime.strptime(clean_str, fmt)
            break
        except:
            continue
            
    if parsed_date:
        return parsed_date, parsed_date.strftime("%d-%m-%y")
    
    # Jika gagal dikenali, kembalikan string aslinya agar tetap tampil
    return datetime.now(), clean_str

def clean_motor_name(raw_text):
    text = re.sub(r'^(ganti\s+motor\s*|cek\s+dan\s+dial\s+motor\s+pisau\s*-\s*ganti\s+motor\s+jika\s+ada\s+yang\s+jelek\s+nilainya\s*[:]?\s*)', '', raw_text, flags=re.IGNORECASE)
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
        
        print("4. Mengambil dan memproses seluruh baris data...")
        rows = driver.find_elements(By.XPATH, "//table//tbody/tr")
        
        processed_data = []
        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            col_data = [col.text.strip() for col in cols]
            
            if len(col_data) > 8:
                raw_job = col_data[1]
                personil = col_data[3]
                jadwal_teks = col_data[9]
                
                # Filter utama: Harus mengandung "ganti motor" dan BUKAN "dial motor"
                if "ganti motor" not in raw_job.lower() or "dial motor" in raw_job.lower():
                    continue
                
                # Cek apakah baris ini memiliki status (Done) di kolom jadwal
                if "(done)" not in jadwal_teks.lower():
                    continue
                
                # Ambil potongan teks tanggal yang ada sebelum tulisan (Done)
                # Contoh: "03 Nov (Done)" -> ambil "03 Nov"
                parts = re.split(r'\(Done\)', jadwal_teks, flags=re.IGNORECASE)
                raw_tgl_str = parts[0].strip()
                
                # Ekstrak tanggal terakhir menggunakan konverter universal
                dt_obj, tgl_terakhir = universal_date_converter(raw_tgl_str)
                
                nama_motor = clean_motor_name(raw_job)
                keterangan = "" 
                periode = "90"
                
                # Hitung Tanggal Berkala Selanjutnya (+90 hari) format DD-MM-YY secara otomatis
                next_dt = dt_obj + timedelta(days=90)
                tgl_selanjutnya = next_dt.strftime("%d-%m-%y")
                
                row_final = [nama_motor, tgl_terakhir, personil, keterangan, periode, tgl_selanjutnya]
                processed_data.append(row_final)
                
        print(f"-> Total data valid terkumpul: {len(processed_data)} baris.")
        
        if processed_data:
            print("5. Mengirim seluruh data ke Google Sheets...")
            response = requests.post(APPS_SCRIPT_URL, json=processed_data)
            print("Respon server Google Sheets:", response.text)

    except Exception as e:
        print("\n[ERROR]:", str(e))
        
    finally:
        driver.quit()

if __name__ == "__main__":
    run_scraper()
