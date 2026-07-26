-- Full pipeline for the live (current) accessibility result, then
-- register/freeze the paper baseline if it does not already exist.
--
-- Prerequisites: PostGIS + pgRouting enabled DB with input layers:
--   roads, population_blocks, urban_services
-- Optional layers used by the API: ahvaz_boundary, ahvaz_neighborhoods
--
-- From the sql/ directory:
--   psql -d YOUR_DB -f run_all.sql

\i 00_extensions.sql
\i 01_prepare_roads.sql
\i 02_connect_population_blocks.sql
\i 03_connect_urban_services.sql
\i 04_service_categories.sql
\i 05_reachable_vertices_15min.sql
\i 06_block_accessibility_15min.sql
\i 07_views.sql
\i 08_analysis_runs.sql
\i 09_freeze_paper_baseline.sql
