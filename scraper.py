
import os
import re
import time
import logging
import requests

from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException
)

from webdriver_manager.chrome import ChromeDriverManager


# ============================================================
# 1. KONFIGURASI UTAMA
# ============================================================

LOGIN_URL = "http://job.pmp.web.id/login/"
DASHBOARD_URL = "http://job.pmp.web.id/dashboard/"

APPS_SCRIPT_URL = (
    "https://script.google.com/macros/s/"
    "AKfycbyaKVBoR7ictxN1pYu0LAiaHARvltJlwlqV1wDsoz96_enjB7pi6bqAWLkHx-JTEnrx/exec"
)

APPSHEET_APP_ID = os.getenv("APPSHEET_APP_ID", "")
APPSHEET_ACCESS_KEY = os.getenv("APPSHEET_ACCESS_KEY", "")
APPSHEET_TABLE = "Trial"

SCRAPER_USERNAME = os.getenv("SCRAPER_USERNAME", "")
SCRAPER_PASSWORD = os.getenv("SCRAPER_PASSWORD", "")

INPUT_DATE_FROM = os.getenv("INPUT_DATE_FROM", "")
INPUT_DATE_TO = os.getenv("INPUT_DATE_TO", "")

SEARCH_KEYWORD = "GANTI MOTOR"

TIMEZONE = ZoneInfo("Asia/Jakarta")

WAIT_TIMEOUT = 30
MAX_PAGES = 100

PERIOD_DEFAULT = "120"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger("SCRAPER")


# ============================================================
# 2. PROGRES SCRAPER
# ============================================================

def report_progress(percent, stage, detail="", status="running"):
    """
    Mengirim progres ke Google Apps Script.

    Kegagalan pengiriman progres tidak boleh menghentikan scraper.
    """

    percent = max(0, min(100, int(percent)))

    payload = {
        "action": "update_scraper_progress",
        "percent": percent,
        "stage": str(stage),
        "detail": str(detail),
        "status": str(status),
        "updated_at": datetime.now(TIMEZONE).isoformat()
    }

    try:
        requests.post(
            APPS_SCRIPT_URL,
            json=payload,
            timeout=15
        )

    except Exception as error:
        logger.warning(
            "Gagal mengirim progres: %s",
            error
        )


# ============================================================
# 3. RENTANG TANGGAL
# ============================================================

def get_date_range():

    today = datetime.now(TIMEZONE).date()

    if INPUT_DATE_FROM and INPUT_DATE_TO:

        date_from = parse_date(INPUT_DATE_FROM)
        date_to = parse_date(INPUT_DATE_TO)

        if date_from > date_to:
            raise ValueError(
                "Tanggal awal tidak boleh lebih besar "
                "dari tanggal akhir."
            )

        return date_from, date_to

    date_from = today - timedelta(days=30)
    date_to = today

    return date_from, date_to


def parse_date(value):

    if isinstance(value, date):
        return value

    value = str(value).strip()

    formats = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
        "%d-%m-%y",
        "%d/%m/%y"
    ]

    for fmt in formats:

        try:
            return datetime.strptime(value, fmt).date()

        except ValueError:
            pass

    raise ValueError(
        "Format tanggal tidak dikenali: " + value
    )


def universal_date_converter(value):

    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    value = str(value).strip()

    if not value:
        return None

    formats = [
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%d %B %Y",
        "%d %b %Y",
        "%Y/%m/%d",
        "%d-%m-%y",
        "%d/%m/%y"
    ]

    for fmt in formats:

        try:
            return datetime.strptime(value, fmt).date()

        except ValueError:
            pass

    # Format tanggal Indonesia, misalnya 16 Nov 2026.
    months = {
        "JANUARI": 1,
        "FEBRUARI": 2,
        "MARET": 3,
        "APRIL": 4,
        "MEI": 5,
        "JUNI": 6,
        "JULI": 7,
        "AGUSTUS": 8,
        "SEPTEMBER": 9,
        "OKTOBER": 10,
        "NOVEMBER": 11,
        "DESEMBER": 12,
        "JAN": 1,
        "FEB": 2,
        "MAR": 3,
        "APR": 4,
        "JUN": 6,
        "JUL": 7,
        "AGU": 8,
        "AGS": 8,
        "SEP": 9,
        "OKT": 10,
        "NOV": 11,
        "DES": 12
    }

    match = re.search(
        r"(\d{1,2})\s+([A-Z]+)\s+(\d{4})",
        value.upper()
    )

    if match:

        day = int(match.group(1))
        month_name = match.group(2)
        year = int(match.group(3))

        month = months.get(month_name)

        if month:
            return date(year, month, day)

    return None


def format_date(value):

    parsed = universal_date_converter(value)

    if not parsed:
        return ""

    return parsed.strftime("%d-%m-%Y")


# ============================================================
# 4. NORMALISASI TEKS DAN MESIN
# ============================================================

def clean_text(value):

    value = str(value or "").strip()

    value = re.sub(r"\s+", " ", value)

    return value


def normalize_machine_name(value):

    value = clean_text(value).upper()

    match = re.search(
        r"\bFS\s*0*(\d+)\b",
        value
    )

    if not match:
        return value

    return "FS " + str(int(match.group(1)))


def normalize_sub_machine(value):

    return clean_text(value).upper()


def clean_motor_name(value):

    value = clean_text(value).upper()

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


def extract_motor_from_detail(detail):

    """
    Mengambil nama motor dari teks pekerjaan setelah
    kata Ganti Motor.

    Contoh:
    Ganti Motor WINCH UTARA DM
    Hasil: WINCH UTARA DM
    """

    detail = clean_text(detail).upper()

    if not detail:
        return ""

    match = re.search(
        r"GANTI\s+MOTOR\s*(.*)",
        detail,
        flags=re.IGNORECASE
    )

    if not match:
        return ""

    motor = match.group(1).strip()

    # Buang informasi tambahan setelah pemisah umum.
    motor = re.split(
        r"\s*(?:\||;|\n)\s*",
        motor
    )[0]

    return clean_motor_name(motor)


# ============================================================
# 5. PEMBANTU SELENIUM
# ============================================================

def create_driver():

    options = Options()

    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-notifications")
    options.add_argument("--lang=id-ID")

    options.add_experimental_option(
        "prefs",
        {
            "profile.default_content_setting_values.notifications": 2
        }
    )

    service = Service(
        ChromeDriverManager().install()
    )

    return webdriver.Chrome(
        service=service,
        options=options
    )


def find_first_element(driver, selectors):

    for by, selector in selectors:

        try:
            element = driver.find_element(
                by,
                selector
            )

            if element:
                return element

        except NoSuchElementException:
            continue

    return None


def login_job_pmp(driver):

    logger.info("Membuka halaman login Job PMP...")

    driver.get(LOGIN_URL)

    wait = WebDriverWait(
        driver,
        WAIT_TIMEOUT
    )

    wait.until(
        EC.presence_of_element_located(
            (By.TAG_NAME, "body")
        )
    )

    username_input = find_first_element(
        driver,
        [
            (By.NAME, "username"),
            (By.ID, "username"),
            (By.NAME, "email"),
            (By.ID, "email"),
            (By.CSS_SELECTOR, "input[type='text']"),
            (By.CSS_SELECTOR, "input[type='email']")
        ]
    )

    password_input = find_first_element(
        driver,
        [
            (By.NAME, "password"),
            (By.ID, "password"),
            (By.CSS_SELECTOR, "input[type='password']")
        ]
    )

    if not username_input or not password_input:

        raise Exception(
            "Input username/password tidak ditemukan."
        )

    if not SCRAPER_USERNAME or not SCRAPER_PASSWORD:

        raise Exception(
            "SCRAPER_USERNAME atau SCRAPER_PASSWORD "
            "belum diatur pada environment."
        )

    username_input.clear()
    username_input.send_keys(SCRAPER_USERNAME)

    password_input.clear()
    password_input.send_keys(SCRAPER_PASSWORD)

    submit_button = find_first_element(
        driver,
        [
            (By.CSS_SELECTOR, "button[type='submit']"),
            (By.CSS_SELECTOR, "input[type='submit']"),
            (By.XPATH, "//button[contains(., 'Login')]"),
            (By.XPATH, "//button[contains(., 'Masuk')]")
        ]
    )

    if submit_button:

        submit_button.click()

    else:

        password_input.submit()

    time.sleep(3)

    logger.info(
        "Proses login selesai. URL sekarang: %s",
        driver.current_url
    )


# ============================================================
# 6. DETEKSI KOLOM TABEL JOB PMP
# ============================================================

def normalize_header(value):

    value = clean_text(value).lower()

    value = re.sub(
        r"[^a-z0-9 ]",
        " ",
        value
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


def get_job_table_column_indices(driver):
    """
    Mendeteksi indeks kolom berdasarkan header tabel.

    PENTING:
    Kolom personil hanya boleh berasal dari header 'Personil'.
    Header 'PIC' tidak pernah dianggap sebagai Personil.
    """

    tables = driver.find_elements(
        By.TAG_NAME,
        "table"
    )

    selected_table = None
    selected_headers = []

    for table in tables:

        try:

            header_elements = table.find_elements(
                By.CSS_SELECTOR,
                "thead tr th"
            )

            if not header_elements:

                header_elements = table.find_elements(
                    By.CSS_SELECTOR,
                    "tr:first-child th, tr:first-child td"
                )

            headers = [
                normalize_header(element.text)
                for element in header_elements
            ]

            if not headers:
                continue

            if "personil" in headers:

                selected_table = table
                selected_headers = headers
                break

        except StaleElementReferenceException:
            continue

    if selected_table is None:

        raise Exception(
            "Tabel Job PMP dengan header 'Personil' "
            "tidak ditemukan. Scraper tidak akan "
            "mengambil data dari kolom PIC."
        )

    logger.info(
        "Header tabel Job PMP: %s",
        selected_headers
    )

    def find_column(*names):

        for index, header in enumerate(selected_headers):

            if header in names:
                return index

        return None

    indices = {
        "job": find_column(
            "pekerjaan",
            "job",
            "nama pekerjaan",
            "detil pekerjaan",
            "detail pekerjaan"
        ),

        # HANYA header Personil.
        "personil": find_column("personil"),

        "mesin": find_column(
            "mesin",
            "nama mesin"
        ),

        "jadwal": find_column(
            "jadwal",
            "tanggal",
            "tgl",
            "tanggal pekerjaan"
        ),

        "sub_mesin": find_column(
            "sub mesin",
            "submesin"
        ),

        "status": find_column(
            "status"
        )
    }

    if indices["personil"] is None:

        raise Exception(
            "Header 'Personil' tidak ditemukan. "
            "Kolom PIC tidak akan digunakan sebagai pengganti."
        )

    if indices["job"] is None:

        raise Exception(
            "Kolom pekerjaan tidak ditemukan pada tabel Job PMP."
        )

    if indices["mesin"] is None:

        raise Exception(
            "Kolom Mesin tidak ditemukan pada tabel Job PMP."
        )

    logger.info(
        "Indeks kolom Job PMP: %s",
        indices
    )

    return selected_table, indices


def get_cell_value(cells, index):

    if index is None:
        return ""

    if index < 0 or index >= len(cells):
        return ""

    return clean_text(cells[index].text)


# ============================================================
# 7. DETEKSI PAGINATION JOB PMP
# ============================================================

def get_next_page_button(driver):

    selectors = [
        (By.CSS_SELECTOR, "a[rel='next']"),
        (By.CSS_SELECTOR, "li.next a"),
        (By.CSS_SELECTOR, ".pagination .next a"),
        (By.XPATH, "//a[contains(., 'Next')]"),
        (By.XPATH, "//a[contains(., 'Berikutnya')]"),
        (By.XPATH, "//button[contains(., 'Next')]")
    ]

    for by, selector in selectors:

        try:

            element = driver.find_element(
                by,
                selector
            )

            if element.is_displayed():

                classes = (
                    element.get_attribute("class") or ""
                ).lower()

                parent_classes = ""

                try:
                    parent_classes = (
                        element.find_element(
                            By.XPATH,
                            ".."
                        ).get_attribute("class") or ""
                    ).lower()

                except Exception:
                    pass

                if (
                    "disabled" in classes
                    or "disabled" in parent_classes
                ):
                    return None

                return element

        except NoSuchElementException:
            continue

    return None


def click_next_page(driver):

    next_button = get_next_page_button(driver)

    if not next_button:
        return False

    try:

        old_url = driver.current_url

        driver.execute_script(
            "arguments[0].click();",
            next_button
        )

        time.sleep(2)

        if driver.current_url != old_url:
            return True

        return True

    except Exception:

        return False


# ============================================================
# 8. SCRAPER JOB PMP
# ============================================================

def run_job_scraper(date_from, date_to):

    logger.info("=" * 60)
    logger.info("MEMULAI SCRAPER JOB PMP")
    logger.info("=" * 60)

    report_progress(
        5,
        "Job PMP",
        "Mempersiapkan browser dan login"
    )

    driver = None

    all_data = []

    try:

        driver = create_driver()

        login_job_pmp(driver)

        report_progress(
            10,
            "Job PMP",
            "Login berhasil, membuka halaman pekerjaan"
        )

        driver.get(DASHBOARD_URL)

        wait = WebDriverWait(
            driver,
            WAIT_TIMEOUT
        )

        wait.until(
            EC.presence_of_element_located(
                (By.TAG_NAME, "body")
            )
        )

        time.sleep(3)

        seen_pages = set()

        page_number = 0

        while page_number < MAX_PAGES:

            page_number += 1

            logger.info(
                "Memproses halaman Job PMP ke-%s",
                page_number
            )

            page_signature = driver.current_url

            if page_signature in seen_pages:
                logger.info(
                    "Halaman berulang terdeteksi, pagination dihentikan."
                )
                break

            seen_pages.add(page_signature)

            table, column_indices = (
                get_job_table_column_indices(driver)
            )

            rows = table.find_elements(
                By.CSS_SELECTOR,
                "tbody tr"
            )

            if not rows:

                rows = table.find_elements(
                    By.CSS_SELECTOR,
                    "tr"
                )[1:]

            for row_element in rows:

                try:

                    cells = row_element.find_elements(
                        By.CSS_SELECTOR,
                        "td"
                    )

                    if not cells:
                        continue

                    row_text = clean_text(
                        row_element.text
                    ).upper()

                    # Hanya pekerjaan selesai.
                    if not re.search(
                        r"\bDONE\b",
                        row_text
                    ):
                        continue

                    job_text = get_cell_value(
                        cells,
                        column_indices["job"]
                    )

                    if SEARCH_KEYWORD not in job_text.upper():
                        continue

                    # Ambil Personil hanya dari kolom Personil.
                    personil = get_cell_value(
                        cells,
                        column_indices["personil"]
                    )

                    mesin = get_cell_value(
                        cells,
                        column_indices["mesin"]
                    )

                    jadwal = get_cell_value(
                        cells,
                        column_indices["jadwal"]
                    )

                    sub_mesin = get_cell_value(
                        cells,
                        column_indices["sub_mesin"]
                    )

                    if not personil:
                        logger.warning(
                            "Personil kosong pada baris: %s",
                            row_text
                        )

                    tanggal = universal_date_converter(
                        jadwal
                    )

                    if not tanggal:
                        logger.warning(
                            "Tanggal tidak terbaca: %s",
                            jadwal
                        )
                        continue

                    if not (
                        date_from <= tanggal <= date_to
                    ):
                        continue

                    motor = extract_motor_from_detail(
                        job_text
                    )

                    if not motor:
                        logger.warning(
                            "Nama motor tidak berhasil diekstrak: %s",
                            job_text
                        )
                        continue

                    mesin = normalize_machine_name(
                        mesin
                    )

                    sub_mesin = normalize_sub_machine(
                        sub_mesin
                    )

                    row_data = [
                        motor,
                        mesin,
                        sub_mesin,
                        tanggal.strftime("%d-%m-%Y"),
                        personil.upper(),
                        "BERKALA",
                        PERIOD_DEFAULT,
                        (
                            tanggal + timedelta(
                                days=int(PERIOD_DEFAULT)
                            )
                        ).strftime("%d-%m-%Y")
                    ]

                    all_data.append(row_data)

                except StaleElementReferenceException:
                    continue

                except Exception as error:

                    logger.warning(
                        "Baris Job PMP dilewati: %s",
                        error
                    )

            logger.info(
                "Halaman %s selesai. Total data Job PMP: %s",
                page_number,
                len(all_data)
            )

            # Progres Job PMP dibuat bertahap.
            # Persentase ini merupakan progres tahap,
            # bukan jumlah halaman keseluruhan.
            progress = min(
                40,
                10 + page_number * 3
            )

            report_progress(
                progress,
                "Job PMP",
                (
                    "Halaman diproses: "
                    + str(page_number)
                    + " | Data ditemukan: "
                    + str(len(all_data))
                )
            )

            if not click_next_page(driver):
                break

        logger.info(
            "Scraper Job PMP selesai. Total: %s",
            len(all_data)
        )

        report_progress(
            42,
            "Job PMP",
            "Selesai mengambil data Job PMP"
        )

        return all_data

    except Exception as error:

        logger.exception(
            "Scraper Job PMP gagal: %s",
            error
        )

        raise

    finally:

        if driver:

            try:
                driver.quit()

            except Exception:
                pass


# ============================================================
# 9. APPSHEET
# ============================================================

def parse_appsheet_date(value):

    if value is None:
        return None

    if isinstance(value, dict):
        value = value.get("Date", value.get("date", ""))

    return universal_date_converter(value)


def get_appsheet_rows():

    if not APPSHEET_APP_ID:
        raise Exception(
            "APPSHEET_APP_ID belum diatur."
        )

    if not APPSHEET_ACCESS_KEY:
        raise Exception(
            "APPSHEET_ACCESS_KEY belum diatur."
        )

    url = (
        "https://api.appsheet.com/api/v2/apps/"
        + APPSHEET_APP_ID
        + "/tables/"
        + APPSHEET_TABLE
        + "/Action"
    )

    payload = {
        "Action": "Find",
        "Properties": {
            "Locale": "id-ID",
            "Timezone": "Asia/Jakarta"
        },
        "Rows": []
    }

    headers = {
        "ApplicationAccessKey": APPSHEET_ACCESS_KEY,
        "Content-Type": "application/json"
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=60
    )

    response.raise_for_status()

    result = response.json()

    if not isinstance(result, list):

        raise Exception(
            "Respons AppSheet bukan berupa list data: "
            + str(result)
        )

    return result


def run_appsheet_scraper(date_from, date_to):

    logger.info("=" * 60)
    logger.info("MEMULAI SCRAPER APPSHEET")
    logger.info("=" * 60)

    report_progress(
        45,
        "AppSheet",
        "Mengambil data dari AppSheet"
    )

    rows = get_appsheet_rows()

    all_data = []

    total = len(rows)

    logger.info(
        "Jumlah baris AppSheet: %s",
        total
    )

    for index, row in enumerate(rows, start=1):

        try:

            # Hanya menggunakan Detil Pekerjaan.
            detail = clean_text(
                row.get("Detil Pekerjaan", "")
            )

            if SEARCH_KEYWORD not in detail.upper():
                continue

            # Motor wajib diambil dari teks setelah Ganti Motor.
            motor = extract_motor_from_detail(
                detail
            )

            if not motor:
                continue

            tanggal_value = row.get("Tanggal", "")

            tanggal = parse_appsheet_date(
                tanggal_value
            )

            if not tanggal:
                continue

            if not (
                date_from <= tanggal <= date_to
            ):
                continue

            mesin = normalize_machine_name(
                row.get("Mesin", "")
            )

            sub_mesin = normalize_sub_machine(
                row.get("Sub Mesin", "")
            )

            personil = clean_text(
                row.get(
                    "PIC",
                    row.get("Nama", "")
                )
            ).upper()

            row_data = [
                motor,
                mesin,
                sub_mesin,
                tanggal.strftime("%d-%m-%Y"),
                personil,
                "PERBAIKAN",
                PERIOD_DEFAULT,
                (
                    tanggal + timedelta(
                        days=int(PERIOD_DEFAULT)
                    )
                ).strftime("%d-%m-%Y")
            ]

            all_data.append(row_data)

        except Exception as error:

            logger.warning(
                "Baris AppSheet ke-%s dilewati: %s",
                index,
                error
            )

        if total > 0 and index % 20 == 0:

            progress = 45 + int(
                (index / total) * 25
            )

            report_progress(
                min(progress, 70),
                "AppSheet",
                (
                    "Memproses "
                    + str(index)
                    + " dari "
                    + str(total)
                    + " baris"
                )
            )

    logger.info(
        "Scraper AppSheet selesai. Total: %s",
        len(all_data)
    )

    report_progress(
        72,
        "AppSheet",
        (
            "Selesai mengambil "
            + str(len(all_data))
            + " data AppSheet"
        )
    )

    return all_data


# ============================================================
# 10. SINKRONISASI GOOGLE SHEETS
# ============================================================

def send_to_google_sheets(all_data):

    logger.info("=" * 60)
    logger.info("MENGIRIM DATA KE GOOGLE SHEETS")
    logger.info("=" * 60)

    berkala_count = sum(
        1 for row in all_data
        if str(row[5]).upper() == "BERKALA"
    )

    perbaikan_count = sum(
        1 for row in all_data
        if str(row[5]).upper() == "PERBAIKAN"
    )

    payload = all_data

    report_progress(
        85,
        "Google Sheets",
        "Mengirim data ke Google Sheets"
    )

    response = requests.post(
        APPS_SCRIPT_URL,
        json=payload,
        timeout=180
    )

    response.raise_for_status()

    result = response.text

    logger.info(
        "Respons Google Apps Script: %s",
        result
    )

    logger.info(
        "Total Berkala: %s",
        berkala_count
    )

    logger.info(
        "Total Perbaikan: %s",
        perbaikan_count
    )

    return {
        "response": result,
        "total": len(all_data),
        "berkala": berkala_count,
        "perbaikan": perbaikan_count
    }


# ============================================================
# 11. PROSES UTAMA
# ============================================================

def run_scraper():

    start_time = time.time()

    try:

        report_progress(
            0,
            "Persiapan",
            "Scraper sedang dimulai"
        )

        date_from, date_to = get_date_range()

        logger.info(
            "Rentang tanggal: %s sampai %s",
            date_from,
            date_to
        )

        # ----------------------------------------------------
        # JOB PMP
        # ----------------------------------------------------

        job_data = run_job_scraper(
            date_from,
            date_to
        )

        # ----------------------------------------------------
        # APPSHEET
        # ----------------------------------------------------

        appsheet_data = run_appsheet_scraper(
            date_from,
            date_to
        )

        # ----------------------------------------------------
        # GABUNG DATA
        # ----------------------------------------------------

        report_progress(
            75,
            "Penggabungan",
            "Menggabungkan data Job PMP dan AppSheet"
        )

        all_data = (
            job_data + appsheet_data
        )

        logger.info(
            "Total data Job PMP: %s",
            len(job_data)
        )

        logger.info(
            "Total data AppSheet: %s",
            len(appsheet_data)
        )

        logger.info(
            "Total gabungan: %s",
            len(all_data)
        )

        # ----------------------------------------------------
        # HAPUS DUPLIKAT IDENTIK
        # ----------------------------------------------------

        unique_data = []
        seen = set()

        for row in all_data:

            key = tuple(
                str(value).strip().upper()
                for value in row
            )

            if key in seen:
                continue

            seen.add(key)
            unique_data.append(row)

        all_data = unique_data

        logger.info(
            "Total setelah menghapus duplikat identik: %s",
            len(all_data)
        )

        # ----------------------------------------------------
        # KIRIM KE GOOGLE SHEETS
        # ----------------------------------------------------

        result = send_to_google_sheets(
            all_data
        )

        elapsed = round(
            time.time() - start_time,
            2
        )

        logger.info("=" * 60)
        logger.info("SCRAPER BERHASIL")
        logger.info("Total data: %s", result["total"])
        logger.info("Berkala: %s", result["berkala"])
        logger.info("Perbaikan: %s", result["perbaikan"])
        logger.info("Waktu: %s detik", elapsed)
        logger.info("=" * 60)

        report_progress(
            100,
            "Selesai",
            (
                "Scraper berhasil. Total "
                + str(result["total"])
                + " data. Berkala: "
                + str(result["berkala"])
                + ", Perbaikan: "
                + str(result["perbaikan"])
            ),
            "completed"
        )

        return result

    except Exception as error:

        logger.exception(
            "SCRAPER GAGAL: %s",
            error
        )

        report_progress(
            100,
            "Gagal",
            str(error),
            "failed"
        )

        raise


# ============================================================
# 12. EKSEKUSI
# ============================================================

if __name__ == "__main__":

    run_scraper()
