-- Phase C: per-block minimum network travel time to each service category.
-- Derived from existing reachable_vertices_15min (times are capped at the 900s catch).
-- Does NOT modify the paper baseline.

DROP TABLE IF EXISTS block_travel_times CASCADE;

CREATE TABLE block_travel_times AS
SELECT
    b.gid AS block_gid,
    b.nearest_vertex,
    b.distance_to_network,
    b.geom,
    MIN(rv.travel_time_sec) FILTER (WHERE rv.category = 'education')  AS time_education_sec,
    MIN(rv.travel_time_sec) FILTER (WHERE rv.category = 'health')     AS time_health_sec,
    MIN(rv.travel_time_sec) FILTER (WHERE rv.category = 'shopping')   AS time_shopping_sec,
    MIN(rv.travel_time_sec) FILTER (WHERE rv.category = 'recreation') AS time_recreation_sec
FROM population_blocks b
LEFT JOIN reachable_vertices_15min rv
    ON b.nearest_vertex = rv.vertex_id
GROUP BY
    b.gid,
    b.nearest_vertex,
    b.distance_to_network,
    b.geom;

CREATE UNIQUE INDEX idx_block_travel_times_gid ON block_travel_times (block_gid);
CREATE INDEX idx_block_travel_times_geom ON block_travel_times USING gist (geom);

ANALYZE block_travel_times;

COMMENT ON TABLE block_travel_times IS
    'Phase C: min walking time (sec) from each block to nearest reachable service per category (within the precomputed catch).';

CREATE OR REPLACE VIEW v_block_travel_times AS
SELECT
    block_gid,
    nearest_vertex,
    distance_to_network,
    time_education_sec,
    time_health_sec,
    time_shopping_sec,
    time_recreation_sec,
    geom
FROM block_travel_times;
