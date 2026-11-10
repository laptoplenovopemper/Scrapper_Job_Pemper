import os
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 1. Menangkap Parameter Tanggal dari Web App / GitHub Actions
date_from_input = os.environ.get("INPUT_DATE_FROM", "").strip()
date_to_input = os.environ.get("INPUT_DATE_TO", "").strip()

if date_from_input and date_to_input:
    START_DATE = date_from_input
    END_DATE = date_to_input
else:
    END_DATE = datetime.now().strftime("%Y-%m-%d")
    START_DATE = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

# Ambil username & password dari GitHub Secrets
USERNAME = os.environ.get("SCRAPER_USERNAME")
PASSWORD = os.environ.get("SCRAPER_PASSWORD")

def run_scraper():
    scraped_data = []
    print("Memulai proses scraping dengan autentikasi sesi...")
    
    # Gunakan Session agar cookie login tersimpan otomatis
    session = requests.Session()
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    session.headers.update(headers)
    
    try:
        # LANGKAH A: LAKUKAN LOGIN TERLEBIH DAHULU (Sesuaikan URL & nama input form login PMP Anda)
        login_url = "https://job.pmp.web.id/login" # Sesuaikan jika URL login berbeda
        login_payload = {
            "username": USERNAME, # Sesuaikan name attribute dari input form
            "password": PASSWORD  # Sesuaikan name attribute dari input form
        }
        
        print("Melakukan login ke website PMP...")
        login_response = session.post(login_url, data=login_payload)
        
        if login_response.status_code != 200:
            print(f"Login gagal atau halaman login tidak merespons (Status: {login_response.status_code})")
            return []

        print("Login berhasil! Mengambil data halaman...")
        
        # LANGKAH B: TARIK DATA SETELAH LOGIN BERHASIL (Looping halaman 1 sampai 32)
        total_pages = 32 
        for page in range(1, total_pages + 1):
            target_url = f"https://job.pmp.web.id/?date_from={START_DATE}&date_to={END_DATE}&daily_page={page}"
            
            response = session.get(target_url, timeout=10)
            if response.status_code != 200:
                break
                
            soup = BeautifulSoup(response.text, 'html.parser')
            rows = soup.select("table tbody tr")
            
            if not rows:
                break
                
            count = 0
            for row in rows:
                cols = row.find_all('td')
                cols_text = [col.text.strip() for col in cols]
                if cols_text and len(cols_text) > 1 and "Tidak ada" not in cols_text[0]:
                    scraped_data.append(cols_text)
                    count += 1
            
            print(f"Halaman {page}: Berhasil menarik {count} baris data.")
            
        print(f"Total keseluruhan data terkumpul: {len(scraped_data)} baris.")
        return scraped_data

    except Exception as e:
        print(f"Terjadi kesalahan saat proses scraping: {str(e)}")
        return []

if __name__ == "__main__":
    hasil_data = run_scraper()
    # Tambahkan fungsi simpan ke Google Sheets di sini jika data sudah berhasil ditarik
