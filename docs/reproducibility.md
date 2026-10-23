# Reproducibility — Paper Baseline

This project separates **live recomputation** from the **immutable paper baseline**.

## Why

Re-running `sql/01–06` rebuilds `block_accessibility_15min`. Without a freeze step, presented paper numbers can be overwritten silently.

## What gets frozen

| Object | Role |
|--------|------|
| `block_accessibility_15min_paper_baseline` | Full geometric + score snapshot |
| `v_paper_baseline_accessibility` | Stable read view over the snapshot |
| `analysis_runs` row `paper_baseline_ahvaz` | Parameters, counts, provenance |

## Freeze (safe to re-run)

From `sql/` after live results exist:

```bash
psql -d fifteen_min_city -f 08_analysis_runs.sql
psql -d fifteen_min_city -f 09_freeze_paper_baseline.sql
```

Behavior of `09_freeze_paper_baseline.sql`:

- If the snapshot table **does not exist** → create it from current `block_accessibility_15min` and register the run.
- If it **already exists** → leave the snapshot unchanged (only refresh registry counts from the existing snapshot).

**Do not** `DROP TABLE block_accessibility_15min_paper_baseline` unless you intentionally discard the paper freeze.

## File backup (recommended)

After freezing, export a durable copy under `outputs/`:

```bash
# From repo root (adjust DB name / path)
mkdir outputs
pg_dump -d fifteen_min_city -t block_accessibility_15min_paper_baseline -t analysis_runs -Fc -f outputs/paper_baseline_ahvaz.dump
```

Restore later:

```bash
pg_restore -d fifteen_min_city --clean --if-exists outputs/paper_baseline_ahvaz.dump
```

Optional GeoJSON export of the baseline view:

```bash
psql -d fifteen_min_city -c "COPY (
  SELECT jsonb_pretty(jsonb_build_object(
    'type', 'FeatureCollection',
    'features', COALESCE(jsonb_agg(
      jsonb_build_object(
        'type', 'Feature',
        'geometry', ST_AsGeoJSON(ST_Transform(geom, 4326))::jsonb,
        'properties', jsonb_build_object(
          'block_gid', block_gid,
          'score', accessibility_score,
          'has_education', has_education,
          'has_health', has_health,
          'has_shopping', has_shopping,
          'has_recreation', has_recreation
        )
      )
    ), '[]'::jsonb)
  ))
  FROM v_paper_baseline_accessibility
) TO STDOUT" > outputs/paper_baseline_ahvaz.geojson
```

(For very large exports, prefer `pg_dump` over a single GeoJSON file.)

## Verify

```sql
SELECT run_code, walking_speed_mps, time_threshold_sec,
       block_count, avg_score, result_table, is_paper_baseline
FROM analysis_runs
WHERE is_paper_baseline;

SELECT COUNT(*), ROUND(AVG(accessibility_score)::numeric, 2)
FROM block_accessibility_15min_paper_baseline;
```

API checks:

- `GET /accessibility/runs`
- `GET /accessibility/runs/baseline`
- `GET /accessibility/geojson?source=paper_baseline&limit=100`

## Layer rules

1. **Inputs** (`roads`, `population_blocks`, `urban_services`) — treat as raw; do not DROP casually.  
2. **Live derived** — may be rebuilt by the SQL pipeline.  
3. **Paper baseline** — immutable; new scientific scenarios must become new `analysis_runs` rows / tables, not overwrites of the baseline.  
