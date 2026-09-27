from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_reports import router as reports_router

app = FastAPI(title="Parcel Risk Report API", version="0.1.0")

# Local dev only: the frontend (Vite, localhost:5173) and this API
# (localhost:8000) are different origins, so the browser blocks fetch()
# without explicit CORS headers. Tighten this to a real allowed-origins
# list before any non-local deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(reports_router)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
