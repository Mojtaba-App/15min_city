-- Analytical extensions for the Ahvaz 15-minute accessibility study.
-- Does not drop or overwrite block_accessibility_15min or the paper baseline.
-- Statements are split on lines that start with "-- STATEMENT".

-- STATEMENT assign neighborhood SRID
UPDATE neighborhoods
SET geom = ST_SetSRID(geom, 32639)
WHERE ST_SRID(geom) = 0;

-- STATEMENT service reachability at 20 minutes
DROP TABLE IF EXISTS reachable_service_vertices;

CREATE TABLE reachable_service_vertices AS
SELECT
    sc.gid AS service_gid,
    sc.category,
    dd.node AS vertex_id,
    dd.agg_cost AS travel_time_sec
FROM service_categories sc
JOIN LATERAL pgr_drivingDistance(
    'SELECT gid::integer AS id, source::integer, target::integer, cost, reverse_cost
     FROM roads
     WHERE source IS NOT NULL AND target IS NOT NULL',
    sc.nearest_vertex,
    1200,
    directed := false
) dd ON TRUE
WHERE sc.category IN ('education', 'health', 'shopping', 'recreation')
  AND sc.nearest_vertex IS NOT NULL;

CREATE INDEX idx_reachable_service_vertices_vertex
ON reachable_service_vertices (vertex_id);

CREATE INDEX idx_reachable_service_vertices_category
ON reachable_service_vertices (category, vertex_id);

ANALYZE reachable_service_vertices;

-- STATEMENT block service counts
DROP TABLE IF EXISTS block_service_supply;

CREATE TABLE block_service_supply AS
SELECT
    b.block_gid,
    COUNT(DISTINCT r.service_gid) FILTER (
        WHERE r.category = 'education' AND r.travel_time_sec <= 600
    )::integer AS n_education_10,
    COUNT(DISTINCT r.service_gid) FILTER (
        WHERE r.category = 'health' AND r.travel_time_sec <= 600
    )::integer AS n_health_10,
    COUNT(DISTINCT r.service_gid) FILTER (
        WHERE r.category = 'shopping' AND r.travel_time_sec <= 600
    )::integer AS n_shopping_10,
    COUNT(DISTINCT r.service_gid) FILTER (
        WHERE r.category = 'recreation' AND r.travel_time_sec <= 600
    )::integer AS n_recreation_10,
    COUNT(DISTINCT r.service_gid) FILTER (
        WHERE r.category = 'education' AND r.travel_time_sec <= 900
    )::integer AS n_education_15,
    COUNT(DISTINCT r.service_gid) FILTER (
        WHERE r.category = 'health' AND r.travel_time_sec <= 900
    )::integer AS n_health_15,
    COUNT(DISTINCT r.service_gid) FILTER (
        WHERE r.category = 'shopping' AND r.travel_time_sec <= 900
    )::integer AS n_shopping_15,
    COUNT(DISTINCT r.service_gid) FILTER (
        WHERE r.category = 'recreation' AND r.travel_time_sec <= 900
    )::integer AS n_recreation_15,
    COUNT(DISTINCT r.service_gid) FILTER (
        WHERE r.category = 'education' AND r.travel_time_sec <= 1200
    )::integer AS n_education_20,
    COUNT(DISTINCT r.service_gid) FILTER (
        WHERE r.category = 'health' AND r.travel_time_sec <= 1200
    )::integer AS n_health_20,
    COUNT(DISTINCT r.service_gid) FILTER (
        WHERE r.category = 'shopping' AND r.travel_time_sec <= 1200
    )::integer AS n_shopping_20,
    COUNT(DISTINCT r.service_gid) FILTER (
        WHERE r.category = 'recreation' AND r.travel_time_sec <= 1200
    )::integer AS n_recreation_20,
    MIN(r.travel_time_sec) FILTER (
        WHERE r.category = 'education' AND r.travel_time_sec <= 1200
    ) AS t_education_20,
    MIN(r.travel_time_sec) FILTER (
        WHERE r.category = 'health' AND r.travel_time_sec <= 1200
    ) AS t_health_20,
    MIN(r.travel_time_sec) FILTER (
        WHERE r.category = 'shopping' AND r.travel_time_sec <= 1200
    ) AS t_shopping_20,
    MIN(r.travel_time_sec) FILTER (
        WHERE r.category = 'recreation' AND r.travel_time_sec <= 1200
    ) AS t_recreation_20
FROM block_accessibility_15min b
LEFT JOIN reachable_service_vertices r
    ON r.vertex_id = b.nearest_vertex
GROUP BY b.block_gid;

ALTER TABLE block_service_supply ADD PRIMARY KEY (block_gid);

ANALYZE block_service_supply;

-- STATEMENT assign blocks to neighborhoods
DROP TABLE IF EXISTS block_zone;

CREATE TABLE block_zone AS
WITH pts AS (
    SELECT
        block_gid,
        ST_PointOnSurface(ST_MakeValid(geom)) AS pt
    FROM block_accessibility_15min
    WHERE geom IS NOT NULL
)
SELECT DISTINCT ON (p.block_gid)
    p.block_gid,
    n.gid AS neighborhood_gid,
    n.name::text AS neighborhood_name,
    CAST(TRUNC(n.cod_mantag) AS integer) AS district_code
FROM pts p
JOIN neighborhoods n
    ON ST_Intersects(n.geom, p.pt)
ORDER BY
    p.block_gid,
    ST_Contains(n.geom, p.pt) DESC,
    n.shape_area ASC NULLS LAST;

ALTER TABLE block_zone ADD PRIMARY KEY (block_gid);
CREATE INDEX idx_block_zone_neighborhood ON block_zone (neighborhood_gid);
CREATE INDEX idx_block_zone_district ON block_zone (district_code);

ANALYZE block_zone;

-- STATEMENT scenario 20 minutes
DELETE FROM block_accessibility_scenarios
WHERE run_code = 'scenario_20min';

INSERT INTO block_accessibility_scenarios (
    run_code,
    block_gid,
    nearest_vertex,
    distance_to_network,
    time_threshold_sec,
    has_education,
    has_health,
    has_shopping,
    has_recreation,
    accessibility_score,
    time_education_sec,
    time_health_sec,
    time_shopping_sec,
    time_recreation_sec,
    geom
)
SELECT
    'scenario_20min',
    b.block_gid,
    b.nearest_vertex,
    b.distance_to_network,
    1200,
    CASE WHEN s.n_education_20 > 0 THEN 1 ELSE 0 END,
    CASE WHEN s.n_health_20 > 0 THEN 1 ELSE 0 END,
    CASE WHEN s.n_shopping_20 > 0 THEN 1 ELSE 0 END,
    CASE WHEN s.n_recreation_20 > 0 THEN 1 ELSE 0 END,
    (
        CASE WHEN s.n_education_20 > 0 THEN 1 ELSE 0 END
        + CASE WHEN s.n_health_20 > 0 THEN 1 ELSE 0 END
        + CASE WHEN s.n_shopping_20 > 0 THEN 1 ELSE 0 END
        + CASE WHEN s.n_recreation_20 > 0 THEN 1 ELSE 0 END
    ),
    s.t_education_20,
    s.t_health_20,
    s.t_shopping_20,
    s.t_recreation_20,
    b.geom
FROM block_accessibility_15min b
JOIN block_service_supply s ON s.block_gid = b.block_gid;

-- STATEMENT register 20 minute run
DELETE FROM analysis_runs
WHERE run_code = 'scenario_20min';

INSERT INTO analysis_runs (
    run_code,
    label,
    time_threshold_sec,
    is_paper_baseline,
    result_table,
    block_count,
    service_count,
    avg_score,
    notes,
    pipeline_version
)
SELECT
    'scenario_20min',
    'Sensitivity — 20-minute walking threshold',
    1200,
    FALSE,
    'block_accessibility_scenarios',
    COUNT(*),
    (SELECT COUNT(*) FROM urban_services),
    ROUND(AVG(accessibility_score)::numeric, 2),
    '1200-second undirected pgr_drivingDistance on the paper network. The paper baseline table is unchanged.',
    'sql/08'
FROM block_accessibility_scenarios
WHERE run_code = 'scenario_20min';
