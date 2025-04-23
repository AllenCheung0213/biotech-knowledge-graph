from ingestion.fierce_layoff import fetch_and_store_layoffs
from ingestion.formd_secapi import ingest_formd_via_secapi
from graph.neo4j_loader import load_to_neo4j

def main():
    fetch_and_store_layoffs()
    ingest_formd_via_secapi("2025-01-01", "2025-03-31")
    load_to_neo4j()

if __name__ == '__main__':
    main()
