DROP TABLE IF EXISTS reachable_vertices_15min;

CREATE TABLE reachable_vertices_15min AS
SELECT
    sc.category,
    dd.node AS vertex_id,
    MIN(dd.agg_cost) AS travel_time_sec
FROM service_categories sc
JOIN LATERAL pgr_drivingDistance(
    'SELECT gid::integer AS id, source::integer, target::integer, cost, reverse_cost
     FROM roads
     WHERE source IS NOT NULL AND target IS NOT NULL',
    sc.nearest_vertex,
    900,
    directed := false
) dd ON true
WHERE sc.category IN ('education', 'health', 'shopping', 'recreation')
  AND sc.nearest_vertex IS NOT NULL
GROUP BY sc.category, dd.node;

CREATE INDEX IF NOT EXISTS idx_reachable_vertices_15min_vertex
ON reachable_vertices_15min(vertex_id);

CREATE INDEX IF NOT EXISTS idx_reachable_vertices_15min_category
ON reachable_vertices_15min(category);

ANALYZE reachable_vertices_15min;
