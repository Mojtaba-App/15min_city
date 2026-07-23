from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import accessibility

app = FastAPI(
    title="15-Minute City Accessibility API",
    description="API for spatial accessibility analysis and GeoJSON delivery",
    version="1.0.0"
)

# CORS برای فرانت‌اند محلی یا وب‌اپ
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(accessibility.router)


@app.get("/")
def root():
    return {
        "message": "15-Minute City Accessibility API is running.",
        "docs": "/docs",
        "endpoints": {
            "summary": "/accessibility/summary",
            "histogram": "/accessibility/histogram",
            "geojson": "/accessibility/geojson",
            "map": "/accessibility/map"
        }
    }
