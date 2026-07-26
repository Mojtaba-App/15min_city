-- Reproducibility registry: parameters and provenance for each analysis run.
-- The paper baseline row is frozen by 09_freeze_paper_baseline.sql.

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

CREATE INDEX IF NOT EXISTS idx_analysis_runs_baseline
    ON analysis_runs (is_paper_baseline)
    WHERE is_paper_baseline = true;

COMMENT ON TABLE analysis_runs IS
    'Registry of accessibility analysis runs (parameters + counts). Paper baseline must remain immutable.';
