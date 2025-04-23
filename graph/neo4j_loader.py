# graph/neo4j_loader.py

import os
import json
from neo4j import GraphDatabase
from db.session import SessionLocal
from db.models import (
    Company,
    LayoffEvent,
    Investor,
    FundingRound,
    FundingRoundInvestor,
)
from dotenv import load_dotenv

load_dotenv()
NEO4J_URI      = os.getenv("NEO4J_URI")
NEO4J_USER     = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

def load_to_neo4j():
    print("Connecting to Neo4j…")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    sql_session = SessionLocal()

    with driver.session() as neo_session:
        # 1) Companies
        print("Upserting Company nodes…")
        for c in sql_session.query(Company).all():
            ext_ids = json.dumps(c.external_ids) if c.external_ids else None
            neo_session.run(
                """
                MERGE (co:Company {company_id: $company_id})
                SET co.name           = $name,
                    co.type           = $type,
                    co.founded_year   = $founded_year,
                    co.website        = $website,
                    co.employee_count = $employee_count,
                    co.hq_location    = $hq_location,
                    co.external_ids   = $external_ids
                """,
                {
                    'company_id':     c.company_id,
                    'name':           c.name,
                    'type':           c.type,
                    'founded_year':   c.founded_year,
                    'website':        c.website,
                    'employee_count': c.employee_count,
                    'hq_location':    c.hq_location,
                    'external_ids':   ext_ids,
                }
            )

        # 2) LayoffEvents
        print("Upserting LayoffEvent nodes…")
        for e in sql_session.query(LayoffEvent).all():
            neo_session.run(
                """
                MERGE (ev:LayoffEvent {layoff_id: $layoff_id})
                SET ev.date             = date($date),
                    ev.num_laid_off     = $num_laid_off,
                    ev.percent_laid_off = $percent_laid_off,
                    ev.description      = $description,
                    ev.source_url       = $source_url
                """,
                {
                    'layoff_id':       e.layoff_id,
                    'date':            e.date.isoformat(),
                    'num_laid_off':    e.num_laid_off,
                    'percent_laid_off': e.percent_laid_off,
                    'description':     e.description,
                    'source_url':      e.source_url or "",
                }
            )
            neo_session.run(
                """
                MATCH (co:Company {company_id: $company_id})
                MATCH (ev:LayoffEvent {layoff_id: $layoff_id})
                MERGE (co)-[:UNDERWENT_LAYOFF]->(ev)
                """,
                {
                    'company_id': e.company_id,
                    'layoff_id':  e.layoff_id
                }
            )

        # 3) Investors
        print("Upserting Investor nodes…")
        for inv in sql_session.query(Investor).all():
            inv_ext = json.dumps(inv.external_ids) if inv.external_ids else None
            neo_session.run(
                """
                MERGE (i:Investor {investor_id: $investor_id})
                SET i.name         = $name,
                    i.type         = $type,
                    i.external_ids = $external_ids
                """,
                {
                    'investor_id':  inv.investor_id,
                    'name':         inv.name,
                    'type':         inv.type,
                    'external_ids': inv_ext,
                }
            )

        # 4) FundingRounds
        print("Upserting FundingRound nodes & RAISING relationships…")
        for fr in sql_session.query(FundingRound).all():
            neo_session.run(
                """
                MERGE (f:FundingRound {round_id: $round_id})
                SET f.date        = date($date),
                    f.round_type = $round_type,
                    f.amount     = $amount,
                    f.details    = $details
                """,
                {
                    'round_id':   fr.round_id,
                    'date':       fr.date.isoformat() if fr.date else None,
                    'round_type': fr.round_type,
                    'amount':     fr.amount,
                    'details':    fr.details,
                }
            )
            neo_session.run(
                """
                MATCH (c:Company {company_id: $company_id})
                MATCH (f:FundingRound {round_id: $round_id})
                MERGE (c)-[:RAISED]->(f)
                """,
                {
                    'company_id': fr.company_id,
                    'round_id':   fr.round_id
                }
            )

        # 5) INVESTED_IN edges
        print("Linking Investors to FundingRounds…")
        for link in sql_session.query(FundingRoundInvestor).all():
            neo_session.run(
                """
                MATCH (i:Investor {investor_id: $investor_id})
                MATCH (f:FundingRound {round_id: $round_id})
                MERGE (i)-[:INVESTED_IN]->(f)
                """,
                {
                    'investor_id': link.investor_id,
                    'round_id':    link.round_id
                }
            )

    sql_session.close()
    driver.close()
    print("Neo4j load complete!")

if __name__ == "__main__":
    load_to_neo4j()
