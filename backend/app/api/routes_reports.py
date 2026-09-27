import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from app.api.deps import get_bq_client, get_redis_client
from app.api.schemas import Coordinates, ReportRequest, ReportResponse
from app.core.orchestrator import generate_report, get_pdf_bytes
from app.datastore.bigquery_client import HazardFeatureStore
from app.pdf.render import render_pdf

logger = logging.getLogger("api.routes_reports")

router = APIRouter(prefix="/v1/reports", tags=["reports"])


@router.post("", response_model=None)
async def create_report(
    body: ReportRequest,
    stream: bool = False,
    store: HazardFeatureStore = Depends(get_bq_client),
    redis_client=Depends(get_redis_client),
):
    if stream:
        async def event_generator():
            async for item in generate_report(body.address, store, redis_client):
                if isinstance(item, ReportResponse):
                    yield {"event": "done", "data": item.model_dump_json()}
                else:
                    yield {"event": "progress", "data": item.model_dump_json()}

        return EventSourceResponse(event_generator())

    final_response: ReportResponse | None = None
    async for item in generate_report(body.address, store, redis_client):
        if isinstance(item, ReportResponse):
            final_response = item
    if final_response is None:
        raise HTTPException(status_code=500, detail="Report generation did not complete")
    return final_response


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(report_id: str, store: HazardFeatureStore = Depends(get_bq_client)):
    row = store.get_report(report_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Report not found")
    scores = row.get("scores") if isinstance(row.get("scores"), dict) else json.loads(row.get("scores") or "{}")
    hazards = {
        hazard: {
            "level": s["level"],
            "score": s["score_0_100"],
            "confidence": s["confidence"],
            "material_to_buyer": s["material_to_buyer"],
            "evidence": [],
        }
        for hazard, s in scores.items()
    }
    return ReportResponse(
        report_id=row["report_id"],
        parcel_id=row["parcel_id"],
        data_version=row["data_version"],
        hazards=hazards,
        needs_expert_review=row.get("needs_expert_review", False),
        data_gaps=row.get("data_gaps") or [],
        evidence={},
        report_md=row["report_md"],
        center=Coordinates(lat=row["center_lat"], lon=row["center_lon"]),
    )


@router.get("/{report_id}/pdf")
async def get_report_pdf(report_id: str, store: HazardFeatureStore = Depends(get_bq_client)):
    pdf_bytes = get_pdf_bytes(report_id)
    if pdf_bytes is None:
        row = store.get_report(report_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Report not found")
        pdf_bytes = render_pdf(row["report_md"], report_id, row["parcel_id"], row["data_version"])

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={report_id}.pdf"},
    )
