CREATE OR REPLACE VIEW v_block_accessibility_15min AS
SELECT
    block_gid,
    accessibility_score,
    has_education,
    has_health,
    has_shopping,
    has_recreation,
    distance_to_network,
    geom
FROM block_accessibility_15min;
