-- Phase C: neighborhood aggregation (optional).
-- Runs only when public.ahvaz_neighborhoods exists with columns name + geom.

DO $$
BEGIN
    IF to_regclass('public.ahvaz_neighborhoods') IS NULL THEN
        RAISE NOTICE 'ahvaz_neighborhoods not found — skipping neighborhood summary table.';
        RETURN;
    END IF;

    DROP TABLE IF EXISTS neighborhood_accessibility_summary CASCADE;

    CREATE TABLE neighborhood_accessibility_summary AS
    SELECT
        n.name AS neighborhood_name,
        COUNT(s.block_gid) AS block_count,
        ROUND(AVG(s.accessibility_score)::numeric, 2) AS avg_score,
        ROUND(100.0 * AVG(s.has_education)::numeric, 2) AS pct_education,
        ROUND(100.0 * AVG(s.has_health)::numeric, 2) AS pct_health,
        ROUND(100.0 * AVG(s.has_shopping)::numeric, 2) AS pct_shopping,
        ROUND(100.0 * AVG(s.has_recreation)::numeric, 2) AS pct_recreation,
        ROUND(AVG(s.time_education_sec)::numeric, 1) AS avg_time_education_sec,
        ROUND(AVG(s.time_health_sec)::numeric, 1) AS avg_time_health_sec,
        n.geom
    FROM ahvaz_neighborhoods n
    LEFT JOIN block_accessibility_scenarios s
        ON s.run_code = 'scenario_15min'
       AND ST_Intersects(ST_PointOnSurface(s.geom), n.geom)
    GROUP BY n.name, n.geom;

    CREATE INDEX idx_neighborhood_summary_geom
        ON neighborhood_accessibility_summary USING gist (geom);

    ANALYZE neighborhood_accessibility_summary;

    RAISE NOTICE 'Created neighborhood_accessibility_summary.';
END $$;
