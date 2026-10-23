# API Contract

Base URL (local): `http://127.0.0.1:8000`

Interactive docs: `/docs`

## Data contract

| Consumer purpose | Object |
|------------------|--------|
| Current / live map & stats | View `v_block_accessibility_15min` |
| Paper baseline map | View `v_paper_baseline_accessibility` |
| Run parameters & provenance | Table `analysis_runs` |

The API **must not** recompute routing; it only reads precomputed views/tables.

### View columns

- `block_gid`
- `nearest_vertex`
- `distance_to_network`
- `accessibility_score` (0–4)
- `has_education`, `has_health`, `has_shopping`, `has_recreation` (0/1)
- `geom`

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Discovery + data contract hints |
| GET | `/health` | Liveness + database ping |
| GET | `/accessibility/summary` | Totals, avg/min/max score, category coverage |
| GET | `/accessibility/histogram` | Score distribution |
| GET | `/accessibility/geojson` | FeatureCollection (filters below) |
| GET | `/accessibility/map` | **Deprecated** alias of `/geojson` |
| GET | `/accessibility/runs` | All registered analysis runs |
| GET | `/accessibility/runs/baseline` | Frozen paper baseline metadata |
| GET | `/accessibility/data-quality` | Read-only snap/topology/classification checks |
| GET | `/accessibility/boundary` | City boundary GeoJSON (`ahvaz_boundary`; empty if table missing) |
| GET | `/accessibility/neighborhoods` | Neighborhoods GeoJSON (`ahvaz_neighborhoods`; empty if table missing) |

### `/accessibility/geojson` query params

| Param | Default | Notes |
|-------|---------|--------|
| `min_score` | — | 0–4 |
| `max_score` | — | 0–4 |
| `only_unserved` | `false` | score = 0 |
| `missing_category` | — | `education` \| `health` \| `shopping` \| `recreation` |
| `limit` | `3000` | 1–20000 |
| `source` | `current` | `current` \| `paper_baseline` \| `scenario_10min` \| `scenario_15min` |

### Phase C endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/accessibility/compare` | Compare two scenarios (`base`, `other`) |
| GET | `/accessibility/gaps/geojson` | Priority intervention candidate points |
| GET | `/accessibility/neighborhoods/summary` | Neighborhood aggregates (if built) |

See [phase_c.md](phase_c.md).

### Frontend config

Edit `frontend/config.js` (`API_ORIGIN`) if the backend is not on `http://127.0.0.1:8000`.
Serve the frontend over HTTP (e.g. port 5500) so CORS matches `CORS_ORIGINS` in `backend/.env`.
