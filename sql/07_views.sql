-- Stable read contract for the API and dashboards.
-- Internal tables may change; consumers should query this view (or paper baseline view).
-- DROP + CREATE is required when column order/names of an existing view must change.

DROP VIEW IF EXISTS v_block_accessibility_15min;

CREATE VIEW v_block_accessibility_15min AS
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
FROM block_accessibility_15min;

COMMENT ON VIEW v_block_accessibility_15min IS
    'API contract view over the current accessibility result table. Prefer this over selecting the table directly.';
