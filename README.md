# 15-Minute City Accessibility Project

Pedestrian 15-minute accessibility analysis for Ahvaz using PostgreSQL, PostGIS, and pgRouting, with a FastAPI read layer and a Leaflet dashboard.

## Architecture (data layers)

| Layer | Objects | Rule |
|-------|---------|------|
| Inputs (raw) | `roads`, `population_blocks`, `urban_services` | Do not DROP in ad-hoc experiments |
| Derived (live) | `roads_vertices`, `service_categories`, `reachable_vertices_15min`, `block_accessibility_15min` | Rebuilt by `sql/run_all.sql` |
| API contract | `v_block_accessibility_15min` | Prefer this over selecting result tables |
| Paper baseline | `block_accessibility_15min_paper_baseline`, `v_paper_baseline_accessibility`, `analysis_runs` | Immutable snapshot of presented results |

## Paper baseline parameters

| Parameter | Value |
|-----------|--------|
| City | Ahvaz |
| Walking speed | 1.2 m/s |
| Time threshold | 900 seconds (15 minutes) |
| Score range | 0–4 |
| Categories | education, health, shopping, recreation |
| Run code | `paper_baseline_ahvaz` |

See [docs/reproducibility.md](docs/reproducibility.md) for freeze/backup steps.

## Prerequisites

- PostgreSQL with **PostGIS** and **pgRouting**
- Python 3.10+
- Input layers already loaded into the database (same CRS as your network)

Optional API layers: `ahvaz_boundary`, `ahvaz_neighborhoods`

## 1. Database setup

```bash
# Create DB (example name)
createdb fifteen_min_city

# From the sql/ directory — rebuilds live results, then freezes paper baseline if missing
cd sql
psql -d fifteen_min_city -f run_all.sql
```

If live results already exist and you only need Phase A objects:

```bash
cd sql
psql -d fifteen_min_city -f 07_views.sql
psql -d fifteen_min_city -f 08_analysis_runs.sql
psql -d fifteen_min_city -f 09_freeze_paper_baseline.sql
```

## 2. Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env   # Windows; or: cp .env.example .env
# Edit backend/.env with your DB credentials
```

Run the API:

```bash
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- OpenAPI docs: http://127.0.0.1:8000/docs  
- Root discovery: http://127.0.0.1:8000/  
- Paper baseline metadata: http://127.0.0.1:8000/accessibility/runs/baseline  

## 3. Frontend

Serve the static dashboard (do not rely on `file://` if CORS is restricted):

```bash
cd frontend
python -m http.server 5500
```

Open http://127.0.0.1:5500

API host/port: edit `frontend/config.js` (`API_ORIGIN`).

Allowed browser origins: `CORS_ORIGINS` in `backend/.env` (see `.env.example`).

## Accessibility score

- `0` = no category within 15 minutes  
- `1`–`3` = that many categories reachable  
- `4` = education + health + shopping + recreation  

## Main derived tables / views

- `block_accessibility_15min` — current live result  
- `v_block_accessibility_15min` — API contract over live result  
- `block_accessibility_15min_paper_baseline` — frozen paper snapshot  
- `v_paper_baseline_accessibility` — API/research contract over snapshot  
- `analysis_runs` — run registry (parameters + counts)  

## Docs

- [Methodology](docs/methodology.md)  
- [Reproducibility & baseline](docs/reproducibility.md)  
- [API contract](docs/api.md)  
- [Phase C scenarios & gaps](docs/phase_c.md)  

### Phase C (optional scientific add-on)

After the live pipeline + paper freeze:

```bash
cd sql
psql -d fifteen_min_city -f run_phase_c.sql
```

This builds travel times, 10/15-minute scenarios, and intervention gap candidates without modifying the paper baseline.
