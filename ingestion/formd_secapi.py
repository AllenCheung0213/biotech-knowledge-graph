import os
from datetime import datetime
from sec_api import QueryApi, ExtractorApi
from db.session import SessionLocal
from db.models import Company, FundingRound
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv

load_dotenv()
SEC_API_KEY = os.getenv("SEC_API_KEY")

# Initialize clients
query_api     = QueryApi(api_key=SEC_API_KEY)
extractor_api = ExtractorApi(api_key=SEC_API_KEY)

def ingest_formd_via_secapi(start_date: str, end_date: str):
    """
    Pull all Form D filings between start_date and end_date (YYYY-MM-DD),
    extract amount & first-sale date, and insert FundingRound records.
    """
    # Build the search query
    query = {
      "query": { 
        "query_string": {
          "query": f'formType:"D" AND filedAt:[{start_date} TO {end_date}]'
        }
      },
      "from": "0",
      "size": "100",    # adjust upward if you need more
      "sort": [{"filedAt":"desc"}]
    }

    print(f"→ Querying SEC EDGAR for Form D between {start_date} and {end_date}")
    filings = query_api.get_filings(query).get("filings", [])

    session = SessionLocal()
    for f in filings:
        issuer_name = f.get("nameOfIssuer") or f.get("issuerNameExp")
        detail_url   = f.get("linkToHtml") or f.get("filingDetailUrl")
        filed_at     = f.get("filedAt")

        if not issuer_name or not detail_url or not filed_at:
            continue

        # Upsert Company by exact name
        company = session.query(Company).filter_by(name=issuer_name).first()
        if not company:
            company = Company(name=issuer_name)
            session.add(company)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                company = session.query(Company).filter_by(name=issuer_name).one()

        # Extract the structured Form D data
        try:
            extracted = extractor_api.get_extracted_data(detail_url).get("entity", {})
        except Exception as e:
            print("  ⚠️ Extraction failed for", issuer_name, detail_url, e)
            continue

        # Parse amount
        amount = None
        amt_obj = extracted.get("offeringAmount")
        if amt_obj and isinstance(amt_obj, dict):
            try:
                amount = float(amt_obj.get("value", 0))
            except Exception:
                pass

        # Parse dateOfFirstSale
        first_sale = None
        ds = extracted.get("dateOfFirstSale")
        if ds:
            try:
                first_sale = datetime.fromisoformat(ds).date()
            except Exception:
                pass

        # Skip if we already have this round (company/date/type)
        exists = session.query(FundingRound).filter_by(
            company_id = company.company_id,
            date       = first_sale,
            round_type = "Form D",
            amount     = amount
        ).first()
        if exists:
            continue

        # Insert the FundingRound
        fr = FundingRound(
            company_id = company.company_id,
            date       = first_sale,
            round_type = "Form D",
            amount     = amount,
            details    = f"Filed: {filed_at}; URL: {detail_url}"
        )
        session.add(fr)

    session.commit()
    session.close()
    print(f"→ Done ingesting Form D filings between {start_date} and {end_date}")

def main():
    # e.g. Q1 2025
    ingest_formd_via_secapi("2025-01-01", "2025-03-31")
    # add more windows as needed

if __name__ == "__main__":
    main()