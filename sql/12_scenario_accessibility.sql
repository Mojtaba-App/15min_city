-- Phase C: sensitivity scenarios from travel times (fixed walking speed 1.2 m/s).
-- scenario_10min = threshold 600s, scenario_15min = threshold 900s.
-- Paper baseline remains untouched.

CREATE TABLE IF NOT EXISTS analysis_runs (
    run_id              serial PRIMARY KEY,
    run_code            text NOT NULL UNIQUE,
    label               text NOT NULL,
    city                text NOT NULL DEFAULT 'Ahvaz',
    walking_speed_mps   double precision NOT NULL DEFAULT 1.2,
    time_threshold_sec  integer NOT NULL DEFAULT 900,
    score_min           integer NOT NULL DEFAULT 0,
    score_max           integer NOT NULL DEFAULT 4,
    categories          text[] NOT NULL DEFAULT ARRAY[
        'education', 'health', 'shopping', 'recreation'
    ],
    pipeline_version    text NOT NULL DEFAULT 'sql/00-07',
    is_paper_baseline   boolean NOT NULL DEFAULT false,
    result_table        text,
    block_count         integer,
    service_count       integer,
    avg_score           numeric(6, 2),
    notes               text,
    created_at          timestamptz NOT NULL DEFAULT now()
);

DROP TABLE IF EXISTS block_accessibility_scenarios CASCADE;

CREATE TABLE block_accessibility_scenarios (
    run_code            text NOT NULL,
    block_gid           integer NOT NULL,
    nearest_vertex      integer,
    distance_to_network double precision,
    time_threshold_sec  integer NOT NULL,
    has_education       integer NOT NULL DEFAULT 0,
    has_health          integer NOT NULL DEFAULT 0,
    has_shopping        integer NOT NULL DEFAULT 0,
    has_recreation      integer NOT NULL DEFAULT 0,
    accessibility_score integer NOT NULL DEFAULT 0,
    time_education_sec  double precision,
    time_health_sec     double precision,
    time_shopping_sec   double precision,
    time_recreation_sec double precision,
    geom                geometry,
    PRIMARY KEY (run_code, block_gid)
);

INSERT INTO block_accessibility_scenarios (
    run_code, block_gid, nearest_vertex, distance_to_network, time_threshold_sec,
    has_education, has_health, has_shopping, has_recreation, accessibility_score,
    time_education_sec, time_health_sec, time_shopping_sec, time_recreation_sec, geom
)
SELECT
    s.run_code,
    t.block_gid,
    t.nearest_vertex,
    t.distance_to_network,
    s.threshold_sec,
    CASE WHEN t.time_education_sec  IS NOT NULL AND t.time_education_sec  <= s.threshold_sec THEN 1 ELSE 0 END,
    CASE WHEN t.time_health_sec     IS NOT NULL AND t.time_health_sec     <= s.threshold_sec THEN 1 ELSE 0 END,
    CASE WHEN t.time_shopping_sec   IS NOT NULL AND t.time_shopping_sec   <= s.threshold_sec THEN 1 ELSE 0 END,
    CASE WHEN t.time_recreation_sec IS NOT NULL AND t.time_recreation_sec <= s.threshold_sec THEN 1 ELSE 0 END,
    (
        CASE WHEN t.time_education_sec  IS NOT NULL AND t.time_education_sec  <= s.threshold_sec THEN 1 ELSE 0 END +
        CASE WHEN t.time_health_sec     IS NOT NULL AND t.time_health_sec     <= s.threshold_sec THEN 1 ELSE 0 END +
        CASE WHEN t.time_shopping_sec   IS NOT NULL AND t.time_shopping_sec   <= s.threshold_sec THEN 1 ELSE 0 END +
        CASE WHEN t.time_recreation_sec IS NOT NULL AND t.time_recreation_sec <= s.threshold_sec THEN 1 ELSE 0 END
    ),
    t.time_education_sec,
    t.time_health_sec,
    t.time_shopping_sec,
    t.time_recreation_sec,
    t.geom
FROM block_travel_times t
CROSS JOIN (
    VALUES
        ('scenario_10min', 600),
        ('scenario_15min', 900)
) AS s(run_code, threshold_sec);

CREATE INDEX idx_scenario_score ON block_accessibility_scenarios (run_code, accessibility_score);
CREATE INDEX idx_scenario_geom ON block_accessibility_scenarios USING gist (geom);

ANALYZE block_accessibility_scenarios;

CREATE OR REPLACE VIEW v_block_accessibility_scenarios AS
SELECT
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
FROM block_accessibility_scenarios;

-- Register / refresh scenario metadata (never paper baseline alone)
INSERT INTO analysis_runs (
    run_code, label, city, walking_speed_mps, time_threshold_sec,
    pipeline_version, is_paper_baseline, result_table,
    block_count, service_count, avg_score, notes
)
SELECT
    s.run_code,
    s.label,
    'Ahvaz',
    1.2,
    s.threshold_sec,
    'sql/11-12',
    false,
    'block_accessibility_scenarios',
    stats.block_count,
    (SELECT COUNT(*) FROM urban_services),
    stats.avg_score,
    s.notes
FROM (
    VALUES
        (
            'scenario_10min',
            600,
            'Sensitivity — 10-minute walking threshold',
            'Derived from travel times; not the paper baseline.'
        ),
        (
            'scenario_15min',
            900,
            'Sensitivity — 15-minute walking threshold',
            'Derived from travel times at the paper threshold for comparison.'
        )
) AS s(run_code, threshold_sec, label, notes)
JOIN LATERAL (
    SELECT
        COUNT(*) AS block_count,
        ROUND(AVG(accessibility_score)::numeric, 2) AS avg_score
    FROM block_accessibility_scenarios
    WHERE run_code = s.run_code
) stats ON true
ON CONFLICT (run_code) DO UPDATE
SET
    label = EXCLUDED.label,
    time_threshold_sec = EXCLUDED.time_threshold_sec,
    pipeline_version = EXCLUDED.pipeline_version,
    result_table = EXCLUDED.result_table,
    block_count = EXCLUDED.block_count,
    service_count = EXCLUDED.service_count,
    avg_score = EXCLUDED.avg_score,
    notes = EXCLUDED.notes;

COMMENT ON TABLE block_accessibility_scenarios IS
    'Phase C multi-threshold accessibility scores. Paper baseline table must not be overwritten.';
