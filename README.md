# WildTrack

WildTrack is a wildlife monitoring operations tool with a React/Vite frontend and a FastAPI backend. Phase 4 adds spatial and temporal intelligence on top of the Phase 3 GPS simulator while keeping the frontend behind a service layer so screens can continue to use the same data shapes.

## Development setup

WildTrack runs as two local services:

- FastAPI backend: serves health checks, versioned API routes, and the development GPS simulator.
- Vite React frontend: serves the ranger operations UI and reads the backend through `VITE_API_BASE_URL`.

Install dependencies from the project root:

```bash
npm install
python -m pip install -r backend/requirements.txt
```

Configure environment variables in `.env`:

```bash
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_WS_BASE_URL=ws://localhost:8000/api/v1
VITE_MAP_STYLE_URL=https://tiles.openfreemap.org/styles/liberty
```

Backend database variables are also read from `.env`. Set these with your own local or hosted database values:

```bash
DATABASE_URL=
DATABASE_MIGRATION_URL=
MONGODB_URI=
MONGODB_DATABASE=
```

## Start the app

Start from the project root. First make sure PostgreSQL/PostGIS and MongoDB are reachable, then run the backend:

```bash
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Verify the backend health endpoint:

```bash
curl http://127.0.0.1:8000/health
```

Expected shape:

```json
{
  "status": "ok",
  "postgres": {
    "reachable": true,
    "postgis": true,
    "postgis_version": "..."
  },
  "mongodb": {
    "reachable": true,
    "database": "wildtrack"
  }
}
```

In a second terminal, start the frontend from the project root:

```bash
npm run dev
```

Open the local Vite URL shown in that terminal. The port is chosen by Vite unless you pin one in `vite.config.js`.

## Database setup

Run PostgreSQL/PostGIS migrations:

```bash
python -m alembic -c backend/alembic.ini upgrade head
```

Seed PostgreSQL/PostGIS and MongoDB:

```bash
python -m backend.app.seed.seed_all
```

Verify database connectivity, PostGIS, required tables, seed counts, and MongoDB event collections:

```bash
python -m backend.app.verify
```

PostgreSQL/PostGIS owns animals, devices, zones, forest boundary, observations, ECA rules, and alerts. MongoDB owns flexible event documents in `wildlife_events`, `boundary_events`, `sensor_events`, and `device_events`.

## Phase 3 API and simulator

Core APIs are mounted under `/api/v1`:

```text
GET  /api/v1/animals
GET  /api/v1/animals/{animal_id}
GET  /api/v1/animals/{animal_id}/location
GET  /api/v1/observations
GET  /api/v1/animals/{animal_id}/observations
GET  /api/v1/animals/{animal_id}/movement
GET  /api/v1/zones
GET  /api/v1/zones/{zone_id}
GET  /api/v1/zones/lookup?latitude=11.414&longitude=76.651
POST /api/v1/simulation/start
POST /api/v1/simulation/stop
POST /api/v1/simulation/reset
GET  /api/v1/simulation/status
```

Useful demo commands:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/simulation/start
curl http://127.0.0.1:8000/api/v1/animals
curl http://127.0.0.1:8000/api/v1/animals/EL-001/location
curl http://127.0.0.1:8000/api/v1/animals/EL-001/movement
curl -X POST http://127.0.0.1:8000/api/v1/simulation/stop
```

The simulator runs inside the FastAPI process for development. Tune it with `SIMULATION_INTERVAL_SECONDS`; the default is `5`.

## Phase 4 — Spatial and temporal intelligence

Phase 4 turns GPS observations into movement intelligence using PostgreSQL/PostGIS as the source of truth:

- Current zone detection with `ST_Contains` against the latest animal observation.
- Point-in-polygon lookup for coordinates and observations.
- Movement reconstruction ordered by `observed_at`.
- Consecutive-point distance with PostGIS geography distance calculations.
- Total distance, movement duration, zone history, and zone transition timelines.
- Nearby zone and nearby animal queries.
- Zone detail intelligence for animals currently inside and recent entries/exits.

MongoDB remains event-only storage. Phase 4 does not execute ECA rules, generate new risk alerts, or duplicate animal, zone, or observation records into MongoDB.

New and enriched APIs under `/api/v1`:

```text
GET /api/v1/animals/{animal_id}/movement
GET /api/v1/animals/{animal_id}/zone-history
GET /api/v1/animals/{animal_id}/timeline
GET /api/v1/animals/{animal_id}/distance
GET /api/v1/animals/nearby?latitude=11.414&longitude=76.651&radius_meters=1000
GET /api/v1/zones/{zone_id}/animals
GET /api/v1/zones/{zone_id}/transitions
GET /api/v1/zones/nearby?latitude=11.414&longitude=76.651&radius_meters=1000
```

Example movement response:

```json
{
  "animal_id": "EL-001",
  "total_distance_meters": 3420.5,
  "movement_duration_seconds": 2040,
  "started_at": "2026-09-24T10:12:00Z",
  "ended_at": "2026-09-24T10:46:00Z",
  "points": [
    {
      "latitude": 11.451,
      "longitude": 76.644,
      "timestamp": "2026-09-24T10:12:00Z",
      "speed": 3.2,
      "zone": {
        "zone_id": "ZONE-SAFE",
        "name": "North Bamboo Safe Zone",
        "zone_type": "safe",
        "risk_level": "safe"
      },
      "distance_from_previous_meters": null
    }
  ]
}
```

The frontend consumes these APIs through `src/services/observationService.js` and `src/services/zoneService.js`. Live Monitor continues polling every few seconds and updates markers/paths without remounting the MapLibre map. Movement History now loads real backend movement, zone history, transition timeline, distance, and duration data.

## Frontend service layer

UI components use hooks, hooks call `src/services/*`, and services call the API client. The frontend expects `VITE_API_BASE_URL` to include the versioned API root, for example:

```bash
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

Service calls should use paths relative to that base, such as `/animals`, `/zones`, and `/observations?limit=500`. The API client also strips an accidental leading `/api/v1` from service paths to avoid duplicate version prefixes.

If the backend is unavailable, the existing service fallbacks keep the UI usable with mock data. Live Monitor and Movement History poll backend-backed services with `VITE_API_POLLING_INTERVAL_MS` or a default of `5000` ms.

## Checks

Run the frontend build:

```bash
npm run build
```

Run backend compile and Phase 3 integration checks:

```bash
python -m compileall -q backend
python -m unittest backend.app.tests.test_phase3
```

Run Phase 4 checks:

```bash
python -m unittest backend.app.tests.test_phase4
```
