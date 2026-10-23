DROP TABLE IF EXISTS block_accessibility_15min;

CREATE TABLE block_accessibility_15min AS
SELECT
    b.gid AS block_gid,
    b.nearest_vertex,
    b.distance_to_network,
    b.geom,

    CASE WHEN COUNT(*) FILTER (WHERE rv.category = 'education') > 0 THEN 1 ELSE 0 END AS has_education,
    CASE WHEN COUNT(*) FILTER (WHERE rv.category = 'health') > 0 THEN 1 ELSE 0 END AS has_health,
    CASE WHEN COUNT(*) FILTER (WHERE rv.category = 'shopping') > 0 THEN 1 ELSE 0 END AS has_shopping,
    CASE WHEN COUNT(*) FILTER (WHERE rv.category = 'recreation') > 0 THEN 1 ELSE 0 END AS has_recreation,

    (
        CASE WHEN COUNT(*) FILTER (WHERE rv.category = 'education') > 0 THEN 1 ELSE 0 END +
        CASE WHEN COUNT(*) FILTER (WHERE rv.category = 'health') > 0 THEN 1 ELSE 0 END +
        CASE WHEN COUNT(*) FILTER (WHERE rv.category = 'shopping') > 0 THEN 1 ELSE 0 END +
        CASE WHEN COUNT(*) FILTER (WHERE rv.category = 'recreation') > 0 THEN 1 ELSE 0 END
    ) AS accessibility_score
FROM population_blocks b
LEFT JOIN reachable_vertices_15min rv
    ON b.nearest_vertex = rv.vertex_id
GROUP BY
    b.gid,
    b.nearest_vertex,
    b.distance_to_network,
    b.geom;

CREATE INDEX IF NOT EXISTS idx_block_accessibility_15min_gid
ON block_accessibility_15min(block_gid);

CREATE INDEX IF NOT EXISTS idx_block_accessibility_15min_vertex
ON block_accessibility_15min(nearest_vertex);

CREATE INDEX IF NOT EXISTS idx_block_accessibility_15min_score
ON block_accessibility_15min(accessibility_score);

CREATE INDEX IF NOT EXISTS idx_block_accessibility_15min_geom
ON block_accessibility_15min USING gist(geom);

ANALYZE block_accessibility_15min;
