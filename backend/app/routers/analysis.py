from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.analysis import (
    AnalysisTablesMissing,
    baseline_summary,
    build_report,
    inventory,
    sensitivity,
    supply_summary,
    zone_features,
    zone_rankings,
)
from app.services.report_markdown import render_report_markdown

router = APIRouter(prefix="/accessibility", tags=["Analysis"])


def _missing(exc: AnalysisTablesMissing) -> HTTPException:
    names = ", ".join(exc.tables)
    return HTTPException(
        status_code=503,
        detail=f"Analysis tables are missing ({names}). Run python build_analysis_extensions.py",
    )


@router.get("/distribution")
def get_distribution(db: Session = Depends(get_db)):
    try:
        summary = baseline_summary(db)
    except AnalysisTablesMissing as exc:
        raise _missing(exc) from exc
    return {
        "total_blocks": summary["total_blocks"],
        "total_population": summary["total_population"],
        "avg_score": summary["avg_score"],
        "weighted_avg_score": summary["weighted_avg_score"],
        "rows": summary["rows"],
        "coverage": summary["coverage"],
    }


@router.get("/combinations")
def get_combinations(db: Session = Depends(get_db)):
    summary = baseline_summary(db)
    return {
        "total_blocks": summary["total_blocks"],
        "total_population": summary["total_population"],
        "combinations": summary["combinations"],
    }


@router.get("/sensitivity")
def get_sensitivity(db: Session = Depends(get_db)):
    try:
        return sensitivity(db)
    except AnalysisTablesMissing as exc:
        raise _missing(exc) from exc


@router.get("/supply")
def get_supply(db: Session = Depends(get_db)):
    try:
        return supply_summary(db)
    except AnalysisTablesMissing as exc:
        raise _missing(exc) from exc


@router.get("/inventory")
def get_inventory(db: Session = Depends(get_db)):
    return inventory(db)


@router.get("/zones/ranking")
def get_zone_ranking(db: Session = Depends(get_db)):
    try:
        return zone_rankings(db)
    except AnalysisTablesMissing as exc:
        raise _missing(exc) from exc


@router.get("/zones")
def get_zones(db: Session = Depends(get_db)):
    try:
        zones = zone_rankings(db)
        return zone_features(db, zones)
    except AnalysisTablesMissing as exc:
        raise _missing(exc) from exc


@router.get("/report")
def get_report(db: Session = Depends(get_db)):
    try:
        return build_report(db)
    except AnalysisTablesMissing as exc:
        raise _missing(exc) from exc


@router.get("/report.md")
def get_report_markdown(db: Session = Depends(get_db)):
    try:
        report = build_report(db)
    except AnalysisTablesMissing as exc:
        raise _missing(exc) from exc
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(render_report_markdown(report), media_type="text/markdown; charset=utf-8")
