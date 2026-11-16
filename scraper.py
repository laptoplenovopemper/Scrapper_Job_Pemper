
import os
import re
import time
import requests
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


# ============================================================
# 1. KONFIGURASI UTAMA
# ============================================================

LOGIN_URL = "http://job.pmp.web.id/login/"

APPS_SCRIPT_URL = (
    "https://script.google.com/macros/s/"
    "AKfycbyaKVBoR7ictxN1pYu0LAiaHARvltJlwlqV1wDsoz96_enjB7pi6bqAWLkHx-JTEnrx/exec"
)

APPSHEET_APP_ID = os.getenv("APPSHEET_APP_ID", "").strip()
APPSHEET_ACCESS_KEY = os.getenv("APPSHEET_ACCESS_KEY", "").strip()

APPSHEET_TABLE = "Trial"

USERNAME = os.getenv("SCRAPER_USERNAME", "").strip()
PASSWORD = os.getenv("SCRAPER_PASSWORD", "").strip()

SEARCH_KEYWORD = "Ganti Motor"
TIMEZONE = ZoneInfo("Asia/Jakarta")


# ============================================================
# 2. RENTANG TANGGAL
# ============================================================

def get_date_range():

    date_from_env = os.getenv("INPUT_DATE_FROM", "").strip()
    date_to_env = os.getenv("INPUT_DATE_TO", "").strip()

    if date_from_env and date_to_env:

        date_from = datetime.strptime(
            date_from_env, "%Y-%m-%d"
        ).date()

        date_to = datetime.strptime(
            date_to_env, "%Y-%m-%d"
        ).date()

        print(
            f"=== TANGGAL KUSTOM: "
            f"{date_from} s/d {date_to} ==="
        )

    elif not date_from_env and not date_to_env:

        date_to = datetime.now(TIMEZONE).date()

        date_from = date_to - timedelta(days=29)

        print(
            f"=== DEFAULT 30 HARI: "
            f"{date_from} s/d {date_to} ==="
        )

    else:

        raise ValueError(
            "Tanggal mulai dan tanggal selesai harus diisi bersamaan."
        )

    if date_from > date_to:
        raise ValueError(
            "Tanggal mulai tidak boleh lebih besar dari tanggal selesai."
        )

    return date_from, date_to


# ============================================================
# 3. KONVERSI TANGGAL
# ============================================================

def universal_date_converter(date_str):

    clean_str = re.sub(
        r'\((Done|Open)\)',
        '',
        str(date_str)
    ).strip()

    current_year = datetime.now(TIMEZONE).year

    bulan_indo = {
        'januari': 'January',
        'februari': 'February',
        'maret': 'March',
        'april': 'April',
        'mei': 'May',
        'juni': 'June',
        'juli': 'July',
        'agustus': 'August',
        'september': 'September',
        'oktober': 'October',
        'november': 'November',
        'desember': 'December',
        'jan': 'Jan',
        'feb': 'Feb',
        'mar': 'Mar',
        'apr': 'Apr',
        'jun': 'Jun',
        'jul': 'Jul',
        'agu': 'Aug',
        'sep': 'Sep',
        'okt': 'Oct',
        'nov': 'Nov',
        'des': 'Dec'
    }

    lower_str = clean_str.lower()

    for id_m, en_m in bulan_indo.items():

        if id_m in lower_str:

            clean_str = re.sub(
                id_m,
                en_m,
                lower_str,
                flags=re.IGNORECASE
            )

            break

    formats = [
        "%d %b %Y",
        "%d %b %y",
        "%d %B %Y",
        "%d %B",
        "%d %b",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d-%m-%y"
    ]

    for fmt in formats:

        try:

            if "%Y" not in fmt and "%y" not in fmt:

                parsed = datetime.strptime(
                    f"{clean_str} {current_year}",
                    "%d %b %Y"
                )

            else:

                parsed = datetime.strptime(
                    clean_str,
                    fmt
                )

            return parsed, parsed.strftime("%d-%m-%y")

        except ValueError:
            continue

    return datetime.now(TIMEZONE), clean_str


def parse_appsheet_date(value):

    if value is None or str(value).strip() == "":
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    value = str(value).strip()

    formats = [
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%m/%d/%y",
        "%d-%m-%Y",
        "%d-%m-%y",
        "%Y/%m/%d"
    ]

    for fmt in formats:

        try:
            return datetime.strptime(
                value[:26] if "%f" in fmt else value,
                fmt
            ).date()

        except ValueError:
            continue

    return None


# ============================================================
# 4. PEMBERSIHAN NAMA MOTOR
# ============================================================

def clean_motor_name(raw_text):

    text = re.sub(
        r'^(ganti\s+motor\s*|'
        r'cek\s+dan\s+dial\s+motor\s+pisau\s*-\s*'
        r'ganti\s+motor\s+jika\s+ada\s+yang\s+jelek\s+nilainya\s*[:]?\s*)',
        '',
        str(raw_text),
        flags=re.IGNORECASE
    )

    text = re.split(
        r'(&|,|\bTrial\b)',
        text,
        flags=re.IGNORECASE
    )[0].strip()

    return text if text else str(raw_text).strip()


# ============================================================
# 5. SCRAPER PERTAMA: JOB.PMP.WEB.ID
# ============================================================

def run_job_scraper(date_from, date_to):

    print("\n" + "=" * 60)
    print("SCRAPER 1: JOB.PMP.WEB.ID")
    print("=" * 60)

    processed_data = []

    driver = None

    dashboard_url = (
        f"http://job.pmp.web.id/"
        f"?date_from={date_from}"
        f"&date_to={date_to}"
        f"&pic=&line=&mesin=&sub_mesin="
        f"&departemen=&bagian=&sub_bagian="
        f"&search={SEARCH_KEYWORD.replace(' ', '+')}"
        f"&page_size=100"
    )

    try:

        print("1. Menyiapkan Chrome Headless...")

        options = Options()

        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")

        driver = webdriver.Chrome(
            service=Service(
                ChromeDriverManager().install()
            ),
            options=options
        )

        print("2. Membuka halaman login...")

        driver.get(LOGIN_URL)
        time.sleep(3)

        driver.find_element(
            By.ID,
            "id_username"
        ).send_keys(USERNAME)

        driver.find_element(
            By.ID,
            "id_password"
        ).send_keys(PASSWORD)

        driver.find_element(
            By.XPATH,
            "//button[@type='submit']"
        ).click()

        time.sleep(5)

        print("3. Mengakses dashboard...")

        driver.get(dashboard_url)

        time.sleep(5)

        page_num = 1
        max_pages = 32

        while page_num <= max_pages:

            print(
                f"-> Memproses halaman "
                f"{page_num}/{max_pages}"
            )

            time.sleep(2)

            rows = driver.find_elements(
                By.XPATH,
                "//table//tbody/tr"
            )

            print(
                f"   Ditemukan {len(rows)} baris."
            )

            if not rows:
                break

            for row in rows:

                cols = row.find_elements(
                    By.TAG_NAME,
                    "td"
                )

                col_data = [
                    col.text.strip()
                    for col in cols
                ]

                if len(col_data) <= 9:
                    continue

                raw_job = col_data[1]
                nama_mesin = col_data[5]
                personil = col_data[3]
                jadwal_teks = col_data[9]

                if (
                    "ganti motor" not in raw_job.lower()
                    or "dial motor" in raw_job.lower()
                ):
                    continue

                if "(done)" not in jadwal_teks.lower():
                    continue

                parts = re.split(
                    r'\(Done\)',
                    jadwal_teks,
                    flags=re.IGNORECASE
                )

                raw_tgl_str = parts[0].strip()

                dt_obj, tgl_terakhir = universal_date_converter(
                    raw_tgl_str
                )

                # Filter tambahan berdasarkan tanggal input
                if not (
                    date_from <= dt_obj.date() <= date_to
                ):
                    continue

                nama_motor = clean_motor_name(raw_job)

                keterangan = "Berkala"
                periode = "120"

                next_dt = dt_obj + timedelta(days=120)

                tgl_selanjutnya = next_dt.strftime(
                    "%d-%m-%y"
                )

                row_final = [
                    nama_motor,
                    nama_mesin,
                    tgl_terakhir,
                    personil,
                    keterangan,
                    periode,
                    tgl_selanjutnya
                ]

                processed_data.append(row_final)

            # Navigasi halaman berikutnya
            try:

                next_button = driver.find_element(
                    By.XPATH,
                    "//a[contains(text(), 'Selanjutnya')]"
                )

                parent_li = next_button.find_element(
                    By.XPATH,
                    "./.."
                )

                if (
                    "disabled"
                    in parent_li.get_attribute("class").lower()
                ):
                    break

                next_button.click()

                page_num += 1

                time.sleep(3)

            except Exception:

                print(
                    "   Halaman terakhir tercapai."
                )

                break

        print(
            f"TOTAL DATA BERKALA: "
            f"{len(processed_data)}"
        )

    except Exception as e:

        print(
            "[ERROR JOB.PMP.WEB.ID]:",
            str(e)
        )

    finally:

        if driver:
            driver.quit()

    return processed_data


# ============================================================
# 6. SCRAPER KEDUA: APPSHEET
# ============================================================

def run_appsheet_scraper(date_from, date_to):

    print("\n" + "=" * 60)
    print("SCRAPER 2: APPSHEET")
    print("=" * 60)

    if not APPSHEET_APP_ID or not APPSHEET_ACCESS_KEY:

        raise ValueError(
            "APPSHEET_APP_ID atau APPSHEET_ACCESS_KEY belum tersedia."
        )

    api_url = (
        f"https://api.appsheet.com/api/v2/apps/"
        f"{APPSHEET_APP_ID}/tables/"
        f"{APPSHEET_TABLE}/Action"
    )

    headers = {
        "ApplicationAccessKey": APPSHEET_ACCESS_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "Action": "Find",
        "Properties": {
            "Locale": "id-ID",
            "Timezone": "Asia/Jakarta"
        },
        "Rows": []
    }

    print("1. Menghubungi API AppSheet...")

    response = requests.post(
        api_url,
        headers=headers,
        json=payload,
        timeout=120
    )

    response.raise_for_status()

    result = response.json()

    if isinstance(result, list):

        rows = result

    elif isinstance(result, dict):

        rows = result.get("Rows", [])

    else:

        rows = []

    if not isinstance(rows, list):

        raise ValueError(
            "Format respons API AppSheet tidak sesuai."
        )

    print(
        f"2. Total baris diterima dari AppSheet: "
        f"{len(rows)}"
    )

    processed_data = []

    # Kolom yang diperiksa untuk keyword Ganti Motor
    search_columns = [
        "Detil Pekerjaan",
        "Part",
        "Unit Part",
        "Perawatan/Perbaikan",
        "Kategori",
        "Mesin",
        "Sub Mesin",
        "Keyword_Ditemukan",
        "Kolom_yang_Cocok"
    ]

    for item in rows:

        if not isinstance(item, dict):
            continue

        # ----------------------------------------------------
        # A. FILTER KEYWORD
        # ----------------------------------------------------

        searchable_text = " ".join(
            str(item.get(column, "") or "")
            for column in search_columns
        )

        if SEARCH_KEYWORD.lower() not in searchable_text.lower():
            continue

        # ----------------------------------------------------
        # B. FILTER TANGGAL
        # ----------------------------------------------------

        raw_date = item.get("Tanggal", "")

        tanggal_obj = parse_appsheet_date(raw_date)

        if tanggal_obj is None:
            continue

        if not (
            date_from <= tanggal_obj <= date_to
        ):
            continue

        # ----------------------------------------------------
        # C. MENGAMBIL INFORMASI MOTOR DAN MESIN
        # ----------------------------------------------------

        detail_pekerjaan = str(
            item.get("Detil Pekerjaan", "") or ""
        ).strip()

        part = str(
            item.get("Part", "") or ""
        ).strip()

        unit_part = str(
            item.get("Unit Part", "") or ""
        ).strip()

        mesin = str(
            item.get("Mesin", "") or ""
        ).strip()

        sub_mesin = str(
            item.get("Sub Mesin", "") or ""
        ).strip()

        # Nama motor diambil dari Part/Unit Part.
        # Jika kosong, ambil dari detail pekerjaan.

        nama_motor = (
            part
            or unit_part
            or clean_motor_name(detail_pekerjaan)
        )

        # Menggabungkan informasi mesin dan sub mesin
        # agar informasi keduanya tetap tersedia.

        if mesin and sub_mesin:

            nama_mesin = (
                mesin
                if mesin.lower() == sub_mesin.lower()
                else f"{mesin} - {sub_mesin}"
            )

        else:

            nama_mesin = mesin or sub_mesin

        # ----------------------------------------------------
        # D. PERSONIL
        # ----------------------------------------------------

        personil = str(
            item.get("PIC", "")
            or item.get("Nama", "")
            or ""
        ).strip()

        # ----------------------------------------------------
        # E. LABEL DAN PERIODE
        # ----------------------------------------------------

        tgl_terakhir = tanggal_obj.strftime(
            "%d-%m-%y"
        )

        keterangan = "Perbaikan"

        periode = "120"

        next_date = tanggal_obj + timedelta(days=120)

        tgl_selanjutnya = next_date.strftime(
            "%d-%m-%y"
        )

        # ----------------------------------------------------
        # F. FORMAT DATA FINAL
        # ----------------------------------------------------

        row_final = [
            nama_motor,
            nama_mesin,
            tgl_terakhir,
            personil,
            keterangan,
            periode,
            tgl_selanjutnya
        ]

        processed_data.append(row_final)

    print(
        f"3. TOTAL DATA PERBAIKAN: "
        f"{len(processed_data)}"
    )

    return processed_data


# ============================================================
# 7. GABUNGKAN DAN KIRIM KE GOOGLE SHEETS
# ============================================================

def send_to_google_sheets(all_data):

    print("\n" + "=" * 60)
    print("MENGIRIM DATA KE GOOGLE SHEETS")
    print("=" * 60)

    if not all_data:

        print(
            "Tidak ada data dari kedua sumber."
        )

        return

    print(
        f"Total data gabungan: {len(all_data)}"
    )

    count_berkala = sum(
        1 for row in all_data
        if row[4] == "Berkala"
    )

    count_perbaikan = sum(
        1 for row in all_data
        if row[4] == "Perbaikan"
    )

    print(
        f"Data Berkala   : {count_berkala}"
    )

    print(
        f"Data Perbaikan : {count_perbaikan}"
    )

    response = requests.post(
        APPS_SCRIPT_URL,
        json=all_data,
        timeout=120
    )

    response.raise_for_status()

    print(
        "Respon Google Sheets:",
        response.text
    )

    print(
        "Sinkronisasi berhasil."
    )


# ============================================================
# 8. PROGRAM UTAMA
# ============================================================

def run_scraper():

    print("\n")
    print("=" * 60)
    print("SISTEM SCRAPER GABUNGAN MOTOR PMP")
    print("=" * 60)

    # A. Rentang tanggal yang sama untuk dua scraper

    date_from, date_to = get_date_range()

    # B. Scraper berkala

    berkala_data = run_job_scraper(
        date_from,
        date_to
    )

    # C. Scraper perbaikan

    perbaikan_data = run_appsheet_scraper(
        date_from,
        date_to
    )

    # D. Gabungkan data

    combined_data = (
        berkala_data + perbaikan_data
    )

    print("\n")
    print("=" * 60)
    print("REKAPITULASI SCRAPER")
    print("=" * 60)

    print(
        f"Berkala   : {len(berkala_data)}"
    )

    print(
        f"Perbaikan : {len(perbaikan_data)}"
    )

    print(
        f"TOTAL     : {len(combined_data)}"
    )

    # E. Kirim satu kali ke database

    send_to_google_sheets(
        combined_data
    )

    print("\n")
    print("=" * 60)
    print("SELURUH PROSES SELESAI")
    print("=" * 60)


if __name__ == "__main__":

    run_scraper()
