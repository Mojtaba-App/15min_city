"""Read-only summaries for the accessibility report.

The paper baseline table is only read. Score flags stay the official 0–4 index.
"""
from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

SCORE_LABELS = {
    0: "بحرانی",
    1: "ضعیف",
    2: "متوسط",
    3: "خوب",
    4: "عالی",
}

CATEGORIES = (
    ("education", "آموزش", "has_education"),
    ("health", "سلامت", "has_health"),
    ("shopping", "خرید", "has_shopping"),
    ("recreation", "تفریح", "has_recreation"),
)

# Types the current keyword rules leave in "other". Reported, not reclassified.
UNCLASSIFIED_HINTS = {
    "doctors": "health",
    "dentist": "health",
    "veterinary": "health",
    "chemist": "health",
    "college": "education",
    "university": "education",
    "library": "education",
    "cinema": "recreation",
    "camp_site": "recreation",
    "picnic_site": "recreation",
    "arts_centre": "recreation",
}

HINT_LABELS = {
    "health": "سلامت",
    "education": "آموزش",
    "recreation": "تفریح",
}


class AnalysisTablesMissing(RuntimeError):
    def __init__(self, tables: List[str]):
        self.tables = tables
        super().__init__("missing: " + ", ".join(tables))


def _int(value: Any) -> int:
    if value is None:
        return 0
    return int(round(float(value)))


def _flt(value: Any, digits: int = 2) -> float:
    if value is None:
        return 0.0
    return round(float(value), digits)


def _pct(part: float, whole: float) -> float:
    if not whole:
        return 0.0
    return round(100.0 * part / whole, 2)


def ensure_tables(db: Session) -> None:
    missing = []
    for name in ("block_service_supply", "block_zone"):
        found = db.execute(text("SELECT to_regclass(:name)"), {"name": f"public.{name}"}).scalar()
        if found is None:
            missing.append(name)
    if missing:
        raise AnalysisTablesMissing(missing)


def _groups(db: Session, sql: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    rows = db.execute(text(sql), params or {}).mappings().all()
    return [dict(row) for row in rows]


def summarize_groups(rows: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    buckets = {score: {"blocks": 0, "population": 0} for score in range(5)}
    coverage = {
        key: {"blocks": 0, "population": 0}
        for key, _label, _flag in CATEGORIES
    }
    combinations = []
    total_blocks = 0
    total_population = 0

    for row in rows:
        flags = {flag: _int(row[flag]) for _key, _label, flag in CATEGORIES}
        blocks = _int(row["blocks"])
        population = _int(row["population"])
        score = sum(flags.values())
        total_blocks += blocks
        total_population += population
        if score in buckets:
            buckets[score]["blocks"] += blocks
            buckets[score]["population"] += population
        for key, _label, flag in CATEGORIES:
            if flags[flag]:
                coverage[key]["blocks"] += blocks
                coverage[key]["population"] += population
        names = [label for _key, label, flag in CATEGORIES if flags[flag]]
        if not names:
            label = "بدون دسترسی"
        elif len(names) == 1:
            label = f"فقط {names[0]}"
        else:
            label = " + ".join(names)
        combinations.append({
            "label": label,
            "score": score,
            "has_education": flags["has_education"],
            "has_health": flags["has_health"],
            "has_shopping": flags["has_shopping"],
            "has_recreation": flags["has_recreation"],
            "blocks": blocks,
            "block_pct": _pct(blocks, 1),  # filled after the total is known
            "population": population,
            "population_pct": 0.0,
        })

    for item in combinations:
        item["block_pct"] = _pct(item["blocks"], total_blocks)
        item["population_pct"] = _pct(item["population"], total_population)
    combinations.sort(key=lambda item: (-item["blocks"], -item["score"]))

    score_rows = []
    cumulative_blocks = 0
    cumulative_population = 0
    weighted_mass = 0
    for score in range(5):
        blocks = buckets[score]["blocks"]
        population = buckets[score]["population"]
        cumulative_blocks += blocks
        cumulative_population += population
        weighted_mass += score * population
        score_rows.append({
            "score": score,
            "label": SCORE_LABELS[score],
            "blocks": blocks,
            "block_pct": _pct(blocks, total_blocks),
            "cumulative_blocks": cumulative_blocks,
            "cumulative_block_pct": _pct(cumulative_blocks, total_blocks),
            "population": population,
            "population_pct": _pct(population, total_population),
            "cumulative_population": cumulative_population,
            "cumulative_population_pct": _pct(cumulative_population, total_population),
        })

    exact_avg = (sum(row["score"] * row["blocks"] for row in score_rows) / total_blocks) if total_blocks else 0.0
    avg_score = round(exact_avg, 2)
    weighted_avg = round(weighted_mass / total_population, 3) if total_population else None

    return {
        "total_blocks": total_blocks,
        "total_population": total_population,
        "avg_score": avg_score,
        "avg_score_exact": round(exact_avg, 3),
        "weighted_avg_score": weighted_avg,
        "min_score": min((row["score"] for row in score_rows if row["blocks"]), default=0),
        "max_score": max((row["score"] for row in score_rows if row["blocks"]), default=0),
        "rows": score_rows,
        "combinations": combinations,
        "coverage": [
            {
                "key": key,
                "label": label,
                "blocks": coverage[key]["blocks"],
                "block_pct": _pct(coverage[key]["blocks"], total_blocks),
                "population": coverage[key]["population"],
                "population_pct": _pct(coverage[key]["population"], total_population),
            }
            for key, label, _flag in CATEGORIES
        ],
    }


BASELINE_GROUPS = """
    SELECT
        COALESCE(a.has_education, 0) AS has_education,
        COALESCE(a.has_health, 0) AS has_health,
        COALESCE(a.has_shopping, 0) AS has_shopping,
        COALESCE(a.has_recreation, 0) AS has_recreation,
        COUNT(*) AS blocks,
        COALESCE(SUM(p.population), 0) AS population
    FROM block_accessibility_15min a
    LEFT JOIN population_blocks p ON p.gid = a.block_gid
    GROUP BY 1, 2, 3, 4
"""

SCENARIO_GROUPS = """
    SELECT
        COALESCE(s.has_education, 0) AS has_education,
        COALESCE(s.has_health, 0) AS has_health,
        COALESCE(s.has_shopping, 0) AS has_shopping,
        COALESCE(s.has_recreation, 0) AS has_recreation,
        COUNT(*) AS blocks,
        COALESCE(SUM(p.population), 0) AS population
    FROM block_accessibility_scenarios s
    LEFT JOIN population_blocks p ON p.gid = s.block_gid
    WHERE s.run_code = :run_code
    GROUP BY 1, 2, 3, 4
"""

NO_RECREATION_GROUPS = """
    SELECT
        COALESCE(a.has_education, 0) AS has_education,
        COALESCE(a.has_health, 0) AS has_health,
        COALESCE(a.has_shopping, 0) AS has_shopping,
        0 AS has_recreation,
        COUNT(*) AS blocks,
        COALESCE(SUM(p.population), 0) AS population
    FROM block_accessibility_15min a
    LEFT JOIN population_blocks p ON p.gid = a.block_gid
    GROUP BY 1, 2, 3
"""


def baseline_summary(db: Session) -> Dict[str, Any]:
    return summarize_groups(_groups(db, BASELINE_GROUPS))


def _scenario(db: Session, run_code: str, scenario_id: str, label: str, seconds: int, note: str) -> Dict[str, Any]:
    summary = summarize_groups(_groups(db, SCENARIO_GROUPS, {"run_code": run_code}))
    summary.update({
        "id": scenario_id,
        "label": label,
        "threshold_sec": seconds,
        "note": note,
    })
    return summary


def sensitivity(db: Session) -> Dict[str, Any]:
    ensure_tables(db)
    paper = baseline_summary(db)
    paper.update({
        "id": "minutes_15",
        "label": "۱۵ دقیقه (مقاله)",
        "threshold_sec": 900,
        "note": "شاخص رسمی مقاله از جدول block_accessibility_15min.",
    })
    without = summarize_groups(_groups(db, NO_RECREATION_GROUPS))
    without.update({
        "id": "minutes_15_without_recreation",
        "label": "۱۵ دقیقه بدون تفریح",
        "threshold_sec": 900,
        "note": "همان شاخص مقاله پس از حذف دسته تفریح، برای دیدن اثر وزن برابر.",
    })
    scenarios = [
        _scenario(db, "scenario_10min", "minutes_10", "۱۰ دقیقه", 600, "از زمان سفر ذخیره‌شده با آستانه ۶۰۰ ثانیه."),
        paper,
        without,
        _scenario(db, "scenario_20min", "minutes_20", "۲۰ دقیقه", 1200, "ایزوکرون ۱۲۰۰ ثانیه‌ای جدید روی همان شبکه. جدول پایه مقاله تغییر نکرده است."),
    ]
    return {"scenarios": scenarios}


def supply_summary(db: Session) -> Dict[str, Any]:
    ensure_tables(db)
    row = db.execute(text("""
        SELECT
            COUNT(*) AS blocks,
            SUM(CASE WHEN s.n_education_15 = 0 THEN 1 ELSE 0 END) AS edu_0,
            SUM(CASE WHEN s.n_education_15 = 1 THEN 1 ELSE 0 END) AS edu_1,
            SUM(CASE WHEN s.n_education_15 >= 2 THEN 1 ELSE 0 END) AS edu_2,
            MAX(s.n_education_15) AS edu_max,
            SUM(CASE WHEN s.n_health_15 = 0 THEN 1 ELSE 0 END) AS health_0,
            SUM(CASE WHEN s.n_health_15 = 1 THEN 1 ELSE 0 END) AS health_1,
            SUM(CASE WHEN s.n_health_15 >= 2 THEN 1 ELSE 0 END) AS health_2,
            MAX(s.n_health_15) AS health_max,
            SUM(CASE WHEN s.n_shopping_15 = 0 THEN 1 ELSE 0 END) AS shop_0,
            SUM(CASE WHEN s.n_shopping_15 = 1 THEN 1 ELSE 0 END) AS shop_1,
            SUM(CASE WHEN s.n_shopping_15 >= 2 THEN 1 ELSE 0 END) AS shop_2,
            MAX(s.n_shopping_15) AS shop_max,
            SUM(CASE WHEN s.n_recreation_15 = 0 THEN 1 ELSE 0 END) AS rec_0,
            SUM(CASE WHEN s.n_recreation_15 = 1 THEN 1 ELSE 0 END) AS rec_1,
            SUM(CASE WHEN s.n_recreation_15 >= 2 THEN 1 ELSE 0 END) AS rec_2,
            MAX(s.n_recreation_15) AS rec_max,
            COALESCE(SUM(CASE WHEN s.n_education_15 >= 2 THEN p.population ELSE 0 END), 0) AS edu_pop_2,
            COALESCE(SUM(CASE WHEN s.n_health_15 >= 2 THEN p.population ELSE 0 END), 0) AS health_pop_2,
            COALESCE(SUM(CASE WHEN s.n_shopping_15 >= 2 THEN p.population ELSE 0 END), 0) AS shop_pop_2,
            COALESCE(SUM(CASE WHEN s.n_recreation_15 >= 2 THEN p.population ELSE 0 END), 0) AS rec_pop_2,
            COALESCE(SUM(p.population), 0) AS population
        FROM block_service_supply s
        LEFT JOIN population_blocks p ON p.gid = s.block_gid
    """)).mappings().one()
    total_blocks = _int(row["blocks"])
    total_population = _int(row["population"])
    specs = (
        ("education", "آموزش", "edu"),
        ("health", "سلامت", "health"),
        ("shopping", "خرید", "shop"),
        ("recreation", "تفریح", "rec"),
    )
    categories = []
    for key, label, prefix in specs:
        zero = _int(row[f"{prefix}_0"])
        one = _int(row[f"{prefix}_1"])
        two = _int(row[f"{prefix}_2"])
        pop_two = _int(row[f"{prefix}_pop_2"])
        categories.append({
            "key": key,
            "label": label,
            "blocks_with_0": zero,
            "blocks_with_1": one,
            "blocks_with_2_or_more": two,
            "block_pct_1": _pct(one, total_blocks),
            "block_pct_2_or_more": _pct(two, total_blocks),
            "population_with_2_or_more": pop_two,
            "population_pct_2_or_more": _pct(pop_two, total_population),
            "max_facilities": _int(row[f"{prefix}_max"]),
        })
    return {
        "threshold_sec": 900,
        "definition": "تعداد تسهیلات همان دسته که از رأس شبکه بلوک در ۹۰۰ ثانیه قابل دسترسی‌اند. این تعداد ظرفیت رسمی خدمت نیست.",
        "categories": categories,
    }


def reconciliation(db: Session) -> Dict[str, Any]:
    ensure_tables(db)
    row = db.execute(text("""
        SELECT
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
    """)).mappings().one()
    pairs = (
        ("education", "آموزش", "edu"),
        ("health", "سلامت", "health"),
        ("shopping", "خرید", "shop"),
        ("recreation", "تفریح", "rec"),
    )
    by_category = []
    matched = True
    for key, label, prefix in pairs:
        paper = _int(row[f"{prefix}_flag"])
        recount = _int(row[f"{prefix}_recount"])
        delta = recount - paper
        if delta != 0:
            matched = False
        by_category.append({
            "key": key,
            "label": label,
            "paper_blocks": paper,
            "recount_blocks": recount,
            "delta": delta,
        })
    return {
        "threshold_sec": 900,
        "paper_flags_match_recount": matched,
        "by_category": by_category,
    }


def inventory(db: Session) -> Dict[str, Any]:
    rows = db.execute(text("""
        SELECT category, service_ty, COUNT(*) AS facilities
        FROM service_categories
        GROUP BY category, service_ty
        ORDER BY category, facilities DESC, service_ty
    """)).mappings().all()
    by_category: Dict[str, Dict[str, Any]] = {}
    hints = []
    for row in rows:
        category = row["category"]
        service_type = row["service_ty"]
        count = _int(row["facilities"])
        bucket = by_category.setdefault(category, {"key": category, "facilities": 0, "types": []})
        bucket["facilities"] += count
        bucket["types"].append({"service_type": service_type, "facilities": count})
        suggested = UNCLASSIFIED_HINTS.get(service_type)
        if category == "other" and suggested:
            hints.append({
                "service_type": service_type,
                "facilities": count,
                "suggested_category": suggested,
                "suggested_label": HINT_LABELS[suggested],
            })
    order = ["education", "health", "shopping", "recreation", "other"]
    labels = {
        "education": "آموزش",
        "health": "سلامت",
        "shopping": "خرید",
        "recreation": "تفریح",
        "other": "خارج از چهار دسته",
    }
    categories = []
    for key in order:
        if key not in by_category:
            continue
        item = by_category[key]
        item["label"] = labels[key]
        categories.append(item)
    total = sum(item["facilities"] for item in categories)
    return {
        "total_facilities": total,
        "categories": categories,
        "unclassified_relevant": hints,
        "note": "امتیاز مقاله فقط چهار دسته آموزش، سلامت، خرید و تفریح را به کار می‌برد. انواع جدول دوم در داده هستند، اما قاعده کلیدواژه فعلی آن‌ها را وارد امتیاز نکرده است. این گزارش طبقه‌بندی را تغییر نمی‌دهد.",
    }


def _zone_row(row: Dict[str, Any], blocks: int, population: int) -> Dict[str, Any]:
    education = _int(row["education_blocks"])
    health = _int(row["health_blocks"])
    shopping = _int(row["shopping_blocks"])
    recreation = _int(row["recreation_blocks"])
    pop_weight = _int(row["pop_for_weight"])
    score_pop = float(row["score_pop"] or 0)
    weighted = round(score_pop / pop_weight, 3) if pop_weight else 0.0
    zero_blocks = _int(row["blocks_score_0"])
    zero_population = _int(row["population_score_0"])
    district = row.get("district_code")
    district_code = _int(district) if district is not None else None
    return {
        "blocks": blocks,
        "population": population,
        "avg_score": _flt(row["avg_score"], 3),
        "weighted_avg_score": weighted,
        "blocks_score_0": zero_blocks,
        "pct_score_0": _pct(zero_blocks, blocks),
        "population_score_0": zero_population,
        "pct_population_score_0": _pct(zero_population, population),
        "education_pct": _pct(education, blocks),
        "health_pct": _pct(health, blocks),
        "shopping_pct": _pct(shopping, blocks),
        "recreation_pct": _pct(recreation, blocks),
        "district_code": district_code,
        "district_label": f"منطقه {district_code}" if district_code is not None else "بدون منطقه",
    }


def zone_rankings(db: Session) -> Dict[str, Any]:
    ensure_tables(db)
    neighborhood_rows = db.execute(text("""
        SELECT
            z.neighborhood_gid,
            z.neighborhood_name,
            z.district_code,
            COUNT(*) AS blocks,
            COALESCE(SUM(p.population), 0) AS population,
            AVG(a.accessibility_score) AS avg_score,
            SUM(a.accessibility_score * COALESCE(p.population, 0)) AS score_pop,
            SUM(COALESCE(p.population, 0)) AS pop_for_weight,
            SUM(CASE WHEN a.accessibility_score = 0 THEN 1 ELSE 0 END) AS blocks_score_0,
            SUM(CASE WHEN a.accessibility_score = 0 THEN COALESCE(p.population, 0) ELSE 0 END) AS population_score_0,
            SUM(a.has_education) AS education_blocks,
            SUM(a.has_health) AS health_blocks,
            SUM(a.has_shopping) AS shopping_blocks,
            SUM(a.has_recreation) AS recreation_blocks,
            ST_Y(ST_Transform(ST_PointOnSurface(n.geom), 4326)) AS lat,
            ST_X(ST_Transform(ST_PointOnSurface(n.geom), 4326)) AS lon
        FROM block_zone z
        JOIN block_accessibility_15min a ON a.block_gid = z.block_gid
        JOIN neighborhoods n ON n.gid = z.neighborhood_gid
        LEFT JOIN population_blocks p ON p.gid = z.block_gid
        GROUP BY z.neighborhood_gid, z.neighborhood_name, z.district_code, n.gid
        ORDER BY z.neighborhood_name
    """)).mappings().all()

    neighborhoods = []
    for row in neighborhood_rows:
        blocks = _int(row["blocks"])
        population = _int(row["population"])
        item = _zone_row(dict(row), blocks, population)
        item.update({
            "neighborhood_gid": _int(row["neighborhood_gid"]),
            "name": row["neighborhood_name"],
            "lat": _flt(row["lat"], 6),
            "lon": _flt(row["lon"], 6),
        })
        neighborhoods.append(item)

    district_rows = db.execute(text("""
        SELECT
            z.district_code,
            COUNT(*) AS blocks,
            COALESCE(SUM(p.population), 0) AS population,
            AVG(a.accessibility_score) AS avg_score,
            SUM(a.accessibility_score * COALESCE(p.population, 0)) AS score_pop,
            SUM(COALESCE(p.population, 0)) AS pop_for_weight,
            SUM(CASE WHEN a.accessibility_score = 0 THEN 1 ELSE 0 END) AS blocks_score_0,
            SUM(CASE WHEN a.accessibility_score = 0 THEN COALESCE(p.population, 0) ELSE 0 END) AS population_score_0,
            SUM(a.has_education) AS education_blocks,
            SUM(a.has_health) AS health_blocks,
            SUM(a.has_shopping) AS shopping_blocks,
            SUM(a.has_recreation) AS recreation_blocks
        FROM block_zone z
        JOIN block_accessibility_15min a ON a.block_gid = z.block_gid
        LEFT JOIN population_blocks p ON p.gid = z.block_gid
        WHERE z.district_code IS NOT NULL
        GROUP BY z.district_code
        ORDER BY z.district_code
    """)).mappings().all()
    districts = []
    for row in district_rows:
        blocks = _int(row["blocks"])
        population = _int(row["population"])
        item = _zone_row(dict(row), blocks, population)
        districts.append(item)

    unmatched = db.execute(text("""
        SELECT
            COUNT(*) AS blocks,
            COALESCE(SUM(p.population), 0) AS population
        FROM block_accessibility_15min a
        LEFT JOIN block_zone z ON z.block_gid = a.block_gid
        LEFT JOIN population_blocks p ON p.gid = a.block_gid
        WHERE z.block_gid IS NULL
    """)).mappings().one()

    eligible = [item for item in neighborhoods if item["blocks"] >= 10]
    best = sorted(eligible, key=lambda item: (item["weighted_avg_score"], item["population"]), reverse=True)[:8]
    underserved = sorted(neighborhoods, key=lambda item: (item["weighted_avg_score"], -item["population"]))[:8]
    return {
        "neighborhoods": neighborhoods,
        "districts": districts,
        "unmatched_blocks": _int(unmatched["blocks"]),
        "unmatched_population": _int(unmatched["population"]),
        "highlights": {
            "best": best,
            "underserved": underserved,
            "best_rule": "بیشترین میانگین وزنی میان محله‌های دارای حداقل ۱۰ بلوک.",
            "underserved_rule": "کمترین میانگین وزنی، و در امتیاز برابر، جمعیت بیشتر.",
        },
    }


def examples(db: Session, zones: Dict[str, Any]) -> Dict[str, Any]:
    best = zones["highlights"]["best"][:3]
    zero_zones = [item for item in zones["neighborhoods"] if item["weighted_avg_score"] == 0]
    if zero_zones:
        zero_zone = max(zero_zones, key=lambda item: item["population"])
    else:
        zero_zone = zones["highlights"]["underserved"][0]
    block = db.execute(text("""
        SELECT
            a.block_gid,
            a.accessibility_score AS score,
            ROUND(a.distance_to_network::numeric, 1) AS distance_to_network,
            COALESCE(p.population, 0) AS population,
            z.neighborhood_name,
            z.district_code,
            COALESCE(s.n_education_15, 0) AS n_education,
            COALESCE(s.n_health_15, 0) AS n_health,
            COALESCE(s.n_shopping_15, 0) AS n_shopping,
            COALESCE(s.n_recreation_15, 0) AS n_recreation,
            ST_Y(ST_Transform(ST_PointOnSurface(a.geom), 4326)) AS lat,
            ST_X(ST_Transform(ST_PointOnSurface(a.geom), 4326)) AS lon
        FROM block_accessibility_15min a
        LEFT JOIN population_blocks p ON p.gid = a.block_gid
        LEFT JOIN block_zone z ON z.block_gid = a.block_gid
        LEFT JOIN block_service_supply s ON s.block_gid = a.block_gid
        WHERE a.accessibility_score = (
            SELECT MAX(accessibility_score) FROM block_accessibility_15min
        )
        ORDER BY
            (
                COALESCE(s.n_education_15, 0) + COALESCE(s.n_health_15, 0)
                + COALESCE(s.n_shopping_15, 0) + COALESCE(s.n_recreation_15, 0)
            ) DESC,
            COALESCE(p.population, 0) DESC
        LIMIT 1
    """)).mappings().one()
    district_code = block["district_code"]
    return {
        "best_neighborhoods": best,
        "zero_access_neighborhood": zero_zone,
        "highest_score_block": {
            "block_gid": _int(block["block_gid"]),
            "score": _int(block["score"]),
            "score_label": SCORE_LABELS.get(_int(block["score"]), ""),
            "population": _int(block["population"]),
            "distance_to_network": _flt(block["distance_to_network"], 1),
            "neighborhood": block["neighborhood_name"],
            "district_code": _int(district_code) if district_code is not None else None,
            "district_label": f"منطقه {_int(district_code)}" if district_code is not None else "بدون منطقه",
            "n_education": _int(block["n_education"]),
            "n_health": _int(block["n_health"]),
            "n_shopping": _int(block["n_shopping"]),
            "n_recreation": _int(block["n_recreation"]),
            "lat": _flt(block["lat"], 6),
            "lon": _flt(block["lon"], 6),
        },
    }


def zone_features(db: Session, zones: Dict[str, Any]) -> Dict[str, Any]:
    stats = {item["neighborhood_gid"]: item for item in zones["neighborhoods"]}
    rows = db.execute(text("""
        SELECT
            gid,
            name::text AS name,
            CAST(TRUNC(cod_mantag) AS integer) AS district_code,
            ST_AsGeoJSON(ST_Transform(ST_SimplifyPreserveTopology(geom, 5), 4326))::text AS geometry
        FROM neighborhoods
        WHERE geom IS NOT NULL
        ORDER BY name
    """)).mappings().all()
    features = []
    for row in rows:
        if not row["geometry"]:
            continue
        gid = _int(row["gid"])
        stat = stats.get(gid, {})
        district_code = _int(row["district_code"]) if row["district_code"] is not None else None
        features.append({
            "type": "Feature",
            "geometry": json.loads(row["geometry"]),
            "properties": {
                "neighborhood_gid": gid,
                "name": row["name"],
                "district_code": district_code,
                "district_label": f"منطقه {district_code}" if district_code is not None else "بدون منطقه",
                "blocks": stat.get("blocks", 0),
                "population": stat.get("population", 0),
                "avg_score": stat.get("avg_score", 0),
                "weighted_avg_score": stat.get("weighted_avg_score", 0),
                "pct_score_0": stat.get("pct_score_0", 0),
                "education_pct": stat.get("education_pct", 0),
                "health_pct": stat.get("health_pct", 0),
                "shopping_pct": stat.get("shopping_pct", 0),
                "recreation_pct": stat.get("recreation_pct", 0),
            },
        })

    district_stats = {item["district_code"]: item for item in zones["districts"]}
    district_rows = db.execute(text("""
        SELECT
            CAST(TRUNC(cod_mantag) AS integer) AS district_code,
            ST_AsGeoJSON(
                ST_Transform(ST_SimplifyPreserveTopology(ST_Union(geom), 8), 4326)
            )::text AS geometry
        FROM neighborhoods
        WHERE geom IS NOT NULL AND cod_mantag IS NOT NULL
        GROUP BY CAST(TRUNC(cod_mantag) AS integer)
        ORDER BY 1
    """)).mappings().all()
    district_features = []
    for row in district_rows:
        if not row["geometry"]:
            continue
        code = _int(row["district_code"])
        stat = district_stats.get(code, {})
        district_features.append({
            "type": "Feature",
            "geometry": json.loads(row["geometry"]),
            "properties": {
                "district_code": code,
                "name": f"منطقه {code}",
                "blocks": stat.get("blocks", 0),
                "population": stat.get("population", 0),
                "avg_score": stat.get("avg_score", 0),
                "weighted_avg_score": stat.get("weighted_avg_score", 0),
                "pct_score_0": stat.get("pct_score_0", 0),
            },
        })
    return {
        "neighborhoods": {"type": "FeatureCollection", "features": features},
        "districts": {"type": "FeatureCollection", "features": district_features},
    }


def build_report(db: Session) -> Dict[str, Any]:
    ensure_tables(db)
    distribution = baseline_summary(db)
    zones = zone_rankings(db)
    populated_blocks = _int(db.execute(text("""
        SELECT COUNT(*) FROM population_blocks WHERE COALESCE(population, 0) > 0
    """)).scalar())
    report = {
        "meta": {
            "city": "اهواز",
            "blocks": distribution["total_blocks"],
            "population": distribution["total_population"],
            "populated_blocks": populated_blocks,
            "unmatched_blocks": zones["unmatched_blocks"],
            "unmatched_population": zones["unmatched_population"],
            "avg_score": distribution["avg_score"],
            "avg_score_exact": distribution["avg_score_exact"],
            "weighted_avg_score": distribution["weighted_avg_score"],
            "min_score": distribution["min_score"],
            "max_score": distribution["max_score"],
            "walking_speed_mps": 1.2,
            "paper_threshold_sec": 900,
            "paper_baseline_preserved": True,
            "score_definition": "تعداد دسته‌های آموزش، سلامت، خرید و تفریح که دست‌کم یک خدمت آن‌ها در ۱۵ دقیقه پیاده در دسترس است. هر دسته وزن یک دارد.",
        },
        "distribution": distribution,
        "combinations": distribution["combinations"],
        "zones": {
            "neighborhoods": zones["neighborhoods"],
            "districts": zones["districts"],
            "highlights": zones["highlights"],
            "unmatched_blocks": zones["unmatched_blocks"],
            "unmatched_population": zones["unmatched_population"],
        },
        "examples": examples(db, zones),
        "sensitivity": sensitivity(db),
        "supply": supply_summary(db),
        "inventory": inventory(db),
        "reconciliation": reconciliation(db),
    }
    report["limitations"] = _limitations(report)
    return report


def _limitations(report: Dict[str, Any]) -> List[str]:
    meta = report["meta"]
    return [
        "شاخص ۰ تا ۴ وزن یکسانی به چهار دسته می‌دهد و فقط بودن یا نبودن دست‌کم یک خدمت را می‌سنجد، نه ظرفیت، کیفیت، امنیت یا ویژگی اجتماعی را.",
        "تعداد خدمت در دسترس در بخش عرضه آمده است. این تعداد تخت، زیربنا یا ظرفیت رسمی نیست.",
        (
            f"میانگین ساده {meta['avg_score']} (با سه رقم اعشار {meta['avg_score_exact']}) سهم بلوک‌هاست، شامل بلوک‌های بدون جمعیت. "
            f"میانگین وزنی با جمعیت {meta['weighted_avg_score']} سهم ساکنان است. "
            f"{meta['populated_blocks']} بلوک جمعیت مثبت دارند."
        ),
        (
            f"{meta['unmatched_blocks']} بلوک با جمعیت {meta['unmatched_population']} درون هیچ محله‌ای نیفتادند "
            "و در رتبه محله و منطقه نیستند، ولی در توزیع کل شهر هستند."
        ),
        "آستانه‌های ۱۰ و ۲۰ دقیقه و حذف تفریح آزمون حساسیت‌اند. جدول پایه مقاله و امتیاز ۱۵ دقیقه‌ای آن تغییر نکرده است.",
        "قاعده کلیدواژه، بخشی از انواع خدمات را در دسته other گذاشته است. پوشش پایین تفریح و سلامت را باید همراه با موجودی خدمات خواند.",
        "هندسه وب با ساده‌سازی حدود ۲ متر برای بلوک و ۵ متر برای محله نمایش داده می‌شود و در محاسبه امتیاز اثری ندارد.",
    ]
