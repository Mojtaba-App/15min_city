from typing import Optional, Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db

router = APIRouter(
    prefix="/accessibility",
    tags=["Accessibility Analysis"]
)


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


@router.get("/summary")
def get_accessibility_summary(db: Session = Depends(get_db)) -> Dict[str, Any]:
    # استفاده از جدول اصلی برای اطمینان از وجود تمام ستون‌ها
    query = text("""
        SELECT
            COUNT(*) AS total_blocks,
            ROUND(AVG(COALESCE(accessibility_score, 0))::numeric, 2) AS avg_score,
            MIN(COALESCE(accessibility_score, 0)) AS min_score,
            MAX(COALESCE(accessibility_score, 0)) AS max_score,
            SUM(CASE WHEN COALESCE(has_education, 0) = 1 THEN 1 ELSE 0 END) AS education_covered,
            SUM(CASE WHEN COALESCE(has_health, 0) = 1 THEN 1 ELSE 0 END) AS health_covered,
            SUM(CASE WHEN COALESCE(has_shopping, 0) = 1 THEN 1 ELSE 0 END) AS shopping_covered,
            SUM(CASE WHEN COALESCE(has_recreation, 0) = 1 THEN 1 ELSE 0 END) AS recreation_covered
        FROM block_accessibility_15min;
    """)

    try:
        result = db.execute(query).mappings().first()
        if not result:
            return {"message": "No data available."}

        total_blocks = safe_int(result.get("total_blocks"), 0)

        if total_blocks == 0:
            return {
                "message": "Table is empty.",
                "total_blocks": 0,
                "statistics": {"avg_score": 0.0, "min_score": 0, "max_score": 0},
                "coverage_metrics": {
                    "education": {"count": 0, "percentage": 0.0},
                    "health": {"count": 0, "percentage": 0.0},
                    "shopping": {"count": 0, "percentage": 0.0},
                    "recreation": {"count": 0, "percentage": 0.0}
                }
            }

        education_count = safe_int(result.get("education_covered"))
        health_count = safe_int(result.get("health_covered"))
        shopping_count = safe_int(result.get("shopping_covered"))
        recreation_count = safe_int(result.get("recreation_covered"))

        return {
            "total_blocks": total_blocks,
            "statistics": {
                "avg_score": safe_float(result.get("avg_score")),
                "min_score": safe_int(result.get("min_score")),
                "max_score": safe_int(result.get("max_score"))
            },
            "coverage_metrics": {
                "education": {
                    "count": education_count,
                    "percentage": round((education_count / total_blocks) * 100, 2)
                },
                "health": {
                    "count": health_count,
                    "percentage": round((health_count / total_blocks) * 100, 2)
                },
                "shopping": {
                    "count": shopping_count,
                    "percentage": round((shopping_count / total_blocks) * 100, 2)
                },
                "recreation": {
                    "count": recreation_count,
                    "percentage": round((recreation_count / total_blocks) * 100, 2)
                }
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summary query failed: {str(e)}")


@router.get("/histogram")
def get_accessibility_histogram(db: Session = Depends(get_db)) -> Dict[str, List[Dict[str, int]]]:
    query = text("""
        SELECT
            COALESCE(accessibility_score, 0) AS score,
            COUNT(*) AS block_count
        FROM block_accessibility_15min
        GROUP BY COALESCE(accessibility_score, 0)
        ORDER BY score;
    """)

    try:
        results = db.execute(query).mappings().all()
        return {
            "histogram": [
                {
                    "score": safe_int(row.get("score")),
                    "count": safe_int(row.get("block_count"))
                }
                for row in results
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Histogram query failed: {str(e)}")


@router.get("/geojson")
def get_accessibility_geojson(
    db: Session = Depends(get_db),
    min_score: Optional[int] = Query(None, ge=0, le=4),
    max_score: Optional[int] = Query(None, ge=0, le=4),
    only_unserved: bool = Query(False),
    limit: int = Query(3000, ge=1, le=20000)
) -> Dict[str, Any]:

    conditions = ["geom IS NOT NULL"]
    params: Dict[str, Any] = {"limit": limit}

    if only_unserved:
        conditions.append("COALESCE(accessibility_score, 0) = 0")

    if min_score is not None:
        conditions.append("COALESCE(accessibility_score, 0) >= :min_score")
        params["min_score"] = min_score

    if max_score is not None:
        conditions.append("COALESCE(accessibility_score, 0) <= :max_score")
        params["max_score"] = max_score

    where_clause = " AND ".join(conditions)

    # خواندن مستقیم از جدول block_accessibility_15min با ستون‌های تایید شده
    query = text(f"""
        SELECT json_build_object(
            'type', 'FeatureCollection',
            'features', COALESCE(json_agg(feature), '[]'::json)
        ) AS geojson
        FROM (
            SELECT json_build_object(
                'type', 'Feature',
                'geometry', ST_AsGeoJSON(ST_Transform(geom, 4326))::json,
                'properties', json_build_object(
                    'block_gid', block_gid,
                    'nearest_vertex', nearest_vertex,
                    'distance_to_network', distance_to_network,
                    'score', COALESCE(accessibility_score, 0),
                    'has_education', COALESCE(has_education, 0),
                    'has_health', COALESCE(has_health, 0),
                    'has_shopping', COALESCE(has_shopping, 0),
                    'has_recreation', COALESCE(has_recreation, 0)
                )
            ) AS feature
            FROM block_accessibility_15min
            WHERE {where_clause}
            ORDER BY block_gid
            LIMIT :limit
        ) AS features;
    """)

    try:
        result = db.execute(query, params).scalar()

        if not result:
            return {"type": "FeatureCollection", "features": []}

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GeoJSON generation failed: {str(e)}")


@router.get("/map")
def get_accessibility_map(
    db: Session = Depends(get_db),
    min_score: Optional[int] = Query(None, ge=0, le=4),
    max_score: Optional[int] = Query(None, ge=0, le=4),
    only_unserved: bool = Query(False),
    limit: int = Query(3000, ge=1, le=20000)
) -> Dict[str, Any]:
    return get_accessibility_geojson(
        db=db,
        min_score=min_score,
        max_score=max_score,
        only_unserved=only_unserved,
        limit=limit
    )

# در فایل accessibility.py

@router.get("/boundary")
async def get_city_boundary(db: Session = Depends(get_db)):
    # فرض بر این است که جدولی به نام city_boundary داری
    # اگر نام جدول متفاوت است، آن را تغییر بده
    query = """
        SELECT jsonb_build_object(
            'type', 'FeatureCollection',
            'features', jsonb_agg(features.feature)
        )
        FROM (
            SELECT jsonb_build_object(
                'type', 'Feature',
                'geometry', ST_AsGeoJSON(ST_Transform(geom, 4326))::jsonb,
                'properties', jsonb_build_object('name', 'مرز محدوده شهر')
            ) AS feature
            FROM ahvaz_boundary  -- نام جدول مرز شهر تو
        ) AS features;
    """
    result = db.execute(text(query)).scalar()
    return result

@router.get("/neighborhoods")
async def get_neighborhoods(db: Session = Depends(get_db)):
    # فرض بر این است که جدولی به نام neighborhoods داری
    query = """
        SELECT jsonb_build_object(
            'type', 'FeatureCollection',
            'features', jsonb_agg(features.feature)
        )
        FROM (
            SELECT jsonb_build_object(
                'type', 'Feature',
                'geometry', ST_AsGeoJSON(ST_Transform(geom, 4326))::jsonb,
                'properties', jsonb_build_object('name', name) -- فرض بر وجود ستون نام محله
            ) AS feature
            FROM ahvaz_neighborhoods -- نام جدول محلات تو
        ) AS features;
    """
    result = db.execute(text(query)).scalar()
    return result
