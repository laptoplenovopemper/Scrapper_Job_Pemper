import os
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# 1. MENANGKAP PARAMETER TANGGAL DARI WEB APP (Via GitHub Actions Environment)
date_from_input = os.environ.get("INPUT_DATE_FROM") # Format dari HTML: YYYY-MM-DD
date_to_input = os.environ.get("INPUT_DATE_TO")     # Format dari HTML: YYYY-MM-DD

if date_from_input and date_to_input:
    # Konversi dari YYYY-MM-DD ke DD/MM/YYYY (menyesuaikan format input di website PMP)
    dt_from = datetime.strptime(date_from_input, "%Y-%m-%d")
    dt_to = datetime.strptime(date_to_input, "%Y-%m-%d")
    
    START_DATE = dt_from.strftime("%d/%m/%Y") # Hasil: DD/MM/YYYY
    END_DATE = dt_to.strftime("%d/%m/%Y")     # Hasil: DD/MM/YYYY
    print(f"=== Menggunakan Tanggal Kustom dari Web App ===")
    print(f"Dari: {START_DATE} S/d: {END_DATE}")
else:
    # Default jika dijalankan otomatis (1 bulan terakhir dalam format DD/MM/YYYY)
    now = datetime.now()
    month_ago = now - timedelta(days=30)
    START_DATE = month_ago.strftime("%d/%m/%Y")
    END_DATE = now.strftime("%d/%m/%Y")
    print(f"=== Menggunakan Tanggal Default (1 Bulan Terakhir) ===")
    print(f"Dari: {START_DATE} S/d: {END_DATE}")

# Ambil kredensial rahasia dari Environment/Secrets
USERNAME = os.environ.get("SCRAPER_USERNAME")
PASSWORD = os.environ.get("SCRAPER_PASSWORD")

def run_scraper():
    scraped_data = []
    print("Membuka browser otomatis (Headless Mode)...")
    
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    try:
        # 1. Buka halaman login PMP
        driver.get("https://job.pmp.web.id/") # Sesuaikan URL login/dashboard Anda
        
        # Contoh proses login (Sesuaikan ID/Name elemen form login website PMP Anda)
        # driver.find_element(By.ID, "username").send_keys(USERNAME)
        # driver.find_element(By.ID, "password").send_keys(PASSWORD)
        # driver.find_element(By.ID, "login-btn").click()
        
        # 2. Masukkan filter tanggal ke form website PMP (Format sudah DD/MM/YYYY)
        print(f"Memasukkan filter tanggal: {START_DATE} sampai {END_DATE}")
        
        # Contoh pengisian elemen input tanggal berdasarkan tangkapan layar web PMP Anda:
        # date_from_element = driver.find_element(By.NAME, "date_from") # Sesuaikan ID/Name elemen
        # date_from_element.clear()
        # date_from_element.send_keys(START_DATE)
        
        # date_to_element = driver.find_element(By.NAME, "date_to")     # Sesuaikan ID/Name elemen
        # date_to_element.clear()
        # date_to_element.send_keys(END_DATE)
        
        # Klik tombol Filter
        # driver.find_element(By.ID, "btn-filter").click() # Sesuaikan tombol filter
        
        # 3. Ekstraksi data dari tabel hasil scraping
        # Contoh mengambil baris-baris tabel:
        # rows = driver.find_elements(By.XPATH, "//table//tbody/tr")
        # for row in rows:
        #     cols = row.find_elements(By.TAG_NAME, "td")
        #     cols_text = [col.text for col in cols]
        #     scraped_data.append(cols_text)

        print("Scraping data berhasil dilakukan!")
        driver.quit()
        return scraped_data

    except Exception as e:
        print(f"Terjadi kesalahan saat scraping: {str(e)}")
        driver.quit()
        return []

def save_to_google_sheets(data):
    if not data:
        print("Tidak ada data untuk dimasukkan ke spreadsheet.")
        return

    print("Menghubungkan ke Google Sheets...")
    # Autentikasi Google Sheets via gspread
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    
    # Menggunakan credential dari file JSON atau Environment Secret
    # credentials_dict = ... 
    # gc = gspread.authorize(credentials)
    
    # sheet = gc.open_by_key("1TJHsAW2_xdunVovqQ2yOwNfKyaXsutyHdOx7A9Cw4gs").getSheetByName("Sheet1")
    
    # Hapus data lama (opsional) lalu masukkan data baru hasil scraping
    # sheet.clear()
    # sheet.append_rows(data)
    print("Data berhasil diperbarui ke Spreadsheet!")

if __name__ == "__main__":
    data_hasil = run_scraper()
    # save_to_google_sheets(data_hasil)
