-- Freeze the paper-presented Ahvaz result as an immutable snapshot.
-- Safe to re-run: if the snapshot already exists, it is left unchanged.

DO $$
DECLARE
    v_block_count   integer;
    v_service_count integer;
    v_avg_score     numeric(6, 2);
BEGIN
    IF to_regclass('public.block_accessibility_15min') IS NULL THEN
        RAISE EXCEPTION
            'block_accessibility_15min not found. Run sql/01–06 (or run_all.sql) before freezing the baseline.';
    END IF;

    SELECT COUNT(*) INTO v_block_count FROM block_accessibility_15min;
    IF v_block_count = 0 THEN
        RAISE EXCEPTION
            'block_accessibility_15min is empty. Populate results before freezing the paper baseline.';
    END IF;

    IF to_regclass('public.block_accessibility_15min_paper_baseline') IS NULL THEN
        CREATE TABLE block_accessibility_15min_paper_baseline AS
        SELECT * FROM block_accessibility_15min;

        CREATE INDEX idx_paper_baseline_gid
            ON block_accessibility_15min_paper_baseline (block_gid);
        CREATE INDEX idx_paper_baseline_score
            ON block_accessibility_15min_paper_baseline (accessibility_score);
        CREATE INDEX idx_paper_baseline_geom
            ON block_accessibility_15min_paper_baseline USING gist (geom);

        RAISE NOTICE
            'Created immutable snapshot block_accessibility_15min_paper_baseline (% rows).',
            v_block_count;
    ELSE
        SELECT COUNT(*) INTO v_block_count
        FROM block_accessibility_15min_paper_baseline;

        RAISE NOTICE
            'Paper baseline snapshot already exists (% rows). Left unchanged.',
            v_block_count;
    END IF;

    SELECT ROUND(AVG(COALESCE(accessibility_score, 0))::numeric, 2)
    INTO v_avg_score
    FROM block_accessibility_15min_paper_baseline;

    SELECT COUNT(*) INTO v_block_count
    FROM block_accessibility_15min_paper_baseline;

    IF to_regclass('public.urban_services') IS NOT NULL THEN
        SELECT COUNT(*) INTO v_service_count FROM urban_services;
    ELSE
        v_service_count := NULL;
    END IF;

    INSERT INTO analysis_runs (
        run_code,
        label,
        city,
        walking_speed_mps,
        time_threshold_sec,
        score_min,
        score_max,
        categories,
        pipeline_version,
        is_paper_baseline,
        result_table,
        block_count,
        service_count,
        avg_score,
        notes
    )
    VALUES (
        'paper_baseline_ahvaz',
        'Paper baseline — Ahvaz 15-minute pedestrian accessibility',
        'Ahvaz',
        1.2,
        900,
        0,
        4,
        ARRAY['education', 'health', 'shopping', 'recreation'],
        'sql/00-07',
        true,
        'block_accessibility_15min_paper_baseline',
        v_block_count,
        v_service_count,
        v_avg_score,
        'Frozen snapshot of results used for the presented paper. Do not DROP or overwrite this table.'
    )
    ON CONFLICT (run_code) DO UPDATE
    SET
        block_count = EXCLUDED.block_count,
        service_count = EXCLUDED.service_count,
        avg_score = EXCLUDED.avg_score,
        result_table = EXCLUDED.result_table,
        notes = EXCLUDED.notes
    WHERE analysis_runs.is_paper_baseline = true;
END $$;

CREATE OR REPLACE VIEW v_paper_baseline_accessibility AS
SELECT
    block_gid,
    nearest_vertex,
    distance_to_network,
    accessibility_score,
    has_education,
    has_health,
    has_shopping,
    has_recreation,
    geom
FROM block_accessibility_15min_paper_baseline;

COMMENT ON VIEW v_paper_baseline_accessibility IS
    'Read-only API/research contract over the frozen paper baseline snapshot.';

COMMENT ON TABLE block_accessibility_15min_paper_baseline IS
    'IMMUTABLE paper baseline. Re-running the live pipeline must not replace this table.';
