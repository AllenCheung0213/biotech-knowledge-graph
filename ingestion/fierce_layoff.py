# ingestion/fierce_layoff.py

import re
import unicodedata
from dateutil.parser import parse
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from db.session import SessionLocal
from db.models import Company, LayoffEvent
from nlp.layoff_extractor import extract_layoff

def clean_text(text):
    if isinstance(text, str):
        text = unicodedata.normalize("NFKD", text)
        text = re.sub(r'[^\x00-\x7F]+', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
    return text

def clean_company(company):
    if isinstance(company, str):
        company = company.strip()
        company = re.sub(r':$', '', company)
    return company

def clean_description(desc):
    if isinstance(desc, str):
        desc = re.sub(r'^\w+\.\s*\d+\s*-\s*[^:]+:\s+', '', desc)
        desc = re.sub(
            r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d+\s*-\s+[^:\n]+:\s*',
            '',
            desc
        )
        desc = re.sub(r'\s*(Story|Release)\.?$', '', desc, flags=re.IGNORECASE)
        desc = desc.replace('""', '"').strip(' ":\n')
    return desc

def fetch_and_store_layoffs():
    # -- set up headless Selenium Chrome driver --
    chrome_opts = Options()
    chrome_opts.add_argument("--headless")
    chrome_opts.add_argument("--no-sandbox")
    chrome_opts.add_argument("--disable-dev-shm-usage")
    chrome_opts.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_opts
    )

    url = "https://www.fiercebiotech.com/biotech/fierce-biotech-layoff-tracker-2025"
    driver.get(url)
    driver.implicitly_wait(10)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    driver.quit()

    year = url.split('-')[-1]
    session = SessionLocal()

    try:
        for header in soup.find_all(['h2', 'h3']):
            for sibling in header.find_next_siblings():
                if sibling.name in ['h2', 'h3']:
                    break

                if sibling.name == 'p' and sibling.strong:
                    strong_text = sibling.strong.text.strip(':').strip()
                    parts = strong_text.split('-', 1)
                    if len(parts) != 2:
                        continue

                    # Parse date and company
                    raw_date = clean_text(parts[0].strip())
                    company_name = clean_company(clean_text(parts[1].strip()))
                    try:
                        parsed_date = parse(f"{raw_date} {year}").date()
                    except ValueError:
                        parsed_date = parse(f"January 1 {year}").date()

                    # Extract description & URL
                    full_text = sibling.get_text(separator=' ', strip=True)
                    desc_raw = full_text.replace(strong_text, '', 1).lstrip(':').strip()
                    description = clean_description(clean_text(desc_raw))
                    link_tag = sibling.find('a')
                    source_url = clean_text(link_tag['href']) if link_tag else None

                    # Idempotency: skip if already stored
                    existing = session.query(LayoffEvent).filter_by(
                        company_id=None,  # temporary placeholder
                        date=parsed_date,
                        source_url=source_url
                    ).first()
                    # We can't filter by company_id yet since company may not exist; do a subquery later

                    # Upsert Company
                    company = session.query(Company).filter_by(name=company_name).first()
                    if not company:
                        company = Company(name=company_name)
                        session.add(company)
                        session.commit()

                    # Now re-check existence using real company_id
                    existing = session.query(LayoffEvent).filter_by(
                        company_id=company.company_id,
                        date=parsed_date,
                        source_url=source_url
                    ).first()
                    if existing:
                        continue

                    # Use LLM to extract layoffs; fallback to regex if missing
                    try:
                        info = extract_layoff(description)
                        num_laid_off = info.num_laid_off
                        percent_laid_off = info.percent
                    except Exception:
                        num_laid_off = None
                        percent_laid_off = None

                    # Fallback numeric parse
                    if num_laid_off is None:
                        m = re.search(r'(\d{1,4})(?=\s*(?:people|employees|\b))', description)
                        if m:
                            num_laid_off = int(m.group(1))
                    if percent_laid_off is None:
                        m = re.search(r'(\d+(?:\.\d+)?)\s*%', description)
                        if m:
                            percent_laid_off = float(m.group(1))

                    # Insert LayoffEvent
                    event = LayoffEvent(
                        company_id=company.company_id,
                        date=parsed_date,
                        num_laid_off=num_laid_off,
                        percent_laid_off=percent_laid_off,
                        description=description,
                        source_url=source_url
                    )
                    session.add(event)
                    session.commit()

    finally:
        session.close()

if __name__ == "__main__":
    fetch_and_store_layoffs()
