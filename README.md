# Biotech Knowledge Graph

This repository builds a comprehensive **knowledge graph** of biotech and biopharma companies, spanning:

- **Workforce events**: Layoff data from Fierce Biotech.
- **Funding events**: Form D filings from SEC EDGAR.
- **Investor relationships**: Linking investors to funding rounds.
- **Graph storage**: Neo4j property graph with `Company`, `LayoffEvent`, `FundingRound`, and `Investor` nodes.

---

## Repository Structure

```
biotech-knowledge-graph/
├── db/
│   ├── __init__.py
│   ├── models.py         # SQLAlchemy models
│   └── session.py        # DB engine & session
│
├── graph/
│   ├── __init__.py
│   └── neo4j_loader.py   # Push Postgres data into Neo4j
│
├── ingestion/
│   ├── fierce_layoff.py  # Scrape Fierce Biotech layoffs
│   ├── formd_secapi.py   # Ingest SEC EDGAR Form D filings
│   └── crunchbase.py     # (Optional) Crunchbase enrichment
│
├── nlp/
│   └── layoff_extractor.py  # LangChain pipeline to extract layoff numbers
│
├── create_tables.py      # Create Postgres tables via SQLAlchemy
├── main.py               # Orchestrator: fetch → ingest → load graph
├── check_rounds.py       # Utility: inspect FundingRound count
├── .env                  # Environment variables (not committed)
└── docker-compose.yml    # Postgres & Neo4j services
```

---

## Getting Started

### 1. Prerequisites

- **Docker Desktop** running on your machine.
- **Python 3.9+** environment (e.g., venv or Conda).
- **SEC API Key** for EDGAR ingestion (see https://sec-api.io).
- **OpenAI API Key** (for layoff number extraction).

### 2. Clone & Install

```bash
git clone https://github.com/your-org/biotech-knowledge-graph.git
cd biotech-knowledge-graph
python -m venv venv             # or conda create -n biotech python=3.9
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt\```

If you don’t have a `requirements.txt`, install:
```bash
pip install sqlalchemy psycopg2-binary neo4j python-dotenv langchain-openai sec-api pydantic selenium beautifulsoup4 webdriver-manager python-dateutil requests
```

### 3. Environment Variables

Create a `.env` file at the project root:

```ini
# Postgres
POSTGRES_USER=biouser
POSTGRES_PASSWORD=biopass
POSTGRES_DB=biodb
# SQLAlchemy URL
DATABASE_URL=postgresql://biouser:biopass@localhost:5432/biodb

# OpenAI
OPENAI_API_KEY=sk-...

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=neo4jpass

# SEC EDGAR
SEC_API_KEY=YOUR_SEC_API_KEY

# (Optional) Crunchbase
CRUNCHBASE_API_KEY=YOUR_CRUNCHBASE_KEY
```

### 4. Launch Databases via Docker Compose

```bash
docker-compose up -d
```

- **Postgres** on port `5432`
- **Neo4j** Browser at http://localhost:7474 (login with `neo4j` / `neo4jpass`)

### 5. Initialize Postgres Schema

```bash
python create_tables.py
```

This creates the tables for companies, layoffs, funding rounds, and investors.

### 6. Run the Pipeline

```bash
python main.py
```

This will:

1. Scrape and ingest layoff events
2. Fetch SEC Form D filings and insert as funding rounds
3. Load all data into Neo4j

### 7. Verify in Neo4j Browser

```cypher
CALL db.labels();
CALL db.relationshipTypes();

// Sample query:
MATCH (c:Company)-[:UNDERWENT_LAYOFF]->(e:LayoffEvent)
RETURN c.name, e.date, e.num_laid_off
LIMIT 5;
```

Or for funding rounds:
```cypher
MATCH (c:Company)-[:RAISED]->(f:FundingRound {round_type:'Form D'})
RETURN c.name, f.date, f.amount
ORDER BY f.date DESC
LIMIT 10;
```

---

## Development & Extensions

- **Crunchbase enrichment**: populate `external_ids['crunchbase']` and fetch investor data.
- **Academic Spinouts**: add scrapers under `ingestion/` for university TLO pages.
- **ClinicalTrials**: ingest from ClinicalTrials.gov API for partnerships.
- **SEC Forms**: extend to Form 3/4 and 8-K for M&A events.
