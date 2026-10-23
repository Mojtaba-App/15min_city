"""Build additive analysis tables. The paper baseline is not modified."""
import re
import time
from pathlib import Path

from sqlalchemy import create_engine, text

from app.config import DATABASE_URL

SQL_PATH = Path(__file__).resolve().parents[1] / "sql" / "08_analysis_extensions.sql"


def statements(sql: str) -> list[tuple[str, str]]:
    parts = re.split(r"(?m)^-- STATEMENT (.+)$", sql)
    named = []
    index = 1
    while index + 1 < len(parts):
        name = parts[index].strip()
        chunks = [part.strip() for part in parts[index + 1].split(";") if part.strip()]
        for chunk_index, chunk in enumerate(chunks, start=1):
            label = name if len(chunks) == 1 else f"{name} ({chunk_index}/{len(chunks)})"
            named.append((label, chunk))
        index += 2
    return named


def main() -> None:
    engine = create_engine(DATABASE_URL)
    sql = SQL_PATH.read_text(encoding="utf-8")
    with engine.connect() as conn:
        border = conn.execute(text("""
            SELECT ST_SRID(geom) AS srid,
                   ST_XMin(ST_Extent(geom)) AS xmin,
                   ST_YMin(ST_Extent(geom)) AS ymin
            FROM city_border
            GROUP BY ST_SRID(geom)
        """)).mappings().first()
        print("city_border", dict(border) if border else None)

    for name, body in statements(sql):
        started = time.perf_counter()
        print(f"running: {name}")
        with engine.begin() as conn:
            conn.execute(text("SET statement_timeout = '15min'"))
            conn.execute(text(body))
        print(f"  done in {time.perf_counter() - started:.1f}s")

    with engine.connect() as conn:
        check = conn.execute(text("""
            SELECT
                COUNT(*) AS blocks,
                SUM(a.has_education) AS edu_flag,
                SUM((s.n_education_15 > 0)::int) AS edu_recount,
                SUM(a.has_health) AS health_flag,
                SUM((s.n_health_15 > 0)::int) AS health_recount,
                SUM(a.has_shopping) AS shop_flag,
                SUM((s.n_shopping_15 > 0)::int) AS shop_recount,
                SUM(a.has_recreation) AS rec_flag,
                SUM((s.n_recreation_15 > 0)::int) AS rec_recount
            FROM block_service_supply s
            JOIN block_accessibility_15min a USING (block_gid)
        """)).mappings().first()
        zones = conn.execute(text("""
            SELECT
                (SELECT COUNT(*) FROM block_zone) AS matched,
                (SELECT COUNT(*) FROM block_accessibility_15min) AS blocks,
                (SELECT COUNT(*) FROM reachable_service_vertices) AS reached_rows,
                (SELECT ROUND(AVG(accessibility_score)::numeric, 3)
                 FROM block_accessibility_scenarios
                 WHERE run_code = 'scenario_20min') AS avg_20
        """)).mappings().first()
        print("reconciliation", dict(check))
        print("zones", dict(zones))


if __name__ == "__main__":
    main()
