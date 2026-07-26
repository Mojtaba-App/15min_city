# Phase C — Scenarios, Travel Times, Gaps

Phase C extends the locked paper baseline with **non-destructive** scientific add-ons.

## What was added

| Object | Role |
|--------|------|
| `block_travel_times` | Min walking time (sec) to each category (from existing 900s catch) |
| `block_accessibility_scenarios` | Scores for `scenario_10min` (600s) and `scenario_15min` (900s) |
| `intervention_gaps` | Heuristic priority ranking + candidate points for under-served blocks |
| `neighborhood_accessibility_summary` | Optional; created only if `ahvaz_neighborhoods` exists |

Paper baseline tables/views are **not** overwritten.

## How scenarios work

Travel times come from `reachable_vertices_15min` (already computed at 900s).  
Shorter thresholds are derived by filtering `travel_time_sec <= threshold`:

- 10 minutes → 600 seconds  
- 15 minutes → 900 seconds  

A 20-minute scenario would need a new `pgr_drivingDistance` catch (not included by default).

## Apply

```bash
cd sql
psql -d fifteen_min_city -f run_phase_c.sql
```

Or from Python (with `backend/.env` configured), run the four SQL files in order: `11` → `14`.

## API

| Endpoint | Purpose |
|----------|---------|
| `GET /accessibility/summary?source=scenario_10min` | Scenario summary |
| `GET /accessibility/histogram?source=scenario_15min` | Scenario histogram |
| `GET /accessibility/geojson?source=scenario_10min` | Map + travel-time properties |
| `GET /accessibility/compare?base=scenario_10min&other=scenario_15min` | Sensitivity comparison |
| `GET /accessibility/gaps/geojson?limit=400&min_priority=6` | Intervention candidates |
| `GET /accessibility/neighborhoods/summary` | Neighborhood stats (if available) |

`source` values: `current` \| `paper_baseline` \| `scenario_10min` \| `scenario_15min`

## Dashboard

Use **منبع / سناریو** to switch thresholds, open the compare card for 10↔15 deltas, and optionally enable **نقاط اولویت مداخله**.

Gap points are a **planning triage heuristic** (weighted missing categories), not an optimized facility-location model.
