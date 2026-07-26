from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS
from app.db import check_db_connection
from app.routers import accessibility
from app.schemas import HealthResponse

app = FastAPI(
    title="15-Minute City Accessibility API",
    description="API for spatial accessibility analysis, scenarios, and GeoJSON delivery",
    version="1.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(accessibility.router)


@app.get("/health", response_model=HealthResponse, tags=["System"])
def health():
    db_ok = check_db_connection()
    return HealthResponse(
        status="ok" if db_ok else "degraded",
        database="up" if db_ok else "down",
    )


@app.get("/")
def root():
    return {
        "message": "15-Minute City Accessibility API is running.",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "summary": "/accessibility/summary",
            "histogram": "/accessibility/histogram",
            "geojson": "/accessibility/geojson",
            "map": "/accessibility/map (deprecated)",
            "runs": "/accessibility/runs",
            "baseline": "/accessibility/runs/baseline",
            "compare": "/accessibility/compare",
            "gaps": "/accessibility/gaps/geojson",
            "neighborhood_summary": "/accessibility/neighborhoods/summary",
            "data_quality": "/accessibility/data-quality",
            "boundary": "/accessibility/boundary",
            "neighborhoods": "/accessibility/neighborhoods",
        },
        "data_contract": {
            "current_view": "v_block_accessibility_15min",
            "paper_baseline_view": "v_paper_baseline_accessibility",
            "scenarios_table": "block_accessibility_scenarios",
            "travel_times_table": "block_travel_times",
            "gaps_table": "intervention_gaps",
            "runs_table": "analysis_runs",
        },
    }
