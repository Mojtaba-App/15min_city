-- Phase C: intervention / gap prioritization (heuristic, not an optimization solver).
-- Ranks under-served blocks and exposes candidate points (block representative points).

DROP TABLE IF EXISTS intervention_gaps CASCADE;

CREATE TABLE intervention_gaps AS
SELECT
    t.block_gid,
    COALESCE(sc.accessibility_score, 0) AS accessibility_score,
    COALESCE(sc.has_education, 0) AS has_education,
    COALESCE(sc.has_health, 0) AS has_health,
    COALESCE(sc.has_shopping, 0) AS has_shopping,
    COALESCE(sc.has_recreation, 0) AS has_recreation,
    (
        (CASE WHEN COALESCE(sc.has_education, 0) = 0 THEN 1 ELSE 0 END) +
        (CASE WHEN COALESCE(sc.has_health, 0) = 0 THEN 1 ELSE 0 END) +
        (CASE WHEN COALESCE(sc.has_shopping, 0) = 0 THEN 1 ELSE 0 END) +
        (CASE WHEN COALESCE(sc.has_recreation, 0) = 0 THEN 1 ELSE 0 END)
    ) AS missing_count,
    (
        (CASE WHEN COALESCE(sc.has_education, 0) = 0 THEN 3 ELSE 0 END) +
        (CASE WHEN COALESCE(sc.has_health, 0) = 0 THEN 3 ELSE 0 END) +
        (CASE WHEN COALESCE(sc.has_shopping, 0) = 0 THEN 2 ELSE 0 END) +
        (CASE WHEN COALESCE(sc.has_recreation, 0) = 0 THEN 2 ELSE 0 END)
    ) AS priority_score,
    t.time_education_sec,
    t.time_health_sec,
    t.time_shopping_sec,
    t.time_recreation_sec,
    ST_PointOnSurface(t.geom) AS candidate_geom,
    t.geom
FROM block_travel_times t
LEFT JOIN block_accessibility_scenarios sc
    ON sc.run_code = 'scenario_15min'
   AND sc.block_gid = t.block_gid
WHERE COALESCE(sc.accessibility_score, 0) < 4;

CREATE INDEX idx_intervention_gaps_priority
    ON intervention_gaps (priority_score DESC, missing_count DESC);
CREATE INDEX idx_intervention_gaps_candidate
    ON intervention_gaps USING gist (candidate_geom);
CREATE INDEX idx_intervention_gaps_geom
    ON intervention_gaps USING gist (geom);

ANALYZE intervention_gaps;

CREATE OR REPLACE VIEW v_intervention_gap_points AS
SELECT
    block_gid,
    accessibility_score,
    missing_count,
    priority_score,
    has_education,
    has_health,
    has_shopping,
    has_recreation,
    candidate_geom AS geom
FROM intervention_gaps
WHERE candidate_geom IS NOT NULL;

COMMENT ON TABLE intervention_gaps IS
    'Phase C heuristic gap ranking for under-served blocks. Candidate points are block representatives, not optimized facility sites.';
