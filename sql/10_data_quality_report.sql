-- Read-only data quality checks for the Ahvaz 15-minute accessibility pipeline.
-- Safe to run anytime; does not modify tables.
--
--   psql -d fifteen_min_city -f 10_data_quality_report.sql
--
-- Prefer the API: GET /accessibility/data-quality

\echo '=== Population blocks snap coverage ==='
SELECT
    COUNT(*) AS total_blocks,
    COUNT(*) FILTER (WHERE nearest_vertex IS NULL) AS unsapped_blocks,
    ROUND(AVG(distance_to_network)::numeric, 2) AS avg_distance_m,
    ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY distance_to_network)::numeric, 2) AS p50_distance_m,
    ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY distance_to_network)::numeric, 2) AS p95_distance_m
FROM population_blocks;

\echo '=== Urban services snap coverage ==='
SELECT
    COUNT(*) AS total_services,
    COUNT(*) FILTER (WHERE nearest_vertex IS NULL) AS unsapped_services,
    ROUND(AVG(distance_to_network)::numeric, 2) AS avg_distance_m
FROM urban_services;

\echo '=== Service category distribution ==='
SELECT category, COUNT(*) AS n
FROM service_categories
GROUP BY category
ORDER BY n DESC;

\echo '=== Road topology completeness ==='
SELECT
    COUNT(*) AS total_edges,
    COUNT(*) FILTER (WHERE source IS NULL OR target IS NULL) AS incomplete_edges
FROM roads;

\echo '=== Accessibility score distribution (live view) ==='
SELECT
    COALESCE(accessibility_score, 0) AS score,
    COUNT(*) AS block_count
FROM v_block_accessibility_15min
GROUP BY COALESCE(accessibility_score, 0)
ORDER BY score;
