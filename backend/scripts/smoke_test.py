"""Manual end-to-end smoke test against REAL BigQuery/Redis (and real
Jev/Gemini calls if those keys are set -- otherwise the orchestrator falls
back to the rule baseline / templated report automatically).

Run scripts/seed_bigquery.py first (after app.datastore.schema.create_tables).

Usage:
    python -m scripts.smoke_test "301 Congress Ave, Austin, TX"
"""

import asyncio
import sys

import httpx

from app.config import get_settings

DEFAULT_ADDRESS = "301 Congress Ave, Austin, TX"


async def main() -> None:
    address = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ADDRESS
    settings = get_settings()
    base_url = f"http://localhost:8000"

    print(f"POSTing address: {address!r} to {base_url}/v1/reports")
    print(f"(assumes `uvicorn app.main:app` is running; GCP_PROJECT_ID={settings.gcp_project_id!r})")

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(f"{base_url}/v1/reports", json={"address": address})
        resp.raise_for_status()
        report = resp.json()

    print(f"report_id: {report['report_id']}")
    print(f"data_gaps: {report['data_gaps']}")
    print(f"needs_expert_review: {report['needs_expert_review']}")
    for hazard, result in report["hazards"].items():
        print(f"  {hazard}: {result['level']} (score={result['score']}, confidence={result['confidence']:.2f})")

    async with httpx.AsyncClient(timeout=30.0) as client:
        pdf_resp = await client.get(f"{base_url}/v1/reports/{report['report_id']}/pdf")
        pdf_resp.raise_for_status()
        assert len(pdf_resp.content) > 0, "PDF response was empty"
        print(f"PDF: {len(pdf_resp.content)} bytes -- OK")

    print("Smoke test passed.")


if __name__ == "__main__":
    asyncio.run(main())
