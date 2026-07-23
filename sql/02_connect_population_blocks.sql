ALTER TABLE population_blocks
ADD COLUMN IF NOT EXISTS nearest_vertex integer,
ADD COLUMN IF NOT EXISTS distance_to_network double precision;

DROP TABLE IF EXISTS tmp_block_nearest_vertex;

CREATE TEMP TABLE tmp_block_nearest_vertex AS
SELECT
    bp.gid AS block_gid,
    v.id AS vertex_id,
    ST_Distance(bp.pt, v.geom) AS dist
FROM (
    SELECT
        gid,
        ST_PointOnSurface(geom) AS pt
    FROM population_blocks
) bp
CROSS JOIN LATERAL (
    SELECT id, geom
    FROM roads_vertices
    ORDER BY bp.pt <-> geom
    LIMIT 1
) v;

UPDATE population_blocks b
SET
    nearest_vertex = t.vertex_id,
    distance_to_network = t.dist
FROM tmp_block_nearest_vertex t
WHERE b.gid = t.block_gid;

CREATE INDEX IF NOT EXISTS idx_population_blocks_nearest_vertex
ON population_blocks(nearest_vertex);

ANALYZE population_blocks;
