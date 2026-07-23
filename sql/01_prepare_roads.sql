ALTER TABLE roads
ADD COLUMN IF NOT EXISTS source integer,
ADD COLUMN IF NOT EXISTS target integer,
ADD COLUMN IF NOT EXISTS cost double precision,
ADD COLUMN IF NOT EXISTS reverse_cost double precision;

DROP TABLE IF EXISTS roads_vertices;

CREATE TABLE roads_vertices AS
WITH points AS (
    SELECT ST_StartPoint(ST_GeometryN(geom, 1)) AS geom FROM roads
    UNION
    SELECT ST_EndPoint(ST_GeometryN(geom, 1)) AS geom FROM roads
),
unique_points AS (
    SELECT DISTINCT
        ROUND(ST_X(geom)::numeric, 4) AS x,
        ROUND(ST_Y(geom)::numeric, 4) AS y,
        geom
    FROM points
)
SELECT
    ROW_NUMBER() OVER ()::integer AS id,
    x,
    y,
    geom
FROM unique_points;

CREATE UNIQUE INDEX IF NOT EXISTS idx_roads_vertices_id ON roads_vertices(id);
CREATE INDEX IF NOT EXISTS idx_roads_vertices_xy ON roads_vertices(x, y);
CREATE INDEX IF NOT EXISTS idx_roads_vertices_geom ON roads_vertices USING gist(geom);

UPDATE roads r
SET
    source = s.id,
    target = t.id
FROM roads_vertices s, roads_vertices t
WHERE ROUND(ST_X(ST_StartPoint(ST_GeometryN(r.geom, 1)))::numeric, 4) = s.x
  AND ROUND(ST_Y(ST_StartPoint(ST_GeometryN(r.geom, 1)))::numeric, 4) = s.y
  AND ROUND(ST_X(ST_EndPoint(ST_GeometryN(r.geom, 1)))::numeric, 4) = t.x
  AND ROUND(ST_Y(ST_EndPoint(ST_GeometryN(r.geom, 1)))::numeric, 4) = t.y;

UPDATE roads
SET
    cost = ST_Length(geom) / 1.2,
    reverse_cost = ST_Length(geom) / 1.2;

ALTER TABLE roads
ALTER COLUMN source TYPE integer USING source::integer,
ALTER COLUMN target TYPE integer USING target::integer;

CREATE INDEX IF NOT EXISTS idx_roads_source ON roads(source);
CREATE INDEX IF NOT EXISTS idx_roads_target ON roads(target);

ANALYZE roads;
ANALYZE roads_vertices;
