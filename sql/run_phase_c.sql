-- Phase C add-on pipeline (does not rebuild paper baseline or live 01–09 tables).
-- Prerequisites: reachable_vertices_15min and population_blocks already populated.
--
--   psql -d fifteen_min_city -f run_phase_c.sql

\i 11_block_travel_times.sql
\i 12_scenario_accessibility.sql
\i 13_intervention_gaps.sql
\i 14_neighborhood_summary.sql
