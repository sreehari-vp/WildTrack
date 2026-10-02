# WildTrack

React and MapLibre wildlife monitoring with FastAPI, PostgreSQL/PostGIS and MongoDB. An optional Neo4j Aura projection powers the separate Movement Network page.
PostgreSQL remains authoritative for wildlife records. Authentication, demo mode and separate test databases are not in scope.

## Run locally

Use the existing backend/venv environment; system Python has incompatible packages.

    python -m venv backend/venv
    .\backend\venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
    npm install

Create .env from .env.example with the existing database URLs. VITE_ variables are public and must not contain database credentials.

    .\backend\venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
    .\backend\venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8001
    npm run dev -- --host 127.0.0.1 --port 5173

Run frontend and backend in separate terminals. API documentation: http://127.0.0.1:8001/docs.

For Windows, `run-backend.ps1` and `run-frontend.ps1` start this checkout from their own folder and fail if the required ports are already occupied. In development, Vite proxies `/api/v1` to `127.0.0.1:8001`; the production build uses `VITE_API_BASE_URL`. If zone or pin saves return HTTP 405, check which backend is serving port 8001.

## Data safety

All screens read API data. Failures display errors; there is no sample-data fallback. Animals without GPS fixes are omitted from the map, and unknown timestamps stay unknown.
Seed commands insert missing records only. They never delete existing data or run automatically.

    .\backend\venv\Scripts\python.exe -m backend.app.seed.seed_all

Migration 0002 adds constraints, a partial unique index for active alerts and trigger-maintained alert history. Migration 0003 adds persistent map pins, map preferences and a zone ownership flag. Migration 0004 adds temporal zone/rule versions, configuration audit, the event outbox and hourly summaries. Incompatible data fails the transaction instead of being silently changed. Existing zone/rule history begins at migration-time baseline version 1; past changes cannot be reconstructed.
Migration 0005 adds an export batch/ID ledger for incremental historical Parquet files. It does not alter wildlife records.

## Advanced database concepts implemented

- PostGIS spatial indexes and geography distances.
- Boundary-inclusive ST_Covers with deterministic overlap priority: highest risk, smallest area, then zone ID.
- Window functions for movement, zone transitions and dwell estimates.
- JSONB event-condition-action rules evaluated by the application.
- Atomic upserts and partial unique indexes for active-alert deduplication.
- Row locks for concurrent alert transitions.
- Database triggers for alert status history.
- Database triggers for zone/rule versions and configuration audit (zones, rules, pins, preferences).
- PostgreSQL transactional outbox with concurrent-worker row locks, MongoDB idempotent upserts and retries.
- SQL hourly operational summary view and server-sent monitoring updates.
- Resumable, locally stored Parquet archives of observations and alert facts.
- Generation-switched Neo4j Aura projection of zone corridors, with daily species and animal contributions. PostgreSQL provides the observations and related alerts.
- Repeatable-read snapshots for consistent analytical results.
- MongoDB document collections for flexible events.
- Foreign keys and coordinate, battery, speed, status and geometry constraints.

## Map behavior

Only the selected route is shown. Legend, layers, tools and the alerts drawer start collapsed. Hover or keyboard focus reveals secondary marker information; clicking opens details. Search, species and zone filters work. MultiPolygon parts and holes are retained, areas come from PostGIS, and OpenStreetMap attribution is visible.

## Verification without a test database

    npm test
    npm run build
    .\backend\venv\Scripts\python.exe -m unittest discover -s backend/app/tests -v

Default backend checks use pure functions and mocks. Opt into read-only checks of existing application records:

    $env:WILDTRACK_READONLY_CHECKS='1'
    .\backend\venv\Scripts\python.exe -m unittest discover -s backend/app/tests -v
    Remove-Item Env:WILDTRACK_READONLY_CHECKS

Checks do not seed, reset, insert fixtures, resolve alerts or start simulation. Destructive legacy fixtures have been replaced.

## Monitoring and analytics

Analytics defaults to the last seven days and supports date range and species filters. Use a preset or choose dates and apply the range. The API accepts timezone-qualified start_time/end_time and an optional species. Activity charts count GPS observations; alert trends include zero-activity days. Distance uses consecutive fixes no more than 30 minutes apart, including a preceding fix just before the selected range. Dwell estimates are clipped to the selected range and use the zone version active at the first fix.
Monitoring uses server-sent events with HTTP polling fallback and exposes simulator start/stop controls. The simulator advances 15 finite journeys approximately every 3 seconds. Five corridor animals use accelerated steps up to 300 metres so their first Safe → Buffer → High-Risk → Protected zone crossing occurs about 30–45 seconds after starting; resident animals retain smoother steps up to 40 metres inside their habitats. Map markers glide between consecutive fixes. Start emits the next fix immediately, Stop pauses progress, and journeys stop at their destinations. After a backend restart, progress resumes from the last recorded waypoint. The Status tab shows active animals, open alerts, pending/retrying event deliveries and hourly activity. Run the simulator in one API worker. Zone edits, newly drawn zones, pins and map settings persist in PostgreSQL. Seeded zones can be edited; only newly drawn zones without observations or alerts can be deleted.

Phase 6C read endpoints: `GET /api/v1/zones/{id}/history?at=<timezone-qualified timestamp>`, `GET /api/v1/rules/{id}/history`, `GET /api/v1/monitoring/audit`, `GET /api/v1/monitoring/summary`, and `GET /api/v1/monitoring/stream`. Rule changes use `GET/POST /api/v1/rules` and `PUT /api/v1/rules/{id}`; every change creates a new version. The outbox worker starts with the backend and delivers PostgreSQL-committed events to MongoDB; pending/retrying counts reveal delays. Restart the existing backend process after updating the code so the worker and new routes load.

## Phase 7 local historical archive

Install the pinned backend dependencies and apply migration 0005 as shown above. Then export the existing PostgreSQL records to the ignored `historical_exports/` directory:

    .\backend\venv\Scripts\python.exe -m backend.app.export_history export
    .\backend\venv\Scripts\python.exe -m backend.app.export_history status
    .\backend\venv\Scripts\python.exe -m backend.app.export_history verify

The exporter reads at most 100 batches of 1,000 records per dataset per invocation; use `--batch-size` and `--max-batches` to adjust. Rerun it to pick up new observations and alerts. PostgreSQL claims each source ID once, and unfinished batches resume with the same filename after a failure. Parquet files are partitioned by UTC `event_date`; observation rows include the matching zone geometry version when available. Alerts capture the rule version that generated them. Existing historical rows predate migration 0004's version baseline, so their zone version can be null.

Phase 8 (Neo4j Aura movement network) and Phase 9 (analytics integration and deployment preparation) are implemented. The completion checklist and limitations are in [IMPLEMENTATION.md](IMPLEMENTATION.md).

## Phase 8 Neo4j Aura movement network

Create one **AuraDB Free** instance, then add its connection details to this checkout's `.env` (never to a `VITE_` variable):

    NEO4J_URI=neo4j+s://YOUR_INSTANCE.databases.neo4j.io
    NEO4J_USERNAME=YOUR_AURA_USERNAME
    NEO4J_PASSWORD=YOUR_INSTANCE_PASSWORD
    NEO4J_DATABASE=YOUR_AURA_DATABASE

Install `backend/requirements.txt` in the existing virtual environment and restart the backend. The backend performs a source-change check and refreshes the graph periodically. You can inspect or force the first sync without starting a project server:

    .\backend\venv\Scripts\python.exe -m backend.app.sync_network status
    .\backend\venv\Scripts\python.exe -m backend.app.sync_network sync

Open `/movement-network` for the separate network page. `GET /api/v1/network/status` and `GET /api/v1/network` expose current projection state and filtered corridors; `POST /api/v1/network/sync` refreshes it. The page also shows contributing animals, related PostgreSQL alerts and three-step habitat connections. The React app never receives Aura credentials. PostgreSQL/PostGIS remains authoritative for observations, zone versions, animals and alerts; Neo4j can be rebuilt after interruption or deletion. Zone assignment uses the version valid at each observation time, so pre-version records without a matching zone are excluded from the graph rather than guessed. A corridor requires successive visits to two different zones by the same animal within six hours; it is an observed connection, not a confirmed physical trail.

The Aura projection has been synchronized and verified against this checkout. Aura supplies the exact username and database name for the instance; use those values rather than assuming a default. The rest of the application continues to work while Aura is unavailable. Habitat impact lists the observed corridors reachable within three connections and animals recorded on those corridors; it describes historical connectivity, not a forecast.

## Demonstration walkthrough

1. Ensure PostgreSQL/PostGIS and MongoDB are reachable. Neo4j Aura is optional for the map and alerts, and required for graph corridor analysis.
2. Apply migrations and start the backend and frontend using the commands under [Run locally](#run-locally).
3. Open Live Monitor and start the simulation. Observe the five corridor animals reach a zone boundary in about 30–45 seconds; configured ECA rules may create alerts as they move.
4. Stop the simulation and confirm the journey pauses. Restart the backend later to demonstrate that progress resumes from stored observations.
5. Open Analytics, choose a date range and species, then apply the filters. Compare GPS activity, alerts, estimated distance and zone dwell for that selection.
6. Open Movement Network, sync if the projection is stale, filter connections by species/date, and select a corridor or zone to inspect contributors and disruption reach.
7. Open the Live Monitor Status tab to inspect active animals, alerts and event deliveries awaiting MongoDB. Export or verify the historical Parquet archive with the Phase 7 commands above.

The simulator uses generated routes for software demonstration. Do not interpret generated positions or graph corridors as verified field telemetry or exact animal trails.

## Deployment preparation

`render.yaml` describes one FastAPI service and one static React service. It does not create databases or deploy anything by itself. Before connecting the repository to Render, provision the hosted PostgreSQL/PostGIS and MongoDB services (and Neo4j Aura if graph analysis is wanted), set the secret environment variables in Render, and apply database migrations from a trusted environment:

    .\backend\venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head

Keep `APP_CORS_ORIGINS` aligned with the deployed frontend URL and `VITE_API_BASE_URL` aligned with the deployed API URL. Do not put credentials in frontend variables. The Render blueprint names assume `wildtrack-web.onrender.com` and `wildtrack-api.onrender.com`; update both if Render assigns different service URLs. External hosting remains a user-controlled step because it needs access to hosting accounts and production database credentials.
