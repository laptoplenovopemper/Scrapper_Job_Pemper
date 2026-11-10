import os
import time
import re
import requests
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# 1. Menangkap rentang tanggal kustom dari Web App / GitHub Actions dengan fallback 30 hari terakhir
date_from_env = os.getenv("INPUT_DATE_FROM", "").strip()
date_to_env = os.getenv("INPUT_DATE_TO", "").strip()

if date_from_env and date_to_env:
    date_from = date_from_env
    date_to = date_to_env
    print(f"=== Menggunakan Tanggal Kustom: {date_from} s/d {date_to} ===")
else:
    date_to = datetime.now().strftime("%Y-%m-%d")
    date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    print(f"=== Menggunakan Tanggal Default (30 Hari Terakhir): {date_from} s/d {date_to} ===")

LOGIN_URL = "http://job.pmp.web.id/login/" 
SEARCH_KEYWORD = "Ganti Motor"

# Kita set page_size=100 agar dalam 1 halaman langsung tampil banyak baris
DASHBOARD_URL = f"http://job.pmp.web.id/?date_from={date_from}&date_to={date_to}&pic=&line=&mesin=&sub_mesin=&departemen=&bagian=&sub_bagian=&search={SEARCH_KEYWORD.replace(' ', '+')}&page_size=100"

# Ambil Username & Password secara aman dari GitHub Secrets
USERNAME = os.getenv("SCRAPER_USERNAME")                     
PASSWORD = os.getenv("SCRAPER_PASSWORD")              
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyaKVBoR7ictxN1pYu0LAiaHARvltJlwlqV1wDsoz96_enjB7pi6bqAWLkHx-JTEnrx/exec"

def universal_date_converter(date_str):
    clean_str = re.sub(r'\((Done|Open)\)', '', date_str).strip()
    current_year = datetime.now().year
    
    bulan_indo = {
        'jan': 'Jan', 'feb': 'Feb', 'mar': 'Mar', 'apr': 'Apr', 
        'mei': 'May', 'jun': 'Jun', 'jul': 'Jul', 'agu': 'Aug', 
        'sep': 'Sep', 'okt': 'Oct', 'nov': 'Nov', 'des': 'Dec',
        'januari': 'January', 'februari': 'February', 'maret': 'March', 'april': 'April',
        'mei': 'May', 'juni': 'June', 'juli': 'July', 'agustus': 'August',
        'september': 'September', 'oktober': 'October', 'november': 'November', 'desember': 'December'
    }
    
    lower_str = clean_str.lower()
    for id_m, en_m in bulan_indo.items():
        if id_m in lower_str:
            clean_str = re.sub(id_m, en_m, lower_str, flags=re.IGNORECASE)
            break
            
    formats = [
        "%d %b %Y", "%d %b %y", "%d %B %Y", "%d %B", "%d %b", 
        "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d-%m-%y"
    ]
    
    parsed_date = None
    for fmt in formats:
        try:
            if "%Y" not in fmt and "%y" not in fmt:
                parsed_date = datetime.strptime(f"{clean_str} {current_year}", f"%d %b %Y")
            else:
                parsed_date = datetime.strptime(clean_str, fmt)
            break
        except:
            continue
            
    if parsed_date:
        return parsed_date, parsed_date.strftime("%d-%m-%y")
    
    return datetime.now(), clean_str

def clean_motor_name(raw_text):
    text = re.sub(r'^(ganti\s+motor\s*|cek\s+dan\s+dial\s+motor\s+pisau\s*-\s*ganti\s+motor\s+jika\s+ada\s+yang\s+jelek\s+nilainya\s*[:]?\s*)', '', raw_text, flags=re.IGNORECASE)
    text = re.split(r'(&|,|\bTrial\b)', text)[0].strip()
    return text if text else raw_text

def run_scraper():
    print("1. Menyiapkan browser Chrome Headless...")
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    try:
        print("2. Membuka halaman login...")
        driver.get(LOGIN_URL)
        time.sleep(3)
        
        driver.find_element(By.ID, "id_username").send_keys(USERNAME)
        driver.find_element(By.ID, "id_password").send_keys(PASSWORD)
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        time.sleep(5)
        
        print(f"3. Mengakses URL Dashboard: {DASHBOARD_URL}")
        driver.get(DASHBOARD_URL)
        time.sleep(5)
        
        print("4. Mengambil dan memproses seluruh baris data dari semua halaman...")
        processed_data = []
        page_num = 1
        max_pages = 32 # Batas maksimal halaman sesuai info web Anda
        
        while page_num <= max_pages:
            print(f"-> Memproses halaman {page_num} dari {max_pages}...")
            time.sleep(2)
            
            rows = driver.find_elements(By.XPATH, "//table//tbody/tr")
            print(f"   Ditemukan {len(rows)} baris pada halaman ini.")
            
            if not rows:
                print("   Tabel kosong, menghentikan perayapan.")
                break
                
            for row in rows:
                cols = row.find_elements(By.TAG_NAME, "td")
                col_data = [col.text.strip() for col in cols]
                
                if len(col_data) > 8:
                    raw_job = col_data[1]
                    nama_mesin = col_data[5] 
                    personil = col_data[3]
                    jadwal_teks = col_data[9]
                    
                    # Filter kata kunci & abaikan dial motor
                    if "ganti motor" not in raw_job.lower() or "dial motor" in raw_job.lower():
                        continue
                    
                    # Hanya ambil yang berstatus Done
                    if "(done)" not in jadwal_teks.lower():
                        continue
                    
                    parts = re.split(r'\(Done\)', jadwal_teks, flags=re.IGNORECASE)
                    raw_tgl_str = parts[0].strip()
                    
                    dt_obj, tgl_terakhir = universal_date_converter(raw_tgl_str)
                    
                    nama_motor = clean_motor_name(raw_job)
                    keterangan = "" 
                    periode = "90"
                    
                    next_dt = dt_obj + timedelta(days=90)
                    tgl_selanjutnya = next_dt.strftime("%d-%m-%y")
                    
                    row_final = [nama_motor, nama_mesin, tgl_terakhir, personil, keterangan, periode, tgl_selanjutnya]
                    processed_data.append(row_final)
            
            # Cek tombol "Selanjutnya" secara aman
            try:
                next_button = driver.find_element(By.XPATH, "//a[contains(text(), 'Selanjutnya')]")
                parent_li = next_button.find_element(By.XPATH, "./..")
                
                # Jika tombol selanjutnya berstatus disabled atau kelasnya mengandung disabled
                if "disabled" in parent_li.get_attribute("class").lower():
                    print("   Sudah mencapai halaman terakhir (tombol disabled).")
                    break
                
                next_button.click()
                page_num += 1
                time.sleep(3)
            except Exception:
                print("   Tombol 'Selanjutnya' tidak ditemukan lagi atau sudah di halaman terakhir.")
                break
                
        print(f"\n=> Total keseluruhan data valid terkumpul: {len(processed_data)} baris.")
        
        if processed_data:
            print("5. Mengirim seluruh data ke Google Sheets...")
            response = requests.post(APPS_SCRIPT_URL, json=processed_data)
            print("Respon server Google Sheets:", response.text)
        else:
            print("Tidak ada data 'Done' yang memenuhi kriteria pada rentang tanggal ini.")

    except Exception as e:
        print("\n[ERROR]:", str(e))
        
    finally:
        driver.quit()

if __name__ == "__main__":
    run_scraper()
