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
    print(f"=== Menggunakan Tanggal Kustom: {START_DATE} s/d {END_DATE} ===")
else:
    # Kembali ke default 30 hari terakhir jika kosong / dijalankan otomatis
    END_DATE = datetime.now().strftime("%Y-%m-%d")
    START_DATE = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    print(f"=== Menggunakan Tanggal Default (30 Hari Terakhir): {START_DATE} s/d {END_DATE} ===")

def run_scraper():
    scraped_data = []
    print("Memulai proses scraping...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    # Looping halaman (misal dari halaman 1 sampai 32)
    total_pages = 32 
    
    try:
        for page in range(1, total_pages + 1):
            target_url = f"https://job.pmp.web.id/?date_from={START_DATE}&date_to={END_DATE}&daily_page={page}"
            print(f"Mengambil data halaman {page}...")
            
            response = requests.get(target_url, headers=headers, timeout=10)
            if response.status_code != 200:
                print(f"Gagal mengakses halaman {page}, status: {response.status_code}")
                break
                
            soup = BeautifulSoup(response.text, 'html.parser')
            rows = soup.select("table tbody tr")
            
            if not rows:
                print(f"Halaman {page} kosong atau habis.")
                break
                
            count = 0
            for row in rows:
                cols = row.find_all('td')
                cols_text = [col.text.strip() for col in cols]
                if cols_text and len(cols_text) > 1 and "Tidak ada" not in cols_text[0]:
                    scraped_data.append(cols_text)
                    count += 1
            
            print(f"Berhasil menarik {count} baris dari halaman {page}.")
            
        print(f"Total keseluruhan data terkumpul: {len(scraped_data)} baris.")
        return scraped_data

    except Exception as e:
        print(f"Terjadi kesalahan saat scraping: {str(e)}")
        return []

def save_to_google_sheets(data):
    if not data:
        print("Tidak ada data untuk disimpan ke Google Sheets.")
        return

    print("Menyimpan data ke Google Sheets...")
    # Masukkan logika gspread Anda di sini jika ingin otomatis memperbarui Google Sheets
    print("Selesai!")

if __name__ == "__main__":
    hasil_data = run_scraper()
    save_to_google_sheets(hasil_data)
