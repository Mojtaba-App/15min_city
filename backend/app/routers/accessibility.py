from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import (
    AccessibilitySummaryResponse,
    AnalysisRun,
    AnalysisRunsResponse,
    CategoryCoverage,
    DataQualityCheck,
    DataQualityResponse,
    HistogramBucket,
    HistogramResponse,
    SummaryStatistics,
)

router = APIRouter(
    prefix="/accessibility",
    tags=["Accessibility Analysis"],
)

CATEGORY_COLUMNS = {
    "education": "has_education",
    "health": "has_health",
    "shopping": "has_shopping",
    "recreation": "has_recreation",
}


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


def _serialize_run(row: Any, *, api_view: str | None = None) -> AnalysisRun:
    return AnalysisRun(
        run_id=safe_int(row.get("run_id")),
        run_code=row.get("run_code"),
        label=row.get("label"),
        city=row.get("city"),
        walking_speed_mps=safe_float(row.get("walking_speed_mps")),
        time_threshold_sec=safe_int(row.get("time_threshold_sec")),
        score_min=safe_int(row.get("score_min")),
        score_max=safe_int(row.get("score_max")),
        categories=list(row.get("categories") or []),
        pipeline_version=row.get("pipeline_version"),
        is_paper_baseline=bool(row.get("is_paper_baseline")),
        result_table=row.get("result_table"),
        block_count=safe_int(row.get("block_count")) if row.get("block_count") is not None else None,
        service_count=safe_int(row.get("service_count")) if row.get("service_count") is not None else None,
        avg_score=safe_float(row.get("avg_score")) if row.get("avg_score") is not None else None,
        notes=row.get("notes"),
        created_at=row.get("created_at").isoformat() if row.get("created_at") else None,
        api_view=api_view,
    )


@router.get("/summary", response_model=AccessibilitySummaryResponse)
def get_accessibility_summary(db: Session = Depends(get_db)) -> AccessibilitySummaryResponse:
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
        FROM v_block_accessibility_15min;
    """)

    try:
        result = db.execute(query).mappings().first()
        if not result:
            return AccessibilitySummaryResponse(
                total_blocks=0,
                statistics=SummaryStatistics(avg_score=0.0, min_score=0, max_score=0),
                coverage_metrics={
                    "education": CategoryCoverage(count=0, percentage=0.0),
                    "health": CategoryCoverage(count=0, percentage=0.0),
                    "shopping": CategoryCoverage(count=0, percentage=0.0),
                    "recreation": CategoryCoverage(count=0, percentage=0.0),
                },
                message="No data available.",
            )

        total_blocks = safe_int(result.get("total_blocks"), 0)
        education_count = safe_int(result.get("education_covered"))
        health_count = safe_int(result.get("health_covered"))
        shopping_count = safe_int(result.get("shopping_covered"))
        recreation_count = safe_int(result.get("recreation_covered"))

        def pct(count: int) -> float:
            return round((count / total_blocks) * 100, 2) if total_blocks else 0.0

        return AccessibilitySummaryResponse(
            total_blocks=total_blocks,
            statistics=SummaryStatistics(
                avg_score=safe_float(result.get("avg_score")),
                min_score=safe_int(result.get("min_score")),
                max_score=safe_int(result.get("max_score")),
            ),
            coverage_metrics={
                "education": CategoryCoverage(count=education_count, percentage=pct(education_count)),
                "health": CategoryCoverage(count=health_count, percentage=pct(health_count)),
                "shopping": CategoryCoverage(count=shopping_count, percentage=pct(shopping_count)),
                "recreation": CategoryCoverage(count=recreation_count, percentage=pct(recreation_count)),
            },
            message="Table is empty." if total_blocks == 0 else None,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summary query failed: {str(e)}")


@router.get("/histogram", response_model=HistogramResponse)
def get_accessibility_histogram(db: Session = Depends(get_db)) -> HistogramResponse:
    query = text("""
        SELECT
            COALESCE(accessibility_score, 0) AS score,
            COUNT(*) AS block_count
        FROM v_block_accessibility_15min
        GROUP BY COALESCE(accessibility_score, 0)
        ORDER BY score;
    """)

    try:
        results = db.execute(query).mappings().all()
        return HistogramResponse(
            histogram=[
                HistogramBucket(
                    score=safe_int(row.get("score")),
                    count=safe_int(row.get("block_count")),
                )
                for row in results
            ]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Histogram query failed: {str(e)}")


@router.get("/runs", response_model=AnalysisRunsResponse)
def list_analysis_runs(db: Session = Depends(get_db)) -> AnalysisRunsResponse:
    query = text("""
        SELECT
            run_id, run_code, label, city, walking_speed_mps, time_threshold_sec,
            score_min, score_max, categories, pipeline_version, is_paper_baseline,
            result_table, block_count, service_count, avg_score, notes, created_at
        FROM analysis_runs
        ORDER BY is_paper_baseline DESC, created_at DESC;
    """)
    try:
        rows = db.execute(query).mappings().all()
        return AnalysisRunsResponse(runs=[_serialize_run(row) for row in rows])
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis runs query failed (run sql/08–09 first): {str(e)}",
        )


@router.get("/runs/baseline", response_model=AnalysisRun)
def get_paper_baseline_run(db: Session = Depends(get_db)) -> AnalysisRun:
    query = text("""
        SELECT
            run_id, run_code, label, city, walking_speed_mps, time_threshold_sec,
            score_min, score_max, categories, pipeline_version, is_paper_baseline,
            result_table, block_count, service_count, avg_score, notes, created_at
        FROM analysis_runs
        WHERE is_paper_baseline = true
        ORDER BY created_at ASC
        LIMIT 1;
    """)
    try:
        row = db.execute(query).mappings().first()
        if not row:
            raise HTTPException(
                status_code=404,
                detail="Paper baseline not registered. Run sql/09_freeze_paper_baseline.sql",
            )
        return _serialize_run(row, api_view="v_paper_baseline_accessibility")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Baseline query failed (run sql/08–09 first): {str(e)}",
        )


@router.get("/data-quality", response_model=DataQualityResponse)
def get_data_quality(db: Session = Depends(get_db)) -> DataQualityResponse:
    """Read-only quality checks for network snap coverage and classification."""
    checks: List[DataQualityCheck] = []

    try:
        blocks = db.execute(text("""
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE nearest_vertex IS NULL) AS unsapped,
                ROUND(AVG(distance_to_network)::numeric, 2) AS avg_dist,
                ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY distance_to_network)::numeric, 2) AS p95_dist
            FROM population_blocks;
        """)).mappings().first()

        total = safe_int(blocks.get("total")) if blocks else 0
        unsapped = safe_int(blocks.get("unsapped")) if blocks else 0
        checks.append(DataQualityCheck(
            check_id="blocks_total",
            label="Total population blocks",
            value=total,
            severity="info",
        ))
        checks.append(DataQualityCheck(
            check_id="blocks_unsapped",
            label="Blocks without nearest_vertex",
            value=unsapped,
            severity="critical" if unsapped > 0 else "info",
        ))
        checks.append(DataQualityCheck(
            check_id="blocks_avg_distance_to_network",
            label="Average block distance to network",
            value=safe_float(blocks.get("avg_dist")) if blocks else None,
            unit="m",
            severity="warn" if blocks and safe_float(blocks.get("avg_dist")) > 100 else "info",
        ))
        checks.append(DataQualityCheck(
            check_id="blocks_p95_distance_to_network",
            label="P95 block distance to network",
            value=safe_float(blocks.get("p95_dist")) if blocks else None,
            unit="m",
            severity="info",
        ))

        services = db.execute(text("""
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE nearest_vertex IS NULL) AS unsapped
            FROM urban_services;
        """)).mappings().first()
        svc_total = safe_int(services.get("total")) if services else 0
        svc_unsapped = safe_int(services.get("unsapped")) if services else 0
        checks.append(DataQualityCheck(
            check_id="services_total",
            label="Total urban services",
            value=svc_total,
            severity="info",
        ))
        checks.append(DataQualityCheck(
            check_id="services_unsapped",
            label="Services without nearest_vertex",
            value=svc_unsapped,
            severity="warn" if svc_unsapped > 0 else "info",
        ))

        categories = db.execute(text("""
            SELECT category, COUNT(*) AS n
            FROM service_categories
            GROUP BY category
            ORDER BY category;
        """)).mappings().all()
        for row in categories:
            cat = row.get("category")
            n = safe_int(row.get("n"))
            checks.append(DataQualityCheck(
                check_id=f"service_category_{cat}",
                label=f"Services classified as {cat}",
                value=n,
                severity="warn" if cat == "other" and n > 0 else "info",
            ))

        roads = db.execute(text("""
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE source IS NULL OR target IS NULL) AS incomplete
            FROM roads;
        """)).mappings().first()
        road_total = safe_int(roads.get("total")) if roads else 0
        road_incomplete = safe_int(roads.get("incomplete")) if roads else 0
        checks.append(DataQualityCheck(
            check_id="roads_total",
            label="Road edges",
            value=road_total,
            severity="info",
        ))
        checks.append(DataQualityCheck(
            check_id="roads_incomplete_topology",
            label="Road edges missing source/target",
            value=road_incomplete,
            severity="critical" if road_incomplete > 0 else "info",
        ))

        scores = db.execute(text("""
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE COALESCE(accessibility_score, 0) = 0) AS score_zero
            FROM v_block_accessibility_15min;
        """)).mappings().first()
        acc_total = safe_int(scores.get("total")) if scores else 0
        score_zero = safe_int(scores.get("score_zero")) if scores else 0
        checks.append(DataQualityCheck(
            check_id="accessibility_blocks",
            label="Blocks in accessibility view",
            value=acc_total,
            severity="info",
        ))
        checks.append(DataQualityCheck(
            check_id="accessibility_score_zero",
            label="Blocks with score 0",
            value=score_zero,
            severity="info",
        ))

        return DataQualityResponse(checks=checks)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Data quality query failed: {str(e)}")


@router.get("/geojson")
def get_accessibility_geojson(
    db: Session = Depends(get_db),
    min_score: Optional[int] = Query(None, ge=0, le=4),
    max_score: Optional[int] = Query(None, ge=0, le=4),
    only_unserved: bool = Query(False),
    missing_category: Optional[str] = Query(
        None,
        pattern="^(education|health|shopping|recreation)$",
        description="Keep blocks that lack this category within 15 minutes",
    ),
    limit: int = Query(3000, ge=1, le=20000),
    source: str = Query(
        "current",
        pattern="^(current|paper_baseline)$",
        description="current = live view; paper_baseline = frozen paper snapshot",
    ),
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

    if missing_category:
        column = CATEGORY_COLUMNS[missing_category]
        conditions.append(f"COALESCE({column}, 0) = 0")

    where_clause = " AND ".join(conditions)
    source_view = (
        "v_paper_baseline_accessibility"
        if source == "paper_baseline"
        else "v_block_accessibility_15min"
    )

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
            FROM {source_view}
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


@router.get("/map", deprecated=True)
def get_accessibility_map(
    db: Session = Depends(get_db),
    min_score: Optional[int] = Query(None, ge=0, le=4),
    max_score: Optional[int] = Query(None, ge=0, le=4),
    only_unserved: bool = Query(False),
    missing_category: Optional[str] = Query(
        None, pattern="^(education|health|shopping|recreation)$"
    ),
    limit: int = Query(3000, ge=1, le=20000),
    source: str = Query("current", pattern="^(current|paper_baseline)$"),
) -> Dict[str, Any]:
    """Deprecated alias of /geojson. Prefer /accessibility/geojson."""
    return get_accessibility_geojson(
        db=db,
        min_score=min_score,
        max_score=max_score,
        only_unserved=only_unserved,
        missing_category=missing_category,
        limit=limit,
        source=source,
    )


def _relation_exists(db: Session, table_name: str) -> bool:
    exists = db.execute(
        text("SELECT to_regclass(:name) IS NOT NULL"),
        {"name": f"public.{table_name}"},
    ).scalar()
    return bool(exists)


@router.get("/boundary")
def get_city_boundary(db: Session = Depends(get_db)) -> Dict[str, Any]:
    if not _relation_exists(db, "ahvaz_boundary"):
        return {"type": "FeatureCollection", "features": []}

    query = text("""
        SELECT jsonb_build_object(
            'type', 'FeatureCollection',
            'features', COALESCE(jsonb_agg(features.feature), '[]'::jsonb)
        )
        FROM (
            SELECT jsonb_build_object(
                'type', 'Feature',
                'geometry', ST_AsGeoJSON(ST_Transform(geom, 4326))::jsonb,
                'properties', jsonb_build_object('name', 'مرز محدوده شهر')
            ) AS feature
            FROM ahvaz_boundary
            WHERE geom IS NOT NULL
        ) AS features;
    """)
    try:
        result = db.execute(query).scalar()
        if not result:
            return {"type": "FeatureCollection", "features": []}
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Boundary query failed: {str(e)}")


@router.get("/neighborhoods")
def get_neighborhoods(db: Session = Depends(get_db)) -> Dict[str, Any]:
    if not _relation_exists(db, "ahvaz_neighborhoods"):
        return {"type": "FeatureCollection", "features": []}

    query = text("""
        SELECT jsonb_build_object(
            'type', 'FeatureCollection',
            'features', COALESCE(jsonb_agg(features.feature), '[]'::jsonb)
        )
        FROM (
            SELECT jsonb_build_object(
                'type', 'Feature',
                'geometry', ST_AsGeoJSON(ST_Transform(geom, 4326))::jsonb,
                'properties', jsonb_build_object('name', name)
            ) AS feature
            FROM ahvaz_neighborhoods
            WHERE geom IS NOT NULL
        ) AS features;
    """)
    try:
        result = db.execute(query).scalar()
        if not result:
            return {"type": "FeatureCollection", "features": []}
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Neighborhoods query failed: {str(e)}")
