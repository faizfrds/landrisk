"""Create (idempotently) the 4 BigQuery tables described in ddl.sql.

Usage:
    python -m app.datastore.schema.create_tables
"""

from pathlib import Path

from google.cloud import bigquery

from app.config import get_settings

DDL_PATH = Path(__file__).parent / "ddl.sql"


def main() -> None:
    settings = get_settings()
    client = bigquery.Client(project=settings.gcp_project_id)

    raw = DDL_PATH.read_text()
    rendered = raw.format(project=settings.gcp_project_id, dataset=settings.bq_dataset)

    statements = [s.strip() for s in rendered.split(";") if s.strip()]
    for statement in statements:
        print(f"Running:\n{statement[:120]}...")
        client.query(statement).result()

    print(f"Schema ready in {settings.gcp_project_id}.{settings.bq_dataset}")


if __name__ == "__main__":
    main()
