# 15-Minute City Accessibility Methodology

## Overview
This project measures pedestrian accessibility to essential urban services within a 15-minute walking threshold using PostgreSQL, PostGIS, and pgRouting.

## Inputs
- `roads`: pedestrian street network
- `population_blocks`: spatial units representing population blocks
- `urban_services`: urban facilities and service points

## Method
1. Build a routable network from `roads`
2. Generate network vertices from road endpoints
3. Assign `source`, `target`, and travel cost to each edge
4. Snap each population block to the nearest network vertex
5. Snap each service point to the nearest network vertex
6. Classify services into:
   - education
   - health
   - shopping
   - recreation
7. Run `pgr_drivingDistance` with a 900-second threshold
8. Compute per-block accessibility score from 0 to 4

## Accessibility Score
- `0`: no category accessible within 15 minutes
- `1`: one category accessible
- `2`: two categories accessible
- `3`: three categories accessible
- `4`: all four categories accessible


# Methodology

## Input Layers
- Road network
- Population blocks
- Urban services

## Workflow
1. Enable PostGIS and pgRouting
2. Build road vertices
3. Assign source and target to road segments
4. Compute walking travel cost
5. Snap blocks to nearest road vertex
6. Snap services to nearest road vertex
7. Classify services into four categories
8. Run 15-minute network reachability
9. Score each block from 0 to 4

## Threshold
- Walking speed: 1.2 m/s
- Time threshold: 900 seconds

## Reproducibility
Paper results are frozen via `sql/08_analysis_runs.sql` and `sql/09_freeze_paper_baseline.sql`.
See `docs/reproducibility.md`. The live API reads `v_block_accessibility_15min`; the paper snapshot is exposed as `v_paper_baseline_accessibility`.
