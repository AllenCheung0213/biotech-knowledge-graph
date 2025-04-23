import os, time, requests, json
from db.session import SessionLocal
from db.models  import Company, Investor, FundingRound, FundingRoundInvestor
from datetime import datetime
from dotenv     import load_dotenv

load_dotenv()
CB_API_KEY = os.getenv('CRUNCHBASE_API_KEY')
SEARCH_URL = 'https://api.crunchbase.com/api/v4/searches/organizations'
BASE_URL   = 'https://api.crunchbase.com/api/v4/organizations'

def search_crunchbase(name: str) -> str | None:
    """Return the first matching Crunchbase UUID for this company name."""
    body = {
        "query": {
            "kind": "predicate",
            "field_name": "identifier",
            "operator": "contains",
            "values": [name]
        },
        "options": {"pagination": {"limit": 1}}
    }
    resp = requests.post(SEARCH_URL, json=body, headers={'X-Cb-User-Key': CB_API_KEY})
    resp.raise_for_status()
    items = resp.json().get('data', {}).get('items', [])
    return items[0].get('uuid') if items else None

def upsert_crunchbase_data():
    session = SessionLocal()
    try:
        companies = session.query(Company).all()
        for c in companies:
            ext = c.external_ids or {}

            # 1) If we don't have a cb id yet, try to look it up and store it
            if 'crunchbase' not in ext:
                uuid = search_crunchbase(c.name)
                if not uuid:
                    continue  # no match
                ext['crunchbase'] = uuid
                c.external_ids = ext
                session.commit()

            cb_uuid = ext['crunchbase']

            # 2) Fetch & upsert core company details (optional)
            details = requests.get(
                f"{BASE_URL}/{cb_uuid}",
                headers={'X-Cb-User-Key': CB_API_KEY}
            ).json().get('data', {}).get('properties', {})
            c.website      = details.get('homepage_url')   or c.website
            c.type         = details.get('primary_role')   or c.type
            fy = details.get('founded_on')
            c.founded_year = int(fy[:4]) if fy else c.founded_year
            session.commit()

            # 3) Fetch funding rounds
            fr_url = f"{BASE_URL}/{cb_uuid}/funding_rounds"
            for rd in requests.get(fr_url, headers={'X-Cb-User-Key': CB_API_KEY}).json().get('data', []):
                p = rd.get('properties', {})
                # parse date
                try:
                    d = datetime.fromisoformat(p.get('announced_on')).date()
                except:
                    d = None

                fr = FundingRound(
                    company_id = c.company_id,
                    date       = d,
                    round_type = p.get('series'),
                    amount     = float(p.get('money_raised_usd') or 0),
                    details    = p.get('short_description')
                )
                session.add(fr)
                session.commit()

                # link each investor
                inv_items = rd.get('relationships', {}).get('investors', {}).get('items', [])
                for inv in inv_items:
                    name = inv.get('properties', {}).get('name')
                    if not name:
                        continue
                    inv_obj = session.query(Investor).filter_by(name=name).first()
                    if not inv_obj:
                        inv_obj = Investor(name=name)
                        session.add(inv_obj)
                        session.commit()
                    session.add(FundingRoundInvestor(
                        round_id    = fr.round_id,
                        investor_id = inv_obj.investor_id
                    ))
                session.commit()

            time.sleep(1)  # rate-limit

    finally:
        session.close()

if __name__ == "__main__":
    upsert_crunchbase_data()