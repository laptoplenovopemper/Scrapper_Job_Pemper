import os
import re
import time
import requests
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
from urllib.parse import urlencode

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager


# ============================================================
# 1. KONFIGURASI UTAMA
# ============================================================

LOGIN_URL = "http://job.pmp.web.id/login/"
BASE_URL = "http://job.pmp.web.id/"

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

HEADLESS = True
PAGE_LOAD_TIMEOUT = 45
ELEMENT_TIMEOUT = 20
MAX_PAGES = 100

ALLOW_FALLBACK_COLUMN = True

# ID harus sama dengan run_id yang dikembalikan oleh
# action trigger_scraper pada Apps Script.
#
# INPUT_RUN_ID dapat diberikan melalui workflow input.
# Jika tidak tersedia, gunakan GITHUB_RUN_ID dari GitHub Actions.
RUN_ID = (
    os.getenv("INPUT_RUN_ID", "").strip()
    or os.getenv("GITHUB_RUN_ID", "").strip()
)

if not RUN_ID:
    RUN_ID = (
        "LOCAL-"
        + datetime.now(TIMEZONE).strftime("%Y%m%d%H%M%S")
    )
    print(
        "PERINGATAN: INPUT_RUN_ID dan GITHUB_RUN_ID tidak ditemukan. "
        "Menggunakan RUN_ID lokal:",
        RUN_ID
    )


# ============================================================
# 2. SISTEM PROGRESS BAR
# ============================================================

_last_progress = -1
_last_message = ""


def update_progress(
    progress,
    message,
    status="running",
    error=""
):
    """
    Mengirim progres scraper ke Apps Script.

    Format yang dikirim:
    {
        "action": "update_scraper_progress",
        "run_id": "...",
        "status": "running",
        "progress": 35,
        "message": "Memproses data...",
        "error": ""
    }

    Kegagalan mengirim progress tidak menghentikan scraper.
    """

    global _last_progress, _last_message

    try:
        progress = int(progress)
        progress = max(0, min(100, progress))

        payload = {
            "action": "update_scraper_progress",
            "run_id": str(RUN_ID),
            "status": status,
            "progress": progress,
            "message": str(message),
            "error": str(error or "")
        }

        # Hindari pengiriman berulang jika angka dan pesan sama.
        if (
            status == "running"
            and progress == _last_progress
            and message == _last_message
        ):
            return

        print(
            f"[PROGRESS {progress}%] {status.upper()} - {message}"
        )

        response = requests.post(
            APPS_SCRIPT_URL,
            json=payload,
            timeout=30
        )

        response.raise_for_status()

        _last_progress = progress
        _last_message = message

    except Exception as e:
        print(
            "[PERINGATAN PROGRESS] Gagal mengirim progres ke Apps Script:",
            str(e)
        )


# ============================================================
# 3. RENTANG TANGGAL
# ============================================================


def get_date_range():

    date_from_env = os.getenv("INPUT_DATE_FROM", "").strip()
    date_to_env = os.getenv("INPUT_DATE_TO", "").strip()

    print("\n========================================")
    print("PEMERIKSAAN INPUT TANGGAL GITHUB ACTIONS")
    print("========================================")
    print(f"INPUT_DATE_FROM diterima : {date_from_env!r}")
    print(f"INPUT_DATE_TO diterima   : {date_to_env!r}")

    if date_from_env and date_to_env:

        try:
            date_from = datetime.strptime(
                date_from_env, "%Y-%m-%d"
            ).date()

            date_to = datetime.strptime(
                date_to_env, "%Y-%m-%d"
            ).date()

        except ValueError:
            raise ValueError(
                "Format tanggal tidak valid. Gunakan YYYY-MM-DD."
            )

        print(
            f"MODE SCRAPING: TANGGAL PILIHAN "
            f"{date_from} s/d {date_to}"
        )

    elif not date_from_env and not date_to_env:

        date_to = datetime.now(TIMEZONE).date()
        date_from = date_to - timedelta(days=29)

        print(
            f"MODE SCRAPING: DEFAULT 30 HARI "
            f"{date_from} s/d {date_to}"
        )

    else:

        raise ValueError(
            "Hanya satu tanggal yang diterima. "
            "Tanggal mulai dan selesai harus diisi bersamaan."
        )

    if date_from > date_to:
        raise ValueError(
            "Tanggal mulai tidak boleh lebih besar dari tanggal selesai."
        )

    print("========================================\n")

    return date_from, date_to

# ============================================================
# 4. KONVERSI TANGGAL
# ============================================================

def universal_date_converter(date_str):

    if not date_str:
        return None, ""

    clean_str = re.sub(
        r'\((Done|Open)\)',
        '',
        str(date_str),
        flags=re.IGNORECASE
    ).strip()

    clean_str = re.sub(
        r'\s+',
        ' ',
        clean_str
    )

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
        'mei': 'May',
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

            if fmt in ("%d %B", "%d %b"):

                parsed = datetime.strptime(
                    f"{clean_str} {current_year}",
                    fmt + " %Y"
                )

            else:

                parsed = datetime.strptime(
                    clean_str,
                    fmt
                )

            return parsed, parsed.strftime("%d-%m-%y")

        except ValueError:
            continue

    return None, ""


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
# 5. PEMBERSIHAN NAMA MOTOR
# ============================================================

def clean_motor_name(raw_text):

    text = str(raw_text or "").strip()

    text = re.sub(
        r'^(ganti\s+motor\s*|'
        r'cek\s+dan\s+dial\s+motor\s+pisau\s*-\s*'
        r'ganti\s+motor\s+jika\s+ada\s+yang\s+jelek\s+nilainya\s*[:]?\s*)',
        '',
        text,
        flags=re.IGNORECASE
    )

    text = re.split(
        r'(&|,|\bTrial\b)',
        text,
        maxsplit=1,
        flags=re.IGNORECASE
    )[0].strip()

    return text if text else str(raw_text or "").strip()


# ============================================================
# 6. EKSTRAKSI NAMA MOTOR DARI DETAIL PEKERJAAN APPSHEET
# ============================================================

def extract_motor_from_detail(detail_pekerjaan):

    if not detail_pekerjaan:
        return ""

    text = str(detail_pekerjaan).strip()

    match = re.search(
        r'ganti\s+motor\s*[:\-]?\s*(.*)',
        text,
        flags=re.IGNORECASE | re.DOTALL
    )

    if not match:
        return ""

    nama_motor = match.group(1).strip()

    nama_motor = re.split(
        r'[,&;\n]|\bTrial\b',
        nama_motor,
        maxsplit=1,
        flags=re.IGNORECASE
    )[0].strip()

    return nama_motor.strip(" :-_.")


# ============================================================
# 7. NORMALISASI NAMA MESIN
# ============================================================

def normalize_machine_name(raw_machine):

    if not raw_machine:
        return ""

    text = str(raw_machine).strip()

    match = re.search(
        r'\bFS\s*0*(\d{1,2})\b',
        text,
        flags=re.IGNORECASE
    )

    if match:
        return f"FS {int(match.group(1))}"

    return text.upper()


# ============================================================
# 8. NORMALISASI SUB MESIN
# ============================================================

def normalize_sub_machine(raw_sub_machine):

    if not raw_sub_machine:
        return ""

    return re.sub(
        r'\s+',
        ' ',
        str(raw_sub_machine).strip()
    ).upper()


# ============================================================
# 9. MEMBACA HEADER TABEL JOB.PMP
# ============================================================

def normalize_header(text):

    return re.sub(
        r'[^a-z0-9]',
        '',
        str(text or '').lower()
    )


def get_job_table_column_indices(driver):

    """
    Personil Job PMP hanya diambil dari kolom PERSONIL.
    Kolom PIC tidak digunakan sebagai alternatif.
    """

    fallback_indices = {
        "job": 1,
        "personil": 3,
        "mesin": 5,
        "jadwal": 9,
        "sub_mesin": None
    }

    try:

        tables = driver.find_elements(
            By.XPATH,
            "//table"
        )

        for table in tables:

            headers = table.find_elements(
                By.XPATH,
                ".//thead//th"
            )

            if not headers:

                headers = table.find_elements(
                    By.XPATH,
                    ".//tr[1]/*"
                )

            if not headers:
                continue

            header_map = {}

            for index, header in enumerate(headers):

                key = normalize_header(header.text)

                if key:
                    header_map[key] = index

            aliases = {

                "job": [
                    "pekerjaan",
                    "detailpekerjaan",
                    "namapekerjaan",
                    "job",
                    "aktivitas"
                ],

                "personil": [
                    "personil"
                ],

                "mesin": [
                    "mesin",
                    "namamesin"
                ],

                "sub_mesin": [
                    "submesin",
                    "namasubmesin"
                ],

                "jadwal": [
                    "jadwal",
                    "tanggal",
                    "tanggalpekerjaan",
                    "tanggaljadwal"
                ]
            }

            found = 0

            indices = {
                "job": None,
                "personil": None,
                "mesin": None,
                "jadwal": None,
                "sub_mesin": None
            }

            for field, names in aliases.items():

                for name in names:

                    if name in header_map:

                        indices[field] = header_map[name]
                        found += 1
                        break

            if found > 0:

                print(
                    "   Header tabel ditemukan:",
                    header_map
                )

                print(
                    "   Posisi kolom yang digunakan:",
                    indices
                )

                if indices["personil"] is None:

                    print(
                        "   PERINGATAN: Header Personil tidak ditemukan."
                    )

                    print(
                        "   Data personil dikosongkan. "
                        "Kolom PIC tidak digunakan."
                    )

                return indices

        print(
            "   PERINGATAN: Header tabel tidak ditemukan."
        )

        if ALLOW_FALLBACK_COLUMN:

            print(
                "   Menggunakan posisi kolom cadangan:",
                fallback_indices
            )

            return fallback_indices.copy()

        return {
            "job": None,
            "personil": None,
            "mesin": None,
            "jadwal": None,
            "sub_mesin": None
        }

    except Exception as e:

        print(
            "   Gagal membaca header tabel:",
            str(e)
        )

        if ALLOW_FALLBACK_COLUMN:
            return fallback_indices.copy()

        return {
            "job": None,
            "personil": None,
            "mesin": None,
            "jadwal": None,
            "sub_mesin": None
        }


# ============================================================
# 10. FUNGSI BANTU SCRAPER JOB PMP
# ============================================================

def get_cell_value(col_data, index):

    if index is None:
        return ""

    if index < 0 or index >= len(col_data):
        return ""

    return str(col_data[index] or "").strip()


def find_date_done_in_row(col_data):

    for cell in col_data:

        if not re.search(
            r'\(\s*Done\s*\)',
            cell,
            flags=re.IGNORECASE
        ):
            continue

        date_text = re.sub(
            r'\(\s*Done\s*\)',
            '',
            cell,
            flags=re.IGNORECASE
        ).strip()

        dt_obj, formatted = universal_date_converter(
            date_text
        )

        if dt_obj:
            return cell, dt_obj, formatted

    return "", None, ""


def find_job_text_in_row(col_data):

    for cell in col_data:

        lower = cell.lower()

        if (
            "ganti motor" in lower
            and "dial motor" not in lower
        ):
            return cell

    return ""


def find_machine_text_in_row(col_data):

    for cell in col_data:

        if re.search(
            r'\bFS\s*0*\d{1,2}\b',
            cell,
            flags=re.IGNORECASE
        ):
            return cell

    return ""


def find_sub_machine_text_in_row(col_data):

    return ""


def save_debug_screenshot(driver, filename="job_pmp_debug.png"):

    try:

        driver.save_screenshot(filename)

        print(
            f"   Screenshot debug tersimpan: {filename}"
        )

    except Exception:
        pass


# ============================================================
# 11. SCRAPER PERTAMA: JOB.PMP.WEB.ID
# ============================================================

def run_job_scraper(date_from, date_to):

    print("\n" + "=" * 60)
    print("SCRAPER 1: JOB.PMP.WEB.ID")
    print("=" * 60)

    processed_data = []

    driver = None

    query_params = {
        "date_from": date_from.strftime("%Y-%m-%d"),
        "date_to": date_to.strftime("%Y-%m-%d"),
        "pic": "",
        "line": "",
        "mesin": "",
        "sub_mesin": "",
        "departemen": "",
        "bagian": "",
        "sub_bagian": "",
        "search": SEARCH_KEYWORD,
        "page_size": "100"
    }

    dashboard_url = (
        BASE_URL + "?" + urlencode(query_params)
    )

    try:

        if not USERNAME or not PASSWORD:

            raise ValueError(
                "SCRAPER_USERNAME atau SCRAPER_PASSWORD kosong. "
                "Periksa Secrets GitHub Actions."
            )

        update_progress(
            5,
            "Menyiapkan browser untuk mengambil data Job PMP."
        )

        print("1. Menyiapkan Chrome...")

        options = Options()

        if HEADLESS:
            options.add_argument("--headless=new")

        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--lang=id-ID")

        driver = webdriver.Chrome(
            service=Service(
                ChromeDriverManager().install()
            ),
            options=options
        )

        driver.set_page_load_timeout(
            PAGE_LOAD_TIMEOUT
        )

        wait = WebDriverWait(
            driver,
            ELEMENT_TIMEOUT
        )

        # LOGIN
        update_progress(
            8,
            "Membuka halaman login Job PMP."
        )

        print("2. Membuka halaman login...")

        driver.get(LOGIN_URL)

        wait.until(
            EC.presence_of_element_located(
                (By.ID, "id_username")
            )
        )

        username_field = driver.find_element(
            By.ID,
            "id_username"
        )

        password_field = driver.find_element(
            By.ID,
            "id_password"
        )

        username_field.clear()
        username_field.send_keys(USERNAME)

        password_field.clear()
        password_field.send_keys(PASSWORD)

        login_button = driver.find_element(
            By.XPATH,
            "//button[@type='submit']"
        )

        login_button.click()

        time.sleep(4)

        print(
            "   URL setelah login:",
            driver.current_url
        )

        if "login" in driver.current_url.lower():

            page_text = driver.find_element(
                By.TAG_NAME,
                "body"
            ).text

            print(
                "   Isi halaman setelah login:",
                page_text[:500]
            )

            raise RuntimeError(
                "Login Job PMP gagal atau masih berada di halaman login."
            )

        print("   Login berhasil atau sesi sudah aktif.")

        update_progress(
            12,
            "Login Job PMP berhasil. Mengakses dashboard."
        )

        # BUKA DASHBOARD
        print("3. Mengakses dashboard Job PMP...")

        print(
            "   URL dashboard:",
            dashboard_url
        )

        driver.get(dashboard_url)

        try:

            wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//table")
                )
            )

        except TimeoutException:

            print(
                "   Tabel tidak muncul dalam waktu tunggu."
            )

            print(
                "   URL saat ini:",
                driver.current_url
            )

            print(
                "   Isi halaman:",
                driver.find_element(
                    By.TAG_NAME,
                    "body"
                ).text[:1500]
            )

            save_debug_screenshot(driver)

            raise RuntimeError(
                "Tabel Job PMP tidak ditemukan."
            )

        time.sleep(2)

        print(
            "   Dashboard berhasil dibuka:",
            driver.current_url
        )

        column_indices = get_job_table_column_indices(
            driver
        )

        update_progress(
            15,
            "Dashboard Job PMP siap. Mulai mengambil data."
        )

        # PROSES PAGINATION
        page_num = 1
        visited_pages = set()

        while page_num <= MAX_PAGES:

            print("\n----------------------------------------")

            print(
                f"MEMPROSES HALAMAN {page_num}"
            )

            print("----------------------------------------")

            update_progress(
                15,
                f"Sedang memproses halaman Job PMP ke-{page_num}."
            )

            time.sleep(1)

            current_url = driver.current_url

            if current_url in visited_pages:

                print(
                    "   URL halaman sudah pernah diproses. Berhenti."
                )

                break

            visited_pages.add(current_url)

            rows = driver.find_elements(
                By.XPATH,
                "//table//tbody/tr"
            )

            print(
                f"   Jumlah baris ditemukan: {len(rows)}"
            )

            if not rows:

                print(
                    "   Tidak ada baris pada halaman ini."
                )

                print(
                    "   Isi halaman:",
                    driver.find_element(
                        By.TAG_NAME,
                        "body"
                    ).text[:1000]
                )

                break

            page_added = 0

            for row_number, row in enumerate(rows, start=1):

                try:

                    cols = row.find_elements(
                        By.TAG_NAME,
                        "td"
                    )

                    col_data = [
                        col.text.strip()
                        for col in cols
                    ]

                    if not col_data or not any(col_data):
                        continue

                    # AMBIL NAMA PEKERJAAN
                    raw_job = get_cell_value(
                        col_data,
                        column_indices.get("job")
                    )

                    if (
                        not raw_job
                        or "ganti motor" not in raw_job.lower()
                        or "dial motor" in raw_job.lower()
                    ):

                        raw_job = find_job_text_in_row(
                            col_data
                        )

                    if not raw_job:
                        continue

                    # AMBIL TANGGAL DAN STATUS DONE
                    jadwal_teks = get_cell_value(
                        col_data,
                        column_indices.get("jadwal")
                    )

                    dt_obj = None
                    tgl_terakhir = ""

                    if re.search(
                        r'\(\s*Done\s*\)',
                        jadwal_teks,
                        flags=re.IGNORECASE
                    ):

                        raw_tgl_str = re.sub(
                            r'\(\s*Done\s*\)',
                            '',
                            jadwal_teks,
                            flags=re.IGNORECASE
                        ).strip()

                        dt_obj, tgl_terakhir = universal_date_converter(
                            raw_tgl_str
                        )

                    if not dt_obj:

                        (
                            jadwal_teks,
                            dt_obj,
                            tgl_terakhir
                        ) = find_date_done_in_row(
                            col_data
                        )

                    if not dt_obj:

                        print(
                            f"   Baris {row_number}: "
                            "tanggal Done tidak ditemukan."
                        )

                        continue

                    # FILTER RENTANG TANGGAL
                    if not (
                        date_from <= dt_obj.date() <= date_to
                    ):
                        continue

                    # AMBIL MESIN
                    mesin_teks = get_cell_value(
                        col_data,
                        column_indices.get("mesin")
                    )

                    if not mesin_teks:

                        mesin_teks = find_machine_text_in_row(
                            col_data
                        )

                    nama_mesin = normalize_machine_name(
                        mesin_teks
                    )

                    # AMBIL SUB MESIN
                    sub_mesin_teks = get_cell_value(
                        col_data,
                        column_indices.get("sub_mesin")
                    )

                    sub_mesin = normalize_sub_machine(
                        sub_mesin_teks
                    )

                    # PERSONIL JOB PMP: KOLOM PERSONIL
                    # TIDAK MENGGUNAKAN KOLOM PIC
                    personil_index = column_indices.get(
                        "personil"
                    )

                    personil = get_cell_value(
                        col_data,
                        personil_index
                    )

                    if not personil:

                        print(
                            f"   Baris {row_number}: "
                            "kolom Personil kosong/tidak ditemukan."
                        )

                    # NAMA MOTOR
                    nama_motor = clean_motor_name(
                        raw_job
                    )

                    if not nama_motor:
                        continue

                    # DATA BERKALA
                    keterangan = "Berkala"
                    periode = "180"

                    next_dt = dt_obj + timedelta(days=180)

                    tgl_selanjutnya = next_dt.strftime(
                        "%d-%m-%y"
                    )

                    row_final = [
                        nama_motor,
                        nama_mesin,
                        sub_mesin,
                        tgl_terakhir,
                        personil,
                        keterangan,
                        periode,
                        tgl_selanjutnya
                    ]

                    processed_data.append(
                        row_final
                    )

                    page_added += 1

                    print(
                        f"   [BERKALA] {nama_motor} | "
                        f"{nama_mesin} | {sub_mesin} | "
                        f"{tgl_terakhir} | Personil: {personil}"
                    )

                except Exception as row_error:

                    print(
                        f"   ERROR baris {row_number}:",
                        str(row_error)
                    )

                    continue

            print(
                f"   Data berhasil diambil dari halaman ini: "
                f"{page_added}"
            )

            # CARI TOMBOL HALAMAN BERIKUTNYA
            next_button = None

            next_xpaths = [
                "//a[contains(normalize-space(.), 'Selanjutnya')]",
                "//a[contains(normalize-space(.), 'Next')]",
                "//a[@aria-label='Next']",
                "//li[contains(@class,'next')]/a",
                "//a[contains(@class,'next')]",
                "//button[contains(normalize-space(.), 'Selanjutnya')]",
                "//button[contains(normalize-space(.), 'Next')]"
            ]

            for xpath in next_xpaths:

                try:

                    candidates = driver.find_elements(
                        By.XPATH,
                        xpath
                    )

                    for candidate in candidates:

                        if candidate.is_displayed():

                            next_button = candidate
                            break

                    if next_button:
                        break

                except Exception:
                    continue

            if not next_button:

                print(
                    "   Tombol halaman berikutnya tidak ditemukan."
                )

                print(
                    "   Dianggap sebagai halaman terakhir."
                )

                break

            # PERIKSA TOMBOL DISABLED
            try:

                parent = next_button.find_element(
                    By.XPATH,
                    "./.."
                )

                disabled_text = (
                    str(next_button.get_attribute("class") or "")
                    + " "
                    + str(parent.get_attribute("class") or "")
                    + " "
                    + str(next_button.get_attribute("aria-disabled") or "")
                ).lower()

                if (
                    "disabled" in disabled_text
                    or "true" in disabled_text
                ):

                    print(
                        "   Tombol berikutnya disabled. Selesai."
                    )

                    break

            except Exception:
                pass

            # PINDAH HALAMAN
            try:

                old_url = driver.current_url

                driver.execute_script(
                    "arguments[0].click();",
                    next_button
                )

                time.sleep(3)

                if driver.current_url != old_url:

                    print(
                        "   Berhasil pindah halaman."
                    )

                else:

                    print(
                        "   Tombol diklik, URL tidak berubah."
                    )

                page_num += 1

                column_indices = get_job_table_column_indices(
                    driver
                )

            except Exception as pagination_error:

                print(
                    "   Gagal pindah halaman:",
                    str(pagination_error)
                )

                break

        # RINGKASAN
        print("\n========================================")

        print(
            "TOTAL DATA BERKALA JOB PMP:",
            len(processed_data)
        )

        print("========================================")

        if len(processed_data) == 0:

            print(
                "PERINGATAN: Tidak ada data Job PMP yang lolos filter."
            )

            print(
                "URL terakhir:",
                driver.current_url
            )

            save_debug_screenshot(driver)

        update_progress(
            40,
            f"Pengambilan data Job PMP selesai. "
            f"{len(processed_data)} data berkala ditemukan."
        )

    except Exception as e:

        print("\n[ERROR JOB.PMP.WEB.ID]")

        print(
            type(e).__name__,
            ":",
            str(e)
        )

        update_progress(
            40,
            "Pengambilan data Job PMP mengalami kendala. "
            "Melanjutkan proses berikutnya jika memungkinkan."
        )

        if driver:

            try:

                print(
                    "URL saat error:",
                    driver.current_url
                )

                print(
                    "Isi halaman saat error:",
                    driver.find_element(
                        By.TAG_NAME,
                        "body"
                    ).text[:1500]
                )

                save_debug_screenshot(driver)

            except Exception:
                pass

    finally:

        if driver:

            try:
                driver.quit()
            except Exception:
                pass

    return processed_data


# ============================================================
# 12. SCRAPER KEDUA: APPSHEET
# ============================================================

def normalize_appsheet_column_name(name):

    """
    Menyamakan format nama kolom AppSheet.
    Contoh:
    'PIC', 'pic', ' PIC ' menjadi 'pic'.
    """

    return re.sub(
        r'\s+',
        ' ',
        str(name or '').strip()
    ).lower()


def get_appsheet_value(item, column_name):

    """
    Mengambil nilai berdasarkan nama kolom AppSheet
    tanpa mempermasalahkan kapitalisasi atau spasi.
    """

    target = normalize_appsheet_column_name(
        column_name
    )

    for key, value in item.items():

        if normalize_appsheet_column_name(key) == target:

            return value

    return ""


def run_appsheet_scraper(date_from, date_to):

    print("\n" + "=" * 60)
    print("SCRAPER 2: APPSHEET")
    print("=" * 60)

    if not APPSHEET_APP_ID or not APPSHEET_ACCESS_KEY:

        raise ValueError(
            "APPSHEET_APP_ID atau APPSHEET_ACCESS_KEY belum tersedia."
        )

    update_progress(
        42,
        "Menghubungi API AppSheet untuk mengambil data perbaikan."
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

    total_rows = len(rows)

    print(
        f"2. Total baris diterima dari AppSheet: "
        f"{total_rows}"
    )

    update_progress(
        48,
        f"Data AppSheet diterima. Memeriksa {total_rows} baris."
    )

    # DEBUG NAMA KOLOM
    if rows and isinstance(rows[0], dict):

        print(
            "   Kolom AppSheet yang diterima:",
            list(rows[0].keys())
        )

        if get_appsheet_value(rows[0], "PIC") == "":

            print(
                "   PERINGATAN: Kolom PIC tidak ditemukan "
                "atau nilainya kosong pada baris pertama."
            )

        else:

            print(
                "   Sumber personil AppSheet: kolom PIC."
            )

    processed_data = []

    # Progress AppSheet berada pada rentang 48% sampai 75%.
    # Perhitungannya berdasarkan jumlah baris yang diperiksa.
    last_reported_progress = 48

    for index, item in enumerate(rows, start=1):

        try:

            if not isinstance(item, dict):
                continue

            detail_pekerjaan = str(
                get_appsheet_value(
                    item,
                    "Detil Pekerjaan"
                ) or ""
            ).strip()

            if SEARCH_KEYWORD.lower() not in detail_pekerjaan.lower():
                continue

            raw_date = get_appsheet_value(
                item,
                "Tanggal"
            )

            tanggal_obj = parse_appsheet_date(
                raw_date
            )

            if tanggal_obj is None:
                continue

            if not (
                date_from <= tanggal_obj <= date_to
            ):
                continue

            nama_motor = extract_motor_from_detail(
                detail_pekerjaan
            )

            if not nama_motor:

                print(
                    "   Melewati data karena nama motor "
                    "tidak ditemukan setelah Ganti Motor."
                )

                continue

            mesin = str(
                get_appsheet_value(
                    item,
                    "Mesin"
                ) or ""
            ).strip()

            nama_mesin = normalize_machine_name(
                mesin
            )

            sub_mesin = normalize_sub_machine(
                get_appsheet_value(
                    item,
                    "Sub Mesin"
                )
            )

            # PERSONIL APPSHEET: AMBIL DARI KOLOM PIC
            # BUKAN DARI KOLOM PERSONIL

            personil = str(
                get_appsheet_value(
                    item,
                    "PIC"
                ) or ""
            ).strip()

            if not personil:

                print(
                    f"   PERINGATAN: PIC kosong untuk pekerjaan "
                    f"{nama_motor}."
                )

            tgl_terakhir = tanggal_obj.strftime(
                "%d-%m-%y"
            )

            keterangan = "Perbaikan"
            periode = "180"

            next_date = tanggal_obj + timedelta(days=180)

            tgl_selanjutnya = next_date.strftime(
                "%d-%m-%y"
            )

            row_final = [
                nama_motor,
                nama_mesin,
                sub_mesin,
                tgl_terakhir,
                personil,
                keterangan,
                periode,
                tgl_selanjutnya
            ]

            processed_data.append(
                row_final
            )

            print(
                f"   [PERBAIKAN] {nama_motor} | "
                f"{nama_mesin} | {sub_mesin} | "
                f"{tgl_terakhir} | Personil (PIC): {personil}"
            )

        except Exception as row_error:

            print(
                f"   ERROR baris AppSheet {index}:",
                str(row_error)
            )

            continue

        finally:

            # Kirim progress secara berkala agar tidak terlalu
            # sering melakukan request ke Apps Script.
            if total_rows > 0:

                current_progress = (
                    48 + int((index / total_rows) * 27)
                )

                should_report = (
                    current_progress != last_reported_progress
                    or index == total_rows
                )

                if should_report:

                    update_progress(
                        current_progress,
                        f"Memeriksa data AppSheet: "
                        f"{index}/{total_rows} baris."
                    )

                    last_reported_progress = current_progress

    print(
        f"3. TOTAL DATA PERBAIKAN: "
        f"{len(processed_data)}"
    )

    update_progress(
        75,
        f"Pemeriksaan AppSheet selesai. "
        f"{len(processed_data)} data perbaikan ditemukan."
    )

    return processed_data


# ============================================================
# 13. GABUNGKAN DAN KIRIM KE GOOGLE SHEETS
# ============================================================

def send_to_google_sheets(all_data):

    print("\n" + "=" * 60)
    print("MENGIRIM DATA KE GOOGLE SHEETS")
    print("=" * 60)

    if not all_data:

    print(
        "Tidak ada data dari kedua sumber."
    )

    print(
        "Mengirim data kosong untuk membersihkan Sheet1."
    )

    update_progress(
        85,
        "Tidak ada data. Membersihkan Sheet1."
    )

    print(
        f"Total data gabungan: {len(all_data)}"
    )

    count_berkala = sum(
        1 for row in all_data
        if len(row) > 5 and row[5] == "Berkala"
    )

    count_perbaikan = sum(
        1 for row in all_data
        if len(row) > 5 and row[5] == "Perbaikan"
    )

    print(
        f"Data Berkala   : {count_berkala}"
    )

    print(
        f"Data Perbaikan : {count_perbaikan}"
    )

    update_progress(
        85,
        f"Data berhasil digabungkan. Total {len(all_data)} baris."
    )

    print(
        "Mengirim data ke Google Sheets..."
    )

    update_progress(
        90,
        "Mengirim data ke Google Sheets."
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

    update_progress(
        97,
        "Data berhasil dikirim ke Google Sheets."
    )


# ============================================================
# 14. PROGRAM UTAMA
# ============================================================

def run_scraper():

    print("\n")

    print("=" * 60)
    print("SISTEM SCRAPER GABUNGAN MOTOR PMP")
    print("=" * 60)

    print(
        "RUN ID:",
        RUN_ID
    )

    try:

        update_progress(
            1,
            "Scraper dimulai. Menyiapkan proses pengambilan data."
        )

        date_from, date_to = get_date_range()

        update_progress(
            3,
            f"Rentang tanggal: {date_from} sampai {date_to}."
        )

        # ----------------------------------------------------
        # SCRAPER JOB PMP
        # ----------------------------------------------------

        berkala_data = run_job_scraper(
            date_from,
            date_to
        )

        # ----------------------------------------------------
        # SCRAPER APPSHEET
        # ----------------------------------------------------

        perbaikan_data = run_appsheet_scraper(
            date_from,
            date_to
        )

        
        # ----------------------------------------------------
        # GABUNGKAN
        # ----------------------------------------------------

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

        update_progress(
            80,
            f"Penggabungan data selesai. "
            f"Total {len(combined_data)} data."
        )

        # PERINGATAN
        if len(berkala_data) == 0:

            print("\nPERINGATAN:")

            print(
                "Data dari Job PMP tidak berhasil diperoleh."
            )

            print(
                "Periksa log login, tabel, header, dan filter tanggal."
            )

        # ----------------------------------------------------
        # PERIKSA JIKA TIDAK ADA DATA
        # ----------------------------------------------------

        if not combined_data:

            print("\n")
            print("=" * 60)
            print("TIDAK ADA PENGGANTIAN MOTOR")
            print("=" * 60)

            print(
                f"Tidak ditemukan data pada rentang "
                f"{date_from} sampai {date_to}."
            )

            update_progress(
                100,
                (
                    f"Tidak ditemukan data Penggantian Motor "
                    f"pada tanggal {date_from} sampai {date_to}."
                ),
                status="no_data"
            )
        # ----------------------------------------------------
        # KIRIM DATA
        # ----------------------------------------------------

        send_to_google_sheets(
            combined_data
        )

        print("\n")
        print("=" * 60)
        print("SELURUH PROSES SELESAI")
        print("=" * 60)

        if combined_data:

            update_progress(
                100,
                (
                    f"Scraper selesai. "
                    f"Berhasil memproses {len(combined_data)} data."
                ),
                status="completed"
            )

        else:

            update_progress(
                100,
                (
                    f"Tidak ditemukan data Penggantian Motor "
                    f"pada tanggal {date_from} sampai {date_to}."
                ),
                status="no_data"
            )

    except Exception as e:

        error_message = (
            f"{type(e).__name__}: {str(e)}"
        )

        print("\n")
        print("=" * 60)
        print("SCRAPER GAGAL")
        print("=" * 60)
        print(error_message)

        update_progress(
            _last_progress if _last_progress >= 0 else 0,
            "Scraper gagal: " + error_message,
            status="failed",
            error=error_message
        )

        # Lempar kembali error agar GitHub Actions
        # juga mencatat workflow sebagai gagal.
        raise


# ============================================================
# 15. EKSEKUSI PROGRAM
# ============================================================

if __name__ == "__main__":

    run_scraper()
