ALTER TABLE urban_services
ADD COLUMN IF NOT EXISTS nearest_vertex integer,
ADD COLUMN IF NOT EXISTS distance_to_network double precision;

DROP TABLE IF EXISTS tmp_service_nearest_vertex;

CREATE TEMP TABLE tmp_service_nearest_vertex AS
SELECT
    sp.gid AS service_gid,
    v.id AS vertex_id,
    ST_Distance(sp.pt, v.geom) AS dist
FROM (
    SELECT
        gid,
        geom AS pt
    FROM urban_services
    WHERE geom IS NOT NULL
) sp
CROSS JOIN LATERAL (
    SELECT id, geom
    FROM roads_vertices
    ORDER BY sp.pt <-> geom
    LIMIT 1
) v;

UPDATE urban_services s
SET
    nearest_vertex = t.vertex_id,
    distance_to_network = t.dist
FROM tmp_service_nearest_vertex t
WHERE s.gid = t.service_gid;

CREATE INDEX IF NOT EXISTS idx_urban_services_nearest_vertex
ON urban_services(nearest_vertex);

CREATE INDEX IF NOT EXISTS idx_urban_services_service_ty
ON urban_services(service_ty);

ANALYZE urban_services;
